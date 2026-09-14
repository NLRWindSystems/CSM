"""Fits a new CSM model's coefficients directly from a CSV of empirical component measurements
(and, optionally, an industry cost benchmark CSV), reusing an existing model's formula shapes
(:py:data:`Land2020NLR` by default) so the result can be dropped into
:py:mod:`csm.tools.experimental.plotting`'s `models=` dict with zero other changes.

Only components the input CSV(s) actually cover get new coefficients; everything else simply
inherits the base model's own value. See :py:func:`build_custom_model` for the main entry point.
"""

import re
import sys
import math
import textwrap
import importlib
import contextlib
from typing import NamedTuple
from pathlib import Path
from dataclasses import dataclass
from collections.abc import Callable

import numpy as np
import pandas as pd
from attrs import fields as attrs_fields
from scipy.optimize import curve_fit

from csm.models.nlr2015 import Land2015NLR
from csm.models.nlr2020 import Land2020NLR
from csm.tools.experimental.plotting import (
    ALL_COMPONENTS,
    BENCHMARK_OVERLAY,
    BENCHMARK_RD_COLUMN,
    WM_CATEGORY_MAPPING,
    BENCHMARK_ITEM_COLUMN,
    DEFAULT_TURBINE_SPECS,
    EMPIRICAL_COST_COLUMN,
    EMPIRICAL_MASS_COLUMN,
    BENCHMARK_TOWER_COLUMN,
    BENCHMARK_VALUE_COLUMN,
    BENCHMARK_CAPACITY_COLUMN,
    TOWER_SWEPT_VOLUME_DRIVER,
    WMMapping,
    ComponentSpec,
    _base_config,
    _driver_range,
    _bin_midpoints,
    _empirical_rows,
    load_benchmark_data as _load_benchmark_data,
    load_empirical_data as _load_empirical_data,
    _evaluate_all_configs,
    _safe_upstream_kwargs,
    _derive_empirical_entry,
    _combined_cost_multiplier,
)


class MassFitSpec(NamedTuple):
    """How to fit one component's mass to a particular formula shape.

    `params` lists the coefficient field names in fit-priority order — the order they're freed in
    when there isn't enough data to fit every one of them (see the data-scarce fallback in
    :py:func:`_fit_mass_component`). `formula` is that exact shape, `f(x, *params) -> mass`.
    `x_from_entry` pulls the independent variable value from a `_derive_empirical_entry`-style
    dict (built from one CSV row's raw RD/MW/hh columns, plus a derived `rotor_torque` and, for
    components that depend on it, a derived `_blade_mass`/`_blade_mass_rating`). `domain` names
    which reference range :py:func:`_plausibility_grid` checks the fit against.
    """

    params: tuple[str, ...]
    formula: Callable[..., float]
    x_from_entry: Callable[[dict], float | None]
    domain: str


class StructuralOverride(NamedTuple):
    """A component whose desired formula shape isn't natively available on some model class as
    plain overridable fields (e.g. `Land2015NLR` has no `blade_mass_exp` field at all — its blade
    exponent is a hardcoded class/carbon lookup table, not a scalar; `Land2020NLR` has no
    `tower_mass_exp` field at all — its tower formula uses a rotor-diameter-dependent composite
    instead of a plain hub-height exponent).

    In that case the generated model needs one or more real new fields, a replacement
    `calculate_*` method, and a `parameter_map` override — mirroring exactly how `nlr2020.py`
    itself introduces `blade_mass_exp` / redefines `calculate_tower_mass` relative to `CSMBase`,
    just generated instead of hand-written. Emitted only when at least one of `new_fields` isn't
    already present on the model's actual base class (see :py:func:`_has_field`) — for a base that
    already provides the desired shape natively, this is skipped entirely, plain `.reuse()`
    suffices.
    """

    new_fields: tuple[tuple[str, float], ...]  # (field name, default fallback) pairs
    method_body: str
    parameter_map_line: str


def _tower_x_from_entry(entry: dict) -> float | None:
    if "rotor_diameter" not in entry or "tower_length" not in entry:
        return None
    return TOWER_SWEPT_VOLUME_DRIVER.display_from_entry(entry)


# Components whose formula shape never changes with base_model_cls — either because every base
# model already shares the same shape (Hub, Generator, Main Bearing, Transformer), or because a
# StructuralOverride (below) forces the same shape regardless of base (Blade).
_SHARED_MASS_FIT_SPECS: dict[str, MassFitSpec] = {
    "Blade": MassFitSpec(
        ("blade_mass_coeff", "blade_mass_exp"),
        lambda x, coeff, exp: coeff * (x / 2) ** exp,
        lambda entry: entry.get("rotor_diameter"),
        "rotor_diameter",
    ),
    "Hub": MassFitSpec(
        ("hub_mass_coeff", "hub_mass_intercept"),
        lambda x, coeff, intercept: coeff * x + intercept,
        lambda entry: entry.get("_blade_mass"),
        "blade_mass",
    ),
    "Generator": MassFitSpec(
        ("generator_mass_coeff", "generator_mass_intercept"),
        lambda x, coeff, intercept: coeff * x + intercept,
        lambda entry: entry.get("rated_power_kw"),
        "rated_power_kw",
    ),
    "Main Bearing": MassFitSpec(
        ("bearing_mass_coeff", "bearing_mass_exp"),
        lambda x, coeff, exp: coeff * x**exp,
        lambda entry: entry.get("rotor_diameter"),
        "rotor_diameter",
    ),
    "Transformer": MassFitSpec(
        ("transformer_mass_coeff", "transformer_mass_intercept"),
        lambda x, coeff, intercept: coeff * x + intercept,
        lambda entry: entry.get("rated_power_kw"),
        "rated_power_kw",
    ),
}

# Land2020NLR's own shapes for the 4 components whose formula genuinely differs from CSMBase's
# (Land2015NLR's) native one.
MASS_FIT_SPECS_2020: dict[str, MassFitSpec] = {
    **_SHARED_MASS_FIT_SPECS,
    "Gearbox": MassFitSpec(
        ("gearbox_torque_density", "gearbox_torque_exp"),
        lambda x, density, exp: density * x**exp,
        lambda entry: entry.get("rotor_torque"),
        "rotor_torque",
    ),
    "Bedplate": MassFitSpec(
        ("bedplate_mass_coeff", "bedplate_mass_intercept"),
        lambda x, coeff, intercept: coeff * x + intercept,
        lambda entry: entry.get("rotor_diameter"),
        "rotor_diameter",
    ),
    "Low Speed Shaft": MassFitSpec(
        ("lss_mass_coeff1", "lss_mass_coeff2", "lss_mass_intercept"),
        lambda x, c1, c2, b: c1 * x**2 + c2 * x + b,
        lambda entry: entry.get("rotor_diameter"),
        "rotor_diameter",
    ),
    "Tower": MassFitSpec(
        ("tower_mass_coeff", "tower_mass_intercept"),
        lambda x, coeff, intercept: coeff * x + intercept,
        _tower_x_from_entry,
        "tower_composite",
    ),
}

# CSMBase's (Land2015NLR's) own native shapes for the same 4 components — including Tower, whose
# native formula (`coeff * H^exp`, ignoring rotor diameter entirely) genuinely differs from
# Land2020NLR's hub-height x swept-area composite.
MASS_FIT_SPECS_2015: dict[str, MassFitSpec] = {
    **_SHARED_MASS_FIT_SPECS,
    "Gearbox": MassFitSpec(
        ("gearbox_torque_density",),
        lambda x, density: x * 1e3 / density,
        lambda entry: entry.get("rotor_torque"),
        "rotor_torque",
    ),
    "Bedplate": MassFitSpec(
        ("bedplate_mass_exp",),
        lambda x, exp: x**exp,
        lambda entry: entry.get("rotor_diameter"),
        "rotor_diameter",
    ),
    "Low Speed Shaft": MassFitSpec(
        ("lss_mass_coeff", "lss_mass_exp", "lss_mass_intercept"),
        lambda x, coeff, exp, intercept: coeff * x**exp + intercept,
        lambda entry: entry.get("_blade_mass_rating"),
        "blade_mass_rating",
    ),
    "Tower": MassFitSpec(
        ("tower_mass_coeff", "tower_mass_exp"),
        lambda x, coeff, exp: coeff * x**exp,
        lambda entry: entry.get("tower_length"),
        "tower_length",
    ),
}

# Components whose x_from_entry needs Blade's *fitted* mass, not a raw CSV column — Blade must be
# fit first (see MASS_FIT_ORDER) so its coefficients are available when these are computed.
NEEDS_BLADE_MASS: frozenset[str] = frozenset({"Hub", "Low Speed Shaft"})

# Blade must be fit before Hub/Low Speed Shaft; everything else is independent of fit order.
MASS_FIT_ORDER: list[str] = [
    "Blade",
    "Hub",
    "Gearbox",
    "Generator",
    "Tower",
    "Bedplate",
    "Main Bearing",
    "Low Speed Shaft",
    "Transformer",
]

# A single empirical mass point can't constrain a new scaling relationship on its own — the one
# coefficient it happens to be able to solve for is an unconstrained extrapolation everywhere
# else, which is what skewed Bedplate (and, via nacelle_mass, the whole nacelle total) noticeably
# off both 2015 and 2020 despite looking like a reasonable "fit what you can" result in isolation.
# Below this many points, _fit_mass_component inherits the relevant model's curve unchanged
# instead of fitting anything.
MIN_MASS_FIT_POINTS = 2

# How far beyond a mass fit's own observed x-range (multiplicatively — these are always-positive
# physical quantities like mass/diameter/torque, where relative distance is the meaningful one)
# _fit_mass_component's negative/invalid-prediction plausibility check still applies. See that
# check's own comment for why this needs to be generous enough to not reject a fit purely because
# DEFAULT_TURBINE_SPECS spans a turbine size class nothing in a given component's own data was
# ever measured at.
MASS_FIT_PLAUSIBILITY_MARGIN = 2.0

# Mass-shape structural overrides, keyed by (component label, shape name) — needed only when a
# component's *resolved* MassFitSpec (see _resolve_mass_fit_specs: every component defaults to
# Land2020NLR's shape, but a per-component `shape_overrides` entry can request a different model's
# shape instead) doesn't match what the generated model's actual base class provides natively.
# Blade's shape is always forced to the scalar-exponent form (Land2015NLR/CSMBase's own blade
# formula is a class/carbon lookup table, not something `shape_overrides` can meaningfully select
# between) — matches Land2020NLR's own nlr2020.py exactly (see calculate_blade_mass there), and is
# only actually emitted when the base class doesn't already provide it (i.e. isn't Land2020NLR).
MASS_SHAPE_OVERRIDES: dict[tuple[str, str], StructuralOverride] = {
    ("Blade", "2020"): StructuralOverride(
        new_fields=(("blade_mass_exp", 1.7679),),
        method_body=(
            "    def calculate_blade_mass(self):\n"
            '        """Structural override: always fits a real blade_mass_exp field, instead of\n'
            "        the base model's class/carbon lookup table, regardless of the base model.\n"
            '        """\n'
            '        exists = self._prepare_calculation("blade_mass")\n'
            "        if exists:\n"
            "            return\n"
            "        self.blade_mass = (\n"
            "            self.blade_mass_coeff * (self.rotor_diameter / 2) ** self.blade_mass_exp\n"
            "        )\n"
        ),
        parameter_map_line=(
            '        self.parameter_map["blade_mass"] = '
            '("rotor_diameter", "blade_mass_coeff", "blade_mass_exp")\n'
        ),
    ),
    ("Tower", "2015"): StructuralOverride(
        # tower_mass_coeff already exists on every base (just with a different fitted value here);
        # only the exponent is genuinely new relative to Land2020NLR's composite shape.
        new_fields=(("tower_mass_exp", 2.0282),),
        method_body=(
            "    def calculate_tower_mass(self):\n"
            '        """Structural override: this component specifically uses Land2015NLR/\n'
            "        CSMBase's simpler hub-height-only shape, instead of this model's own base\n"
            "        class's native shape.\n"
            '        """\n'
            '        exists = self._prepare_calculation("tower_mass")\n'
            "        if exists:\n"
            "            return\n"
            "        self.tower_mass = (\n"
            "            self.tower_mass_coeff * self.tower_length**self.tower_mass_exp\n"
            "        )\n"
        ),
        parameter_map_line=(
            '        self.parameter_map["tower_mass"] = '
            '("tower_mass_coeff", "tower_length", "tower_mass_exp")\n'
        ),
    ),
    ("Bedplate", "2015"): StructuralOverride(
        # Land2020NLR carries a vestigial bedplate_mass_exp field (default 0, unused by its own
        # linear formula) — declaring it here via create_field (not .reuse()) always sets it
        # explicitly, whether from a real fit or this shape's own default, rather than silently
        # inheriting that unrelated 0.
        new_fields=(("bedplate_mass_exp", 2.2),),
        method_body=(
            "    def calculate_bedplate_mass(self):\n"
            '        """Structural override: this component specifically uses Land2015NLR/\n'
            "        CSMBase's simpler rotor-diameter-only shape, instead of this model's own\n"
            "        base class's native shape.\n"
            '        """\n'
            '        exists = self._prepare_calculation("bedplate_mass")\n'
            "        if exists:\n"
            "            return\n"
            "        self.bedplate_mass = self.rotor_diameter**self.bedplate_mass_exp\n"
        ),
        parameter_map_line=(
            '        self.parameter_map["bedplate_mass"] = (\n'
            '            "rotor_diameter",\n'
            '            "bedplate_mass_exp",\n'
            "        )\n"
        ),
    ),
}

# Converter's cost override is unconditional (no existing model prices it as a function of
# turbine rating at all — its mass, and therefore its mass-based cost, is hardcoded to 0 in every
# current model) — an affine fit (coeff * rating + intercept), unlike every other current cost
# formula's proportional-through-origin shape, chosen so the fit can get as close as possible to
# the 2026 benchmark's "Converter" category (see _fit_converter_cost).
CONVERTER_COST_OVERRIDE = StructuralOverride(
    new_fields=(("converter_cost_coeff", 20.0), ("converter_cost_intercept", 0.0)),
    method_body=(
        "    def calculate_converter_cost(self):\n"
        '        """Structural override: cost is fit directly against turbine rating, with an\n'
        "        intercept (unlike every other current cost formula), instead of the base\n"
        "        model's always-zero converter mass, regardless of the base model.\n"
        '        """\n'
        '        exists = self._prepare_calculation("converter_cost")\n'
        "        if exists:\n"
        "            return\n"
        "        self.converter_cost = (\n"
        "            self.converter_cost_coeff * self.rated_power_kw\n"
        "            + self.converter_cost_intercept\n"
        "        )\n"
    ),
    parameter_map_line=(
        '        self.parameter_map["converter_cost"] = (\n'
        '            "converter_cost_coeff",\n'
        '            "rated_power_kw",\n'
        '            "converter_cost_intercept",\n'
        "        )\n"
    ),
)


def _has_field(model_cls: type, name: str) -> bool:
    return any(f.name == name for f in attrs_fields(model_cls))


class PitchSystemShape(NamedTuple):
    """Which field :py:func:`_fit_pitch_system_mass` should fit to move Pitch System's mass, for
    one of the two structurally different implementations of `outer*(inner*blade_mass*num_blades
    + inner_intercept) + offset` found across the base models this module supports — `Land2020NLR`
    introduces its own dedicated scaling field for `outer` (`pitch_system_mass_coeff`), while
    `CSMBase`/`Land2015NLR`'s native formula has no such field (its outer factor is the literal
    expression `1 + bearing_housing_fraction`), so it's `inner` (`pitch_bearing_mass_coeff`) that
    gets fit there instead. `fixed_multiplier` is whichever of outer/inner *isn't* `fit_field`,
    already resolved to a plain float (folding in `Land2015NLR`'s `1 +` where relevant) so the
    solve in :py:func:`_fit_pitch_system_mass` doesn't need its own branch per shape.
    """

    fit_field: str
    fit_is_outer: bool
    fixed_multiplier: float
    fixed_intercept: float
    offset_field: str


def _pitch_system_shape(base_model_cls: type) -> PitchSystemShape:
    """Resolves :py:class:`PitchSystemShape` for `base_model_cls` — checked via field presence
    the same way :py:func:`_native_spec_for` distinguishes mass-formula shapes elsewhere in this
    module: `pitch_system_mass_coeff` is a field `Land2020NLR` itself introduces, never present
    (even vestigially) on a model using `CSMBase`'s native shape.
    """
    if _has_field(base_model_cls, "pitch_system_mass_coeff"):
        return PitchSystemShape(
            fit_field="pitch_system_mass_coeff",
            fit_is_outer=True,
            fixed_multiplier=_default_coeff(base_model_cls, "pitch_blade_mass_coeff"),
            fixed_intercept=_default_coeff(base_model_cls, "pitch_blade_mass_intercept"),
            offset_field="mass_sys_offset",
        )
    return PitchSystemShape(
        fit_field="pitch_bearing_mass_coeff",
        fit_is_outer=False,
        fixed_multiplier=1 + _default_coeff(base_model_cls, "bearing_housing_fraction"),
        fixed_intercept=_default_coeff(base_model_cls, "pitch_bearing_mass_intercept"),
        offset_field="mass_sys_offset",
    )


def _shape_name(label: str, spec: MassFitSpec) -> str:
    """Which named shape variant `spec` represents for `label` — "2020" or "2015" — used to look
    up the matching entry in :py:data:`MASS_SHAPE_OVERRIDES` when a structural override turns out
    to be needed. Blade only has one meaningful representation (see that override's docstring).
    """
    if label == "Blade":
        return "2020"
    if spec is MASS_FIT_SPECS_2020.get(label):
        return "2020"
    if spec is MASS_FIT_SPECS_2015.get(label):
        return "2015"
    raise ValueError(f"'{label}' spec doesn't match a known shape variant")


def _native_spec_for(label: str, model_cls: type) -> MassFitSpec:
    """Which shape (`MASS_FIT_SPECS_2020[label]` or `MASS_FIT_SPECS_2015[label]`) `model_cls`'s
    own `calculate_<label>_mass` method actually implements.

    Checked via whether `model_cls` has *every* field the 2020-shape's formula needs — reliable
    specifically because, for every component where the two shapes differ, at least one of those
    fields is genuinely exclusive to `Land2020NLR` (e.g. `tower_mass_intercept`,
    `gearbox_torque_exp`, `bedplate_mass_intercept`, `lss_mass_coeff1`) and never present, even
    vestigially, on a model actually using the 2015/`CSMBase` shape. Deliberately does **not**
    check the 2015-shape's own fields the same way: `CSMBase` declares some fields (e.g.
    `tower_mass_exp`) that `Land2020NLR` still carries even though its own formula doesn't use
    them, which would make a naive "does it have all of this shape's fields" check on the
    *2015* side wrongly conclude a `Land2020NLR`-based model natively provides the 2015 shape too.
    """
    spec_2020 = MASS_FIT_SPECS_2020[label]
    return (
        spec_2020
        if all(_has_field(model_cls, p) for p in spec_2020.params)
        else MASS_FIT_SPECS_2015[label]
    )


def _resolve_mass_fit_specs(
    base_model_cls: type, shape_overrides: dict[str, type] | None
) -> dict[str, MassFitSpec]:
    """The effective `MassFitSpec` for every component this module can fit: `Land2020NLR`'s shape
    by default, except where `shape_overrides` names a different model class to source a specific
    component's formula *shape* from (e.g. `{"Tower": Land2015NLR}`) — independent of
    `base_model_cls`, which only sets the default for anything not explicitly overridden.
    """
    shape_overrides = shape_overrides or {}
    return {
        label: _native_spec_for(label, shape_overrides.get(label, base_model_cls))
        for label in MASS_FIT_ORDER
    }


def _shape_default_source(
    label: str, spec: MassFitSpec, shape_overrides: dict[str, type] | None
) -> type:
    """The model class whose own coefficient values are the right p0/default for `spec` — the
    `shape_overrides` entry for `label` if there is one (e.g. `Land2015NLR` for a Tower forced to
    its shape), otherwise whichever of `Land2020NLR`/`Land2015NLR` actually matches `spec`'s shape
    (Blade always resolves to `Land2020NLR`, the only model with a plain `blade_mass_exp` field).
    """
    shape_overrides = shape_overrides or {}
    if label in shape_overrides:
        return shape_overrides[label]
    return Land2020NLR if _shape_name(label, spec) == "2020" else Land2015NLR


def _needed_structural_overrides(
    mass_fit_specs: dict[str, MassFitSpec], base_model_cls: type
) -> list[StructuralOverride]:
    """Every :py:data:`MASS_SHAPE_OVERRIDES` entry actually needed to render `mass_fit_specs`
    faithfully against `base_model_cls`, plus :py:data:`CONVERTER_COST_OVERRIDE` (always needed —
    no base model has that shape natively). Raises clearly if a resolved shape has no matching
    override available, rather than silently rendering a formula that doesn't match the fitted
    coefficients.
    """
    needed = [CONVERTER_COST_OVERRIDE]
    for label, spec in mass_fit_specs.items():
        if spec is _native_spec_for(label, base_model_cls):
            continue
        key = (label, _shape_name(label, spec))
        if key not in MASS_SHAPE_OVERRIDES:
            raise ValueError(
                f"No structural override available to render {label}'s {key[1]}-style formula "
                f"on top of {base_model_cls.__name__} — add one to MASS_SHAPE_OVERRIDES."
            )
        needed.append(MASS_SHAPE_OVERRIDES[key])
    return needed


# Cost coefficient field name for every leaf component that appears in WM_CATEGORY_MAPPING (i.e.
# every component a benchmark category can inform), so the group-cost fit in _fit_cost_group can
# look up where to put a fitted coefficient regardless of whether that component also has mass
# data of its own. Most formulas multiply mass ("*_mass_cost_coeff"); Controls/Electrical
# Connection multiply rated power directly instead (their mass is hardcoded to 0 in every current
# model) — handled uniformly by reading each leaf's own already-computed cost back from the model
# rather than assuming any particular formula shape (see _fit_cost_group's `regressor`).
COST_COEFF_FIELD: dict[str, str] = {
    "Blade": "blade_mass_cost_coeff",
    "Hub": "hub_mass_cost_coeff",
    "Pitch System": "pitch_system_mass_cost_coeff",
    "Spinner": "spinner_mass_cost_coeff",
    "Low Speed Shaft": "lss_mass_cost_coeff",
    "Main Bearing": "bearing_mass_cost_coeff",
    "Gearbox": "gearbox_mass_cost_coeff",
    "Brake": "brake_mass_cost_coeff",
    "High Speed Shaft": "hss_mass_cost_coeff",
    "Generator": "generator_mass_cost_coeff",
    "Bedplate": "bedplate_mass_cost_coeff",
    "Yaw System": "yaw_system_mass_cost_coeff",
    "Hydraulic Cooling": "hvac_mass_cost_coeff",
    "Nacelle Cover": "nacelle_cover_mass_cost_coeff",
    "Platform & Mainframe": "platform_mainframe_mass_cost_coeff",
    "Transformer": "transformer_mass_cost_coeff",
    "Converter": "converter_cost_coeff",
    "Controls": "controls_cost_coeff",
    "Electrical Connection": "electrical_connection_cost_coeff",
    "Tower": "tower_mass_cost_coeff",
}


def _cost_coeff_field_for(label: str, base_model_cls: type) -> str:
    """The cost coefficient field name to use for `label` under `base_model_cls` — almost always
    just `COST_COEFF_FIELD[label]`, except in these cases.

    - Gearbox: `Land2015NLR`/`CSMBase`'s native gearbox cost formula multiplies mass by
      `gearbox_torque_density * gearbox_torque_cost` (two fields, the first already used as the
      *mass* formula's own coefficient) rather than a single `gearbox_mass_cost_coeff` field
      (`Land2020NLR`'s own invention) — so under a 2015-shaped base, the single coefficient this
      module scales is `gearbox_torque_cost` instead.
    - Any structural-override field (e.g. Converter's `converter_cost_coeff`) — not native to
      *either* base model, so `_has_field` alone would never find it.
    """
    field = COST_COEFF_FIELD[label]
    known_override_fields = {
        name
        for o in (*MASS_SHAPE_OVERRIDES.values(), CONVERTER_COST_OVERRIDE)
        for name, _ in o.new_fields
    }
    if _has_field(base_model_cls, field) or field in known_override_fields:
        return field
    if label == "Gearbox":
        return "gearbox_torque_cost"
    raise AttributeError(f"{base_model_cls.__name__} has no cost field for '{label}'")


# "Total" components with no coefficients of their own to fit (their mass is a straight sum in
# the base model) — their CSV rows are instead used to validate the bottom-up result.
AGGREGATE_CHECKS: dict[str, str] = {
    "Nacelle (Total)": "nacelle_mass",
    "Rotor (Total)": "rotor_mass",
    "Turbine (Total)": "turbine_mass",
}


@dataclass
class FitResult:
    """One row of the fit report: what was (or wasn't) fit for one component."""

    label: str
    kind: str  # "mass" | "cost" | "aggregate_check"
    params: dict[str, float]
    r_squared: float | None
    n_points: int
    status: str


@dataclass
class CustomModelResult:
    """The fitted model class, its class name, the file it was written to (if any), and the
    full fit report — everything :py:func:`build_custom_model` produces.
    """

    model_cls: type
    class_name: str
    module_path: Path | None
    report: list[FitResult]


def _default_coeff(model_cls: type, name: str) -> float:
    """Reads a model class's default (coefficient) value for one of its attrs fields.

    Falls back to a structural override's own default (`MASS_SHAPE_OVERRIDES` or
    `CONVERTER_COST_OVERRIDE`) if `model_cls` doesn't have the field at all — true for a field
    genuinely new to every existing model (e.g. Converter's `converter_cost_coeff`/
    `converter_cost_intercept`, fit fresh from benchmark data, not borrowed from anywhere). In
    practice this fallback rarely fires for a *mass*-shape field: callers normally look those up
    via whichever model actually provides that shape natively (see `_shape_default_source`), so
    the field is already present on the first try.
    """
    for f in attrs_fields(model_cls):
        if f.name == name:
            return f.default
    for override in (*MASS_SHAPE_OVERRIDES.values(), CONVERTER_COST_OVERRIDE):
        for field_name, default in override.new_fields:
            if field_name == name:
                return default
    raise AttributeError(f"{model_cls.__name__} has no field '{name}'")


def _r_squared(y: np.ndarray, y_pred: np.ndarray) -> float:
    ss_res = np.sum((y - y_pred) ** 2)
    ss_tot = np.sum((y - np.mean(y)) ** 2)
    if ss_tot == 0:
        return 1.0 if ss_res == 0 else float("nan")
    return float(1.0 - ss_res / ss_tot)


def _plausibility_grid(spec: MassFitSpec, reference_cache: dict) -> np.ndarray:
    """The realistic x-range :py:mod:`csm.tools.experimental.plotting` itself would naturally
    sweep for `spec`'s independent variable (per `spec.domain`), used to sanity-check a fit
    against real-world turbine sizes rather than just its own (possibly very narrow, for a
    data-scarce component) observed data range — a fit can interpolate its handful of points
    perfectly while still being invalid at the ordinary rotor diameters the comparison plots
    actually cover.
    """
    entries = None
    if spec.domain == "tower_composite":
        entries = [e for cache in reference_cache.values() for e in cache.values() if e is not None]
        xs = [e["tower_length"] * math.pi * (e["rotor_diameter"] / 2) ** 2 for e in entries]
        lo, hi = min(xs), max(xs)
    elif spec.domain == "blade_mass_rating":
        entries = [e for cache in reference_cache.values() for e in cache.values() if e is not None]
        xs = [e["blade_mass"] * e["rated_power_kw"] / 1e3 for e in entries]
        lo, hi = min(xs), max(xs)
    else:
        lo, hi = _driver_range(reference_cache, spec.domain)
    return np.linspace(lo, hi, 50)


def _fit_mass_component(
    label: str,
    mass_fit_specs: dict[str, MassFitSpec],
    shape_default_sources: dict[str, type],
    empirical_df: pd.DataFrame | None,
    base_kwargs: dict,
    blade_params: dict[str, float] | None,
    plausibility_grid: np.ndarray,
) -> FitResult:
    """Fits `label`'s mass coefficients (per `mass_fit_specs`) against every empirical row for it
    with a usable mass value.

    A single data point is treated as insufficient to fit *any* new scaling relationship from
    (see :py:data:`MIN_MASS_FIT_POINTS`) — inherits `shape_default_sources[label]`'s complete,
    unmodified curve instead (the model whose coefficients actually match `label`'s resolved
    shape — see `_shape_default_source`), rather than solving for the one coefficient a single
    point happens to be able to determine, which risks an extrapolation nothing else constrains.
    With at least two points, `n_free = min(len(params), n_points)` coefficients are freed
    (highest fit-priority first per `MassFitSpec.params`'s order) and any remaining ones are held
    at that same default, so a fit with still-too-little data to move every coefficient just
    reproduces the default for the rest rather than something arbitrary.
    """
    spec = mass_fit_specs[label]
    defaults_source = shape_default_sources[label]
    defaults = {p: _default_coeff(defaults_source, p) for p in spec.params}
    component = next(c for c in ALL_COMPONENTS if c.label == label)
    rows = _empirical_rows(empirical_df, component)
    if rows is None:
        return FitResult(label, "mass", defaults, None, 0, "inherited (no data)")

    xs, ys = [], []
    for _, row in rows.iterrows():
        mass = pd.to_numeric(row.get(EMPIRICAL_MASS_COLUMN), errors="coerce")
        if pd.isna(mass):
            continue
        entry = _derive_empirical_entry(row, base_kwargs)
        if label in NEEDS_BLADE_MASS and "rotor_diameter" in entry:
            blade_spec = mass_fit_specs["Blade"]
            blade_source = shape_default_sources["Blade"]
            blade_p = blade_params or {
                p: _default_coeff(blade_source, p) for p in blade_spec.params
            }
            blade_mass_val = blade_spec.formula(
                entry["rotor_diameter"], *[blade_p[p] for p in blade_spec.params]
            )
            entry = {**entry, "_blade_mass": blade_mass_val}
            if "rated_power_kw" in entry:
                entry["_blade_mass_rating"] = blade_mass_val * entry["rated_power_kw"] / 1e3
        x = spec.x_from_entry(entry)
        if x is None:
            continue
        xs.append(x)
        ys.append(float(mass))

    n_points = len(xs)
    if n_points == 0:
        return FitResult(label, "mass", defaults, None, 0, "inherited (no data)")
    if n_points < MIN_MASS_FIT_POINTS:
        return FitResult(
            label,
            "mass",
            defaults,
            None,
            n_points,
            f"sample size too low (n={n_points}) to fit a new scaling relationship, "
            f"inherited {defaults_source.__name__}'s curve unchanged",
        )

    xs_arr, ys_arr = np.array(xs, dtype=float), np.array(ys, dtype=float)
    n_free = min(len(spec.params), n_points)
    free_params = spec.params[:n_free]
    fixed_params = spec.params[n_free:]

    def wrapped(x, *free_values):
        values = dict(zip(free_params, free_values, strict=True))
        values.update({p: defaults[p] for p in fixed_params})
        return spec.formula(x, *(values[p] for p in spec.params))

    p0 = [defaults[p] for p in free_params]
    try:
        popt, _ = curve_fit(wrapped, xs_arr, ys_arr, p0=p0, maxfev=20000)
    except RuntimeError:
        return FitResult(label, "mass", defaults, None, n_points, "fit failed, inherited")

    fitted = dict(zip(free_params, popt, strict=True))
    fitted.update({p: defaults[p] for p in fixed_params})

    # A fit with little data to constrain it (few points relative to free params) can still be an
    # exact/near-exact match to those points while being wildly wrong just beyond them — e.g. a
    # 3-point exact quadratic fit from narrow-range data (this repo's Low Speed Shaft rows all sit
    # under 100m rotor diameter) that dips negative at the 150m+ diameters the comparison plots
    # actually sweep. Reject anything that produces a negative or non-finite mass rather than
    # shipping a coefficient nothing can evaluate; the base model's value is used instead.
    #
    # The check only runs across a multiplicative margin around xs_arr's *own* observed range,
    # not the full plausibility_grid unconditionally — plausibility_grid spans every
    # DEFAULT_TURBINE_SPECS config (now including legacy sub-2MW COWER reference turbines a
    # modern-turbine component like Hub was never remotely measured at), and a fit that's
    # perfectly sound near its own data can still — correctly — go unphysical when extrapolated
    # that many multiples beyond it. Rejecting the *entire* fit over that distant a point would
    # throw away real empirical evidence just because one comparison config sits in a regime
    # nothing in this component's data was ever measured at; CSMBase's own runtime validation
    # already handles a config that far outside a fit's support on its own, per model *and* per
    # configuration (comes back "n/a" rather than silently extrapolating — see e.g.
    # Land2020NLR/Land2021NLR at the smallest COWER configs). MASS_FIT_PLAUSIBILITY_MARGIN is
    # generous enough to still catch the motivating Low Speed Shaft case above (roughly a 1.5-1.7x
    # extrapolation) while not rejecting Hub's fit purely because DEFAULT_TURBINE_SPECS spans
    # turbines ~9x smaller (by blade mass) than anything Hub was ever fit from.
    x_lo, x_hi = float(xs_arr.min()), float(xs_arr.max())
    check_lo, check_hi = x_lo / MASS_FIT_PLAUSIBILITY_MARGIN, x_hi * MASS_FIT_PLAUSIBILITY_MARGIN
    check_grid = plausibility_grid[
        (plausibility_grid >= check_lo) & (plausibility_grid <= check_hi)
    ]
    if check_grid.size == 0:
        check_grid = plausibility_grid
    predicted_check = spec.formula(check_grid, *(fitted[p] for p in spec.params))
    if not (np.all(np.isfinite(predicted_check)) and np.all(predicted_check >= 0)):
        return FitResult(
            label,
            "mass",
            defaults,
            None,
            n_points,
            "fit rejected (negative/invalid mass across realistic turbine range), inherited",
        )

    y_pred = wrapped(xs_arr, *popt)
    r2 = _r_squared(ys_arr, y_pred)
    if n_free < len(spec.params):
        status = f"fit (reduced: {n_free} of {len(spec.params)} params free)"
    elif n_points == n_free:
        status = "fit (exact, R² not meaningful — 0 residual d.o.f.)"
    else:
        status = "fit"
    return FitResult(label, "mass", fitted, r2, n_points, status)


def _fit_pitch_system_mass(
    empirical_df: pd.DataFrame | None,
    base_kwargs: dict,
    base_model_cls: type,
    pre_pitch_system_cls: type,
    plausibility_grid: np.ndarray,
) -> FitResult:
    """Fits Pitch System's mass so that Hub + Pitch System + Spinner (see
    :py:data:`csm.tools.experimental.plotting.WM_CATEGORY_MAPPING`'s "Hub and Pitch" grouping)
    matches empirical measurements as closely as possible — nothing in the CSV measures Pitch
    System's mass on its own (unlike Hub, which has its own direct rows), so its target is backed
    out of two *combined*-assembly measurements instead, pooled into one fit for maximum R².

    - "hub system" rows (Hub + Pitch System + Spinner combined) — target = row mass minus
      `pre_pitch_system_cls`'s own predicted Hub and (never separately measured, so always
      inherited) Spinner mass at that row's real inputs.
    - "rotor" rows (Blades x num_blades + Hub + Pitch System + Spinner, i.e. the full rotor
      assembly) — target = row mass minus num_blades x `pre_pitch_system_cls`'s predicted Blade
      mass, then the same Hub/Spinner subtraction. Far more numerous (broad real fleet, dozens of
      models spanning decades) than the "hub system" rows alone, so pooling both in gives this fit
      much more to go on — and, since `pre_pitch_system_cls` is the same model the rest of the
      pipeline actually runs (every other component's mass already fitted, only Pitch System still
      at its stock default), keeps this fit's target numerically consistent with the fully-
      assembled model's own `Rotor (Total)`/`Hub System` aggregate checks (see `AGGREGATE_CHECKS`)
      and lets a row invalid for reasons unrelated to Pitch System (e.g. a legacy sub-1MW "rotor"
      row outside this model's valid input range) drop out exactly the way it does everywhere else
      in this pipeline, rather than polluting the fit with a target hand-computed from a formula
      the real model would have refused to evaluate.

    Reduces to the exact same 2-parameter linear-in-blade-mass shape used for Hub
    (`pitch_system_mass = coeff * blade_mass + intercept`), fit by maximizing R² against the
    pooled target above, then mapped back onto whichever two of `base_model_cls`'s own fields
    give exactly that (coeff, intercept) once the other two are held at their inherited defaults
    (see `_pitch_system_shape` — `Land2020NLR` and `CSMBase`/`Land2015NLR` structurally override
    this formula with two *different* sets of field names for the same `outer*(inner*blade_mass*
    num_blades + inner_intercept) + offset` shape, so which field actually needs fitting to move
    the mass depends on which one `base_model_cls` is).
    """
    shape = _pitch_system_shape(base_model_cls)
    field_names = (shape.fit_field, shape.offset_field)
    defaults = {name: _default_coeff(base_model_cls, name) for name in field_names}
    num_blades = base_kwargs["num_blades"]

    def pooled_points(label: str, *, subtract_blades: bool) -> tuple[list[float], list[float]]:
        component = next(c for c in ALL_COMPONENTS if c.label == label)
        rows = _empirical_rows(empirical_df, component)
        if rows is None:
            return [], []
        xs, ys = [], []
        for _, row in rows.iterrows():
            mass = pd.to_numeric(row.get(EMPIRICAL_MASS_COLUMN), errors="coerce")
            if pd.isna(mass):
                continue
            entry = _derive_empirical_entry(row, base_kwargs)
            kwargs = dict(base_kwargs)
            for attr in ("rotor_diameter", "rated_power_kw", "tower_length"):
                if attr in entry:
                    kwargs[attr] = round(entry[attr]) if attr == "rated_power_kw" else entry[attr]
            try:
                model = pre_pitch_system_cls(**kwargs)
                model.run()
            except ValueError:
                continue
            blade_mass, hub_mass, spinner_mass = (
                model.blade_mass,
                model.hub_mass,
                model.spinner_mass,
            )
            if blade_mass is None or hub_mass is None or spinner_mass is None:
                continue
            target = float(mass) - hub_mass - spinner_mass
            if subtract_blades:
                target -= num_blades * blade_mass
            xs.append(blade_mass)
            ys.append(target)
        return xs, ys

    hub_system_xs, hub_system_ys = pooled_points("Hub System", subtract_blades=False)
    rotor_xs, rotor_ys = pooled_points("Rotor (Total)", subtract_blades=True)
    xs, ys = hub_system_xs + rotor_xs, hub_system_ys + rotor_ys
    n_hub_system, n_rotor = len(hub_system_xs), len(rotor_xs)

    if not xs:
        return FitResult("Pitch System", "mass", defaults, None, 0, "inherited (no data)")

    n_points = len(xs)
    if n_points < MIN_MASS_FIT_POINTS:
        return FitResult(
            "Pitch System",
            "mass",
            defaults,
            None,
            n_points,
            f"sample size too low (n={n_points}) to fit a new scaling relationship, inherited "
            f"{base_model_cls.__name__}'s curve unchanged",
        )

    xs_arr, ys_arr = np.array(xs, dtype=float), np.array(ys, dtype=float)
    try:
        (coeff, intercept), _ = curve_fit(
            lambda x, c, b: c * x + b,
            xs_arr,
            ys_arr,
            p0=[defaults[shape.fit_field], 0.0],
        )
    except RuntimeError:
        return FitResult("Pitch System", "mass", defaults, None, n_points, "fit failed, inherited")

    # Same plausibility guard as _fit_mass_component: reject a fit that goes negative anywhere
    # across a margin around the pooled rows' own blade-mass range, rather than shipping a
    # coefficient nothing beyond that data constrains.
    x_lo, x_hi = float(xs_arr.min()), float(xs_arr.max())
    check_lo, check_hi = x_lo / MASS_FIT_PLAUSIBILITY_MARGIN, x_hi * MASS_FIT_PLAUSIBILITY_MARGIN
    check_grid = plausibility_grid[
        (plausibility_grid >= check_lo) & (plausibility_grid <= check_hi)
    ]
    if check_grid.size == 0:
        check_grid = plausibility_grid
    predicted_check = coeff * check_grid + intercept
    if not (np.all(np.isfinite(predicted_check)) and np.all(predicted_check >= 0)):
        return FitResult(
            "Pitch System",
            "mass",
            defaults,
            None,
            n_points,
            "fit rejected (negative/invalid mass across realistic turbine range), inherited",
        )

    # Map the fitted (coeff, intercept) back onto base_model_cls's own fields, holding
    # shape.fixed_multiplier and shape.fixed_intercept (whichever of outer/inner isn't
    # shape.fit_field, plus the inner intercept) at their inherited defaults:
    # pitch_system_mass = outer*(inner*blade_mass*num_blades + inner_intercept) + offset
    #                    = (outer*inner*num_blades)*blade_mass + (outer*inner_intercept + offset)
    # so coeff = outer*inner*num_blades and intercept = outer*inner_intercept + offset. Whichever
    # of outer/inner is shape.fit_field solves to coeff / (fixed_multiplier * num_blades)
    # regardless of which role it plays, since the other factor is exactly fixed_multiplier
    # either way; outer itself is that fitted value when shape.fit_field plays the outer role, or
    # fixed_multiplier unchanged when it plays the inner role.
    fit_value = float(coeff) / (shape.fixed_multiplier * num_blades)
    outer = fit_value if shape.fit_is_outer else shape.fixed_multiplier
    fitted = {
        shape.fit_field: fit_value,
        shape.offset_field: float(intercept) - outer * shape.fixed_intercept,
    }
    y_pred = coeff * xs_arr + intercept
    r2 = _r_squared(ys_arr, y_pred)
    status = (
        f"fit (solved so Hub + Pitch System + Spinner matches n={n_hub_system} 'hub system' + "
        f"n={n_rotor} 'rotor' empirical points, pooled)"
        if n_points > len(field_names)
        else "fit (exact, R² not meaningful — 0 residual d.o.f.)"
    )
    return FitResult("Pitch System", "mass", fitted, r2, n_points, status)


def _benchmark_bin_points(benchmark_df: pd.DataFrame, category: str) -> pd.DataFrame | None:
    """One row per benchmark bin combination for `category`: capacity/RD/tower-height midpoints
    plus the bin's absolute cost in USD.

    Keeps all three raw bins (unlike :py:func:`csm.tools.experimental.plotting._benchmark_points`,
    which collapses to a single driver column for plotting) since a cost fit may need more than
    one of them at once — Tower's real driver is a composite of RD and tower height, and Gearbox's
    mass formula needs both RD and rated power to reconstruct rotor torque.
    """
    rows = benchmark_df[benchmark_df[BENCHMARK_ITEM_COLUMN] == category]
    if rows.empty:
        return None
    capacity_mid = _bin_midpoints(rows[BENCHMARK_CAPACITY_COLUMN].unique())
    rd_mid = _bin_midpoints(rows[BENCHMARK_RD_COLUMN].unique())
    tower_mid = _bin_midpoints(rows[BENCHMARK_TOWER_COLUMN].unique())
    out = rows.copy()
    out["rated_power_kw"] = out[BENCHMARK_CAPACITY_COLUMN].map(capacity_mid) * 1000.0
    out["rotor_diameter"] = out[BENCHMARK_RD_COLUMN].map(rd_mid)
    out["tower_length"] = out[BENCHMARK_TOWER_COLUMN].map(tower_mid)
    out["cost_usd"] = out[BENCHMARK_VALUE_COLUMN] * out["rated_power_kw"] / 1000.0
    return out


def _build_class(
    class_name: str,
    overrides: dict[str, float],
    docstring: str,
    base_model_cls: type,
    mass_fit_specs: dict[str, MassFitSpec],
) -> type:
    """Renders and `exec`s a `base_model_cls` subclass with `overrides` applied — the same source
    :py:func:`build_custom_model` would write to disk for a real result, used here to build a
    throwaway intermediate class (mass coefficients applied, no cost overrides yet) so the cost
    fit can run the model's own dependency chain rather than re-deriving it.
    """
    source = _render_model_source(class_name, overrides, docstring, base_model_cls, mass_fit_specs)
    namespace: dict = {}
    exec(compile(source, f"<{class_name}>", "exec"), namespace)
    return namespace[class_name]


def _restrict_to_realistic_range(
    points: pd.DataFrame, size_window: dict[str, tuple[float, float]]
) -> pd.DataFrame:
    """Keeps only benchmark bins within the padded range `csm.tools.experimental.plotting` itself
    sweeps for the comparison's actual reference turbines (see `_driver_range`) — a cost fit
    unrestricted to this spans the benchmark's full 1-10MW/<101-171+m extent, most of which
    nothing in this comparison resembles, and gets pulled away from the sizes that actually
    matter. Falls back to the unrestricted set if the window happens to exclude every row (should
    not normally happen given `_driver_range`'s own padding, but stay safe rather than fitting
    against nothing).
    """
    mask = pd.Series(data=True, index=points.index)
    for column, (lo, hi) in size_window.items():
        mask &= points[column].between(lo, hi)
    restricted = points[mask]
    return restricted if not restricted.empty else points


def _empirical_cost_points(
    label: str,
    field_name: str,
    empirical_df: pd.DataFrame | None,
    mass_fitted_cls: type,
    base_kwargs: dict,
    base_model_cls: type,
) -> tuple[list[float], list[float]] | None:
    """(regressors, costs) pairs for `label`'s own empirical CSV cost rows, or None if there's
    none usable.

    Each regressor is what `label`'s cost formula actually multiplies its own coefficient by at
    that row's real inputs — read back by dividing the model's own computed cost (at
    `mass_fitted_cls`'s *default* coefficient) by that same default, so a single coefficient
    `coeff = cost / regressor` reproduces a compound formula like Land2015NLR's native
    `gearbox_cost = mass * gearbox_torque_density * gearbox_torque_cost * 1e-3` or a power-based
    one (Controls/Electrical Connection) correctly, without special-casing either. Used both for
    an empirical-only fallback fit (no benchmark data for this component's category at all) and,
    normally, as one leaf's own rows feeding directly into :py:func:`_fit_cost_group`'s joint fit
    against the benchmark.
    """
    component = next(c for c in ALL_COMPONENTS if c.label == label)
    rows = _empirical_rows(empirical_df, component)
    if rows is None or EMPIRICAL_COST_COLUMN not in rows.columns:
        return None
    default = _default_coeff(base_model_cls, field_name)
    if not default:
        return None

    regressors, costs = [], []
    for _, row in rows.iterrows():
        cost = pd.to_numeric(row.get(EMPIRICAL_COST_COLUMN), errors="coerce")
        if pd.isna(cost):
            continue
        entry = _derive_empirical_entry(row, base_kwargs)
        kwargs = dict(base_kwargs)
        for attr in ("rotor_diameter", "rated_power_kw", "tower_length"):
            if attr in entry:
                kwargs[attr] = round(entry[attr]) if attr == "rated_power_kw" else entry[attr]
        model = mass_fitted_cls(**kwargs)
        with contextlib.suppress(ValueError):
            model.run()
        cost_at_default = getattr(model, component.cost_attr, None)
        if cost_at_default is None or cost_at_default <= 0:
            continue
        regressors.append(cost_at_default / default)
        costs.append(float(cost))

    return (regressors, costs) if regressors else None


def _fit_converter_cost(
    benchmark_df: pd.DataFrame | None,
    base_kwargs: dict,
    size_window: dict[str, tuple[float, float]],
) -> FitResult:
    """Fits Converter's cost as an affine function of turbine rating (`coeff * rating +
    intercept`) — unlike every other current cost formula's proportional-through-origin shape —
    directly against the 2026 benchmark's "Converter" category, restricted to the realistic-size
    window (see :py:func:`_restrict_to_realistic_range`). Handled as its own dedicated fit, not
    through :py:func:`_fit_cost_group`'s single-shared-scale-factor mechanism, since no existing
    model prices Converter as a function of turbine rating at all — there's no proportional
    formula (or starting coefficient) to scale in the first place, and the intercept is
    specifically what lets this one match the benchmark as closely as possible.
    """
    field_coeff, field_intercept = "converter_cost_coeff", "converter_cost_intercept"
    defaults = {field_coeff: 20.0, field_intercept: 0.0}
    if benchmark_df is None:
        return FitResult("Converter", "cost", defaults, None, 0, "inherited (no benchmark data)")
    points = _benchmark_bin_points(benchmark_df, "Converter")
    if points is None or points.empty:
        return FitResult("Converter", "cost", defaults, None, 0, "inherited (no benchmark data)")
    points = _restrict_to_realistic_range(points, size_window).dropna(subset=["cost_usd"])
    if points.empty:
        return FitResult("Converter", "cost", defaults, None, 0, "inherited (no benchmark data)")

    x = points["rated_power_kw"].to_numpy(dtype=float)
    y = points["cost_usd"].to_numpy(dtype=float)
    coeff, intercept = np.polyfit(x, y, 1)
    coeff = max(float(coeff), 0.0)  # cost shouldn't decrease with turbine size
    r2 = _r_squared(y, coeff * x + float(intercept))
    return FitResult(
        "Converter",
        "cost",
        {field_coeff: coeff, field_intercept: float(intercept)},
        r2,
        len(x),
        "fit (Converter, affine against turbine rating)",
    )


def _fit_cost_group(
    category: str,
    mapping: WMMapping,
    mass_fitted_cls: type,
    benchmark_df: pd.DataFrame | None,
    base_kwargs: dict,
    base_model_cls: type,
    size_window: dict[str, tuple[float, float]],
    empirical_df: pd.DataFrame | None,
) -> list[FitResult]:
    """Sets one coefficient per leaf component in `mapping.csm_components`. Two different rules
    apply depending on whether the category is a single component or a multi-leaf aggregate,
    because a single-leaf category's benchmark bins directly measure that one component's cost,
    while a multi-leaf category's benchmark bins are a lump sum across several components with no
    reliable way to split back apart.

    - **Single-leaf category** (e.g. Generator, Gearbox, Tower — see :py:func:`_fit_single_leaf_
      cost`): the leaf's own empirical rows and the benchmark bins are both genuine, independent,
      leaf-level cost evidence, so they're weighted **equally by point count** — one empirical row
      counts exactly as much as one (effective) benchmark bin, no special-casing for a single
      empirical point and no floor favoring either source.
    - **Multi-leaf category** (e.g. Hub and Pitch, Bearings and Shaft, Structure): a leaf with its
      own empirical rows is fit *purely* from them, with no benchmark influence at all — the
      benchmark's total can't be decomposed onto individual leaves without an arbitrary
      assumption, so a real per-part measurement is worth strictly more than a share of an
      aggregate nothing actually separates leaf-by-leaf. The benchmark instead drives only the
      leaves with no empirical data of their own, fit against the benchmark's *residual* — each
      bin's real cost minus what the already-fixed empirical leaves are predicted to cost there —
      so a leaf's own measurement is never double-counted through the benchmark as well. Uses one
      *shared* scale factor across those remaining leaves (independently decomposing several
      coefficients from one combined total is ill-posed whenever two leaves scale similarly with
      the same driver — a shared factor instead moves them together, preserving whatever relative
      cost weighting `base_model_cls` already encodes between them).

    Either way, `cost_aggregate_check` still validates the fully-assembled model against the
    benchmark's mid-range regardless of which leaves came from where, so a benchmark that
    disagrees with a leaf's empirical fit still shows up as a visible ratio, just never overrides
    the real data for a multi-leaf category's leaves.
    """
    leaves = [c for c in ALL_COMPONENTS if c.label in mapping.csm_components]
    field_names = {c.label: _cost_coeff_field_for(c.label, base_model_cls) for c in leaves}
    defaults = {
        label: _default_coeff(base_model_cls, field) for label, field in field_names.items()
    }

    empirical_points = {
        leaf.label: _empirical_cost_points(
            leaf.label,
            field_names[leaf.label],
            empirical_df,
            mass_fitted_cls,
            base_kwargs,
            base_model_cls,
        )
        for leaf in leaves
    }
    with_empirical = [leaf for leaf in leaves if empirical_points[leaf.label] is not None]
    without_empirical = [leaf for leaf in leaves if empirical_points[leaf.label] is None]

    def regressor_at(leaf: ComponentSpec, model, kwargs: dict) -> float:
        # Reads back what this leaf's cost formula actually multiplies its coefficient by, by
        # dividing the model's own cost (computed with mass_fitted_cls's *default* coefficient,
        # since no cost overrides are applied yet) by that same default — works uniformly for
        # every current shape, including compound ones where the "coefficient" isn't the
        # formula's only multiplicative factor (e.g. Land2015NLR's native gearbox_cost = mass *
        # gearbox_torque_density * gearbox_torque_cost * 1e-3 — density is already baked into the
        # model's own cost here, torque_cost is backed out cleanly) and power-based ones
        # (Controls/Electrical Connection multiply rated power, not mass) without needing to
        # special-case either.
        default = defaults[leaf.label]
        cost_at_default = getattr(model, leaf.cost_attr, None)
        value = (cost_at_default / default) if (cost_at_default is not None and default) else 0.0
        return value * _combined_cost_multiplier(leaf.label, mapping.multipliers, kwargs)

    target_attrs = [leaf.mass_attr for leaf in leaves]
    safe_kwargs = _safe_upstream_kwargs(mass_fitted_cls, base_kwargs, *target_attrs)

    bench_points = None
    if benchmark_df is not None:
        bench_points = _benchmark_bin_points(benchmark_df, category)
        if bench_points is not None and not bench_points.empty:
            bench_points = _restrict_to_realistic_range(bench_points, size_window)

    if len(leaves) == 1:
        return _fit_single_leaf_cost(
            leaves[0],
            category,
            mapping,
            field_names,
            defaults,
            empirical_points.get(leaves[0].label),
            bench_points,
            mass_fitted_cls,
            base_kwargs,
            safe_kwargs,
            regressor_at,
        )

    # Multi-leaf category. Step 1: each with-empirical leaf's coefficient, fit purely from its
    # own rows — a least-squares cost/regressor ratio (maximizing R²) for 2+ points, or the
    # single point taken exactly. Never touches the benchmark; computed first so Step 2 can
    # subtract these leaves' predicted cost out of the benchmark's total before fitting whatever
    # is left.
    empirical_coeffs: dict[str, float] = {}
    results: list[FitResult] = []
    for leaf in with_empirical:
        regressors, costs = empirical_points[leaf.label]
        regressors_arr = np.array(regressors, dtype=float)
        costs_arr = np.array(costs, dtype=float)
        coeff = float(np.sum(costs_arr * regressors_arr) / np.sum(regressors_arr**2))
        n_leaf_empirical = len(regressors)
        r2 = _r_squared(costs_arr, coeff * regressors_arr) if n_leaf_empirical > 1 else None
        empirical_coeffs[leaf.label] = coeff
        aside_note = (
            f", not blended with {category}'s benchmark data" if benchmark_df is not None else ""
        )
        status = (
            f"fit (empirical data, n={n_leaf_empirical}{aside_note})"
            if n_leaf_empirical > 1
            else f"fit (empirical data, 1 point — exact{aside_note})"
        )
        results.append(
            FitResult(
                leaf.label, "cost", {field_names[leaf.label]: coeff}, r2, n_leaf_empirical, status
            )
        )

    if not without_empirical:
        # Every leaf in this group has its own empirical data — nothing left for the benchmark
        # to inform.
        return results

    # Step 2: one shared scale factor for the leaves with no empirical data of their own, fit
    # against the benchmark's *residual* — each bin's real cost minus what Step 1's leaves are
    # already predicted to cost there — so their real measurements are never counted a second
    # time through the benchmark as well.
    residual_contribution, residual_targets = [], []
    n_benchmark_used = 0
    if bench_points is not None and not bench_points.empty:
        for _, row in bench_points.iterrows():
            if pd.isna(row["cost_usd"]):
                continue
            kwargs = {**base_kwargs, **safe_kwargs}
            kwargs["rotor_diameter"] = row["rotor_diameter"]
            kwargs["rated_power_kw"] = round(row["rated_power_kw"])
            kwargs["tower_length"] = row["tower_length"]
            model = mass_fitted_cls(**kwargs)
            with contextlib.suppress(ValueError):
                model.run()
            fixed_cost = sum(
                empirical_coeffs[leaf.label] * regressor_at(leaf, model, kwargs)
                for leaf in with_empirical
            )
            residual_contribution.append(
                sum(
                    defaults[leaf.label] * regressor_at(leaf, model, kwargs)
                    for leaf in without_empirical
                )
            )
            residual_targets.append(float(row["cost_usd"]) - fixed_cost)
            n_benchmark_used += 1

    s_bench = None
    r2_bench = None
    if n_benchmark_used:
        baseline_arr = np.array(residual_contribution, dtype=float)
        target_arr = np.array(residual_targets, dtype=float)
        if np.max(baseline_arr) <= 1e-9:
            # Every remaining leaf's mass is ~0 in every bin (e.g. High Speed Shaft, always
            # unmodeled) — nothing to scale against.
            n_benchmark_used = 0
        else:
            # Clipped at 0 rather than left negative: a residual target that's already negative
            # (the empirical leaves alone predict more than the bin's whole real cost) means the
            # data sources disagree, not that the remaining leaves have negative cost.
            s_bench = max(float(np.sum(target_arr * baseline_arr) / np.sum(baseline_arr**2)), 0.0)
            r2_bench = _r_squared(target_arr, s_bench * baseline_arr)

    # R² here is measured only across the realistic-size window (B3), which is deliberately
    # narrow — by design there's much less bin-to-bin variation left to explain than across the
    # benchmark's full 1-10MW extent, so a low or even negative R² doesn't mean the fit is
    # centered poorly (see the cost_aggregate_check rows below for that — the ratio there is the
    # meaningful "does this land near the benchmark's mid-range" signal). It does still mean the
    # shared coefficient isn't capturing whatever real size-dependence remains within that narrow
    # window, which is worth flagging rather than leaving implicit in the number alone.
    low_r2_note = ""
    if r2_bench is not None and r2_bench < 0.0:
        low_r2_note = (
            " — low R² within the realistic-size window (check cost_aggregate_check for centering)"
        )

    residual_note = (
        f", net of {' and '.join(leaf.label for leaf in with_empirical)}'s own empirical fit"
        if with_empirical
        else ""
    )

    for leaf in without_empirical:
        if s_bench is None:
            status = (
                "inherited (no benchmark data)"
                if n_benchmark_used == 0 and (bench_points is None or bench_points.empty)
                else "inherited (mass always ~0 for this component, nothing to fit)"
            )
            results.append(
                FitResult(
                    leaf.label,
                    "cost",
                    {field_names[leaf.label]: defaults[leaf.label]},
                    None,
                    0,
                    status,
                )
            )
        else:
            results.append(
                FitResult(
                    leaf.label,
                    "cost",
                    {field_names[leaf.label]: s_bench * defaults[leaf.label]},
                    r2_bench,
                    n_benchmark_used,
                    f"fit (group: {category}{residual_note}){low_r2_note}",
                )
            )

    return results


def _fit_single_leaf_cost(
    leaf: ComponentSpec,
    category: str,
    mapping: WMMapping,
    field_names: dict[str, str],
    defaults: dict[str, float],
    empirical: tuple[list[float], list[float]] | None,
    bench_points: pd.DataFrame | None,
    mass_fitted_cls: type,
    base_kwargs: dict,
    safe_kwargs: dict,
    regressor_at,
) -> list[FitResult]:
    """The single-leaf-category half of :py:func:`_fit_cost_group`: `leaf`'s own empirical rows
    (if any) and the category's benchmark bins are both direct, independent cost evidence for
    this exact component — no aggregate to decompose, unlike a multi-leaf category — so they're
    weighted equally by point count rather than one categorically overriding the other.
    """
    baseline_contribution, targets, driver_values = [], [], []
    n_benchmark_used = 0
    if bench_points is not None and not bench_points.empty:
        for _, row in bench_points.iterrows():
            if pd.isna(row["cost_usd"]):
                continue
            kwargs = {**base_kwargs, **safe_kwargs}
            kwargs["rotor_diameter"] = row["rotor_diameter"]
            kwargs["rated_power_kw"] = round(row["rated_power_kw"])
            kwargs["tower_length"] = row["tower_length"]
            model = mass_fitted_cls(**kwargs)
            with contextlib.suppress(ValueError):
                model.run()
            baseline_contribution.append(defaults[leaf.label] * regressor_at(leaf, model, kwargs))
            targets.append(float(row["cost_usd"]))
            driver_values.append(row[mapping.driver])
            n_benchmark_used += 1

    # The benchmark's *effective* sample size: the number of *distinct* values of `mapping.
    # driver`'s own bin (the one axis this category's benchmark cost genuinely varies along)
    # rather than the full row count `_benchmark_bin_points` returns (every capacity x
    # rotor-diameter x tower-height combination, which crosses a handful of real capacity classes
    # against many redundant RD/tower bins at each one — treating that raw row count as sample
    # size would drown out even a well-populated empirical leaf by two orders of magnitude). The
    # full row set is still used below to fit `s_bench` itself, for regression stability; it's
    # specifically the *weight against empirical* that needs the effective count instead.
    n_benchmark_effective = len(set(driver_values))

    s_bench = None
    r2_bench = None
    if n_benchmark_used:
        baseline_arr = np.array(baseline_contribution, dtype=float)
        target_arr = np.array(targets, dtype=float)
        if np.max(baseline_arr) <= 1e-9:
            n_benchmark_used = 0
            n_benchmark_effective = 0
        else:
            s_bench = max(float(np.sum(target_arr * baseline_arr) / np.sum(baseline_arr**2)), 0.0)
            r2_bench = _r_squared(target_arr, s_bench * baseline_arr)

    low_r2_note = ""
    if r2_bench is not None and r2_bench < 0.0:
        low_r2_note = (
            " — low R² within the realistic-size window (check cost_aggregate_check for centering)"
        )

    if empirical is None:
        if s_bench is None:
            status = (
                "inherited (no benchmark data)"
                if n_benchmark_used == 0 and (bench_points is None or bench_points.empty)
                else "inherited (mass always ~0 for this component, nothing to fit)"
            )
            return [
                FitResult(
                    leaf.label,
                    "cost",
                    {field_names[leaf.label]: defaults[leaf.label]},
                    None,
                    0,
                    status,
                )
            ]
        return [
            FitResult(
                leaf.label,
                "cost",
                {field_names[leaf.label]: s_bench * defaults[leaf.label]},
                r2_bench,
                n_benchmark_used,
                f"fit ({category}){low_r2_note}",
            )
        ]

    regressors, costs = empirical
    regressors_arr = np.array(regressors, dtype=float)
    costs_arr = np.array(costs, dtype=float)
    empirical_coeff = float(np.sum(costs_arr * regressors_arr) / np.sum(regressors_arr**2))
    n_leaf_empirical = len(regressors)
    r2_empirical = (
        _r_squared(costs_arr, empirical_coeff * regressors_arr) if n_leaf_empirical > 1 else None
    )

    if s_bench is None:
        coeff, r2, n_points = empirical_coeff, r2_empirical, n_leaf_empirical
        status = (
            f"fit (empirical data, n={n_leaf_empirical}, no benchmark data for {category})"
            if n_leaf_empirical > 1
            else f"fit (empirical data, 1 point — exact, no benchmark data for {category})"
        )
        return [
            FitResult(leaf.label, "cost", {field_names[leaf.label]: coeff}, r2, n_points, status)
        ]

    bench_only_coeff = s_bench * defaults[leaf.label]
    # Equal weight per point — one empirical row counts exactly as much as one (effective)
    # benchmark bin, whether n_leaf_empirical is 1 or 20: n_leaf_empirical : n_benchmark_effective,
    # no floor, no special-casing for a single point. Both sides are direct, independent
    # measurements of this same leaf's cost (unlike a multi-leaf category's benchmark total, which
    # can't be trusted at the individual-leaf level at all — see _fit_cost_group's docstring), so
    # there's no principled reason for one to categorically outweigh the other beyond how many
    # independent observations each actually contributes.
    total_n = n_leaf_empirical + n_benchmark_effective
    coeff = (
        n_leaf_empirical * empirical_coeff + n_benchmark_effective * bench_only_coeff
    ) / total_n
    status = (
        f"fit ({category}: {n_leaf_empirical} empirical @ {empirical_coeff:.4g}/unit + "
        f"{n_benchmark_effective} distinct benchmark {mapping.driver} bins ({n_benchmark_used} "
        f"rows total) @ {bench_only_coeff:.4g}/unit, weighted {n_leaf_empirical}:"
        f"{n_benchmark_effective} by point count){low_r2_note}"
    )
    return [
        FitResult(
            leaf.label,
            "cost",
            {field_names[leaf.label]: coeff},
            r2_bench,
            n_leaf_empirical + n_benchmark_used,
            status,
        )
    ]


def _fit_aggregate_check(
    label: str,
    mass_attr: str,
    empirical_df: pd.DataFrame | None,
    base_kwargs: dict,
    model_cls: type,
) -> FitResult:
    """Validates (does not fit) `mass_attr` — a sum with no coefficients of its own — against
    `label`'s empirical rows, by running the fully-assembled `model_cls` at each row's real inputs
    and comparing its bottom-up total to the row's measured mass.
    """
    component = next(c for c in ALL_COMPONENTS if c.label == label)
    rows = _empirical_rows(empirical_df, component)
    if rows is None:
        return FitResult(label, "aggregate_check", {}, None, 0, "no data")

    predicted, observed = [], []
    for _, row in rows.iterrows():
        mass = pd.to_numeric(row.get(EMPIRICAL_MASS_COLUMN), errors="coerce")
        if pd.isna(mass):
            continue
        entry = _derive_empirical_entry(row, base_kwargs)
        kwargs = dict(base_kwargs)
        for attr in ("rotor_diameter", "rated_power_kw", "tower_length"):
            if attr in entry:
                kwargs[attr] = round(entry[attr]) if attr == "rated_power_kw" else entry[attr]
        try:
            model = model_cls(**kwargs)
            model.run()
        except ValueError:
            continue
        value = getattr(model, mass_attr, None)
        if value is None:
            continue
        predicted.append(value)
        observed.append(float(mass))

    n_points = len(predicted)
    if n_points == 0:
        return FitResult(label, "aggregate_check", {}, None, 0, "no valid rows")
    r2 = _r_squared(np.array(observed), np.array(predicted))
    return FitResult(label, "aggregate_check", {}, r2, n_points, "validation only (not fit)")


# Every WM benchmark grouping worth checking the finished model's cost against: the 4 categories
# already calibrated directly (single- or multi-leaf), plus the two true roll-ups — reusing
# csm.tools.experimental.plotting.BENCHMARK_OVERLAY's own multi-category grouping for those
# instead of re-deriving it (e.g. "Turbine (Total)" = every category that feeds turbine_cost).
COST_AGGREGATE_CHECKS: dict[str, list[str]] = {
    "Blades": ["Blades"],
    "Gearbox": ["Gearbox"],
    "Generator": ["Generator"],
    "Tower": ["Tower"],
    "Converter": ["Converter"],
    "Hub and Pitch": ["Hub and Pitch"],
    "Bearings and Shaft": ["Bearings and Shaft"],
    "Structure": ["Structure"],
    "Balance of Nacelle": ["Balance of Nacelle"],
    "Nacelle (Total)": BENCHMARK_OVERLAY["Nacelle (Total)"][0],
    "Turbine (Total)": BENCHMARK_OVERLAY["Turbine (Total)"][0],
}

# The two roll-ups have a single model attribute that already sums everything underneath them —
# reading it directly is simpler and more consistent than re-summing leaf costs by hand.
_ROLLUP_COST_ATTR: dict[str, str] = {
    "Nacelle (Total)": "nacelle_cost",
    "Turbine (Total)": "turbine_cost",
}


def _fit_cost_aggregate_check(
    label: str,
    categories: list[str],
    model_cls: type,
    benchmark_df: pd.DataFrame | None,
    base_kwargs: dict,
    size_window: dict[str, tuple[float, float]],
) -> FitResult:
    """Validates (does not fit) how the fully-assembled `model_cls`'s bottom-up cost for `label`
    compares to `categories`' benchmark mid-range (median across their bins, restricted to the
    turbine sizes this comparison actually spans), evaluated at the single averaged reference
    configuration (`base_kwargs`) — the same "am I roughly in the WoodMac range" visibility for
    Nacelle (Total)/Turbine (Total) and every individual WM category, not just the ones with their
    own direct fit.
    """
    if benchmark_df is None:
        return FitResult(label, "cost_aggregate_check", {}, None, 0, "no benchmark data")

    target = 0.0
    n_total = 0
    for category in categories:
        points = _benchmark_bin_points(benchmark_df, category)
        if points is None:
            continue
        points = _restrict_to_realistic_range(points, size_window)
        target += float(points["cost_usd"].median())
        n_total += len(points)
    if n_total == 0:
        return FitResult(label, "cost_aggregate_check", {}, None, 0, "no benchmark data")

    model = model_cls(**base_kwargs)
    with contextlib.suppress(ValueError):
        model.run()

    rollup_attr = _ROLLUP_COST_ATTR.get(label)
    if rollup_attr is not None:
        predicted = getattr(model, rollup_attr, None)
    else:
        mapping = WM_CATEGORY_MAPPING[label]
        leaves = [c for c in ALL_COMPONENTS if c.label in mapping.csm_components]
        predicted = sum(
            (getattr(model, leaf.cost_attr, None) or 0.0)
            * _combined_cost_multiplier(leaf.label, mapping.multipliers, base_kwargs)
            for leaf in leaves
        )

    if predicted is None:
        return FitResult(
            label, "cost_aggregate_check", {}, None, n_total, "model couldn't compute this total"
        )
    ratio = predicted / target if target else float("nan")
    status = f"model ${predicted:,.0f} vs. benchmark mid-range ${target:,.0f} (ratio={ratio:.2f})"
    return FitResult(label, "cost_aggregate_check", {}, None, n_total, status)


def _class_name_for(model_name: str) -> str:
    """Derives a class name matching the repo's `Land<year>NLR` convention when `model_name`
    contains a plausible year (e.g. "nlr2026" -> "Land2026NLR"); otherwise falls back to a plain
    CamelCase of `model_name`.
    """
    match = re.search(r"(19|20)\d{2}", model_name)
    if match:
        return f"Land{match.group(0)}NLR"
    return "".join(part.capitalize() for part in re.split(r"[_\-]+", model_name)) + "Model"


def _render_model_source(
    class_name: str,
    overrides: dict[str, float],
    docstring: str,
    base_model_cls: type = Land2020NLR,
    mass_fit_specs: dict[str, MassFitSpec] | None = None,
) -> str:
    """Renders a `base_model_cls` subclass: a plain `.reuse(default=...)` line per entry in
    `overrides`, plus — for each override in :py:func:`_needed_structural_overrides` (any
    component in `mass_fit_specs` whose resolved shape isn't native to `base_model_cls`, plus
    Converter's cost, always) — one or more new fields, a replacement `calculate_*` method, and a
    `parameter_map` override in a generated `__attrs_post_init__`.
    """
    structural = _needed_structural_overrides(mass_fit_specs or {}, base_model_cls)
    structural_fields = {name for o in structural for name, _ in o.new_fields}

    # A structural field's fitted value (if any) is baked directly into its create_field(...)
    # declaration below, not emitted as a `.reuse()` line — base_model_cls has no such field to
    # reuse from at all (that's exactly why it's structural).
    def _override_line(name: str, value: float) -> str:
        one_line = f"    {name} = base.{name}.reuse(default={float(value)!r})"
        if len(one_line) <= 100:
            return one_line
        return f"    {name} = base.{name}.reuse(\n        default={float(value)!r}\n    )"

    override_lines = [
        _override_line(name, value)
        for name, value in overrides.items()
        if name not in structural_fields
    ]
    overrides_body = "\n".join(override_lines) if override_lines else "    pass"

    new_field_lines = "".join(
        f'    {field_name} = create_field(float, "unitless", "input", '
        f"default={float(overrides.get(field_name, default))!r})\n"
        for o in structural
        for field_name, default in o.new_fields
    )
    method_blocks = "\n".join(o.method_body for o in structural)

    post_init_block = ""
    if structural:
        param_map_lines = "".join(o.parameter_map_line for o in structural)
        post_init_block = (
            "\n    def __attrs_post_init__(self):\n"
            '        """Applies structural formula overrides not natively present on the base '
            'model."""\n'
            f"{param_map_lines}"
            "        super().__attrs_post_init__()\n"
        )

    base_module, base_name = base_model_cls.__module__, base_model_cls.__name__
    header = [
        '"""Auto-generated by build_custom_model.py — coefficients fit from empirical data.',
        "",
        *textwrap.wrap(docstring, width=100),
        "",
        *textwrap.wrap(
            "Do not hand-edit this file; rerun the fitting script instead so the model and its "
            "fit report stay in sync.",
            width=100,
        ),
        '"""',
        "",
    ]
    if any("math." in o.method_body for o in structural):
        header.append("import math")
    header.append("from attrs import define, fields")
    if structural:
        header.append("from csm.models.utils import create_field")
    header.append(f"from {base_module} import {base_name}")
    header += ["", ""]
    # Records which named shape ("2020"/"2015") each overridden component's formula actually
    # implements — read by csm.tools.experimental.plotting to resolve driver/formula-text display
    # for this generated class, since attrs subclasses inherit every parent field even when a
    # method is overridden to stop using some of them, which makes field-presence or issubclass()
    # alone unreliable for telling which shape a specific component's calculate_* method actually
    # implements (see csm.tools.experimental.plotting._generated_shape_overrides).
    shape_markers = {
        label: _shape_name(label, spec)
        for label, spec in (mass_fit_specs or {}).items()
        if spec is not _native_spec_for(label, base_model_cls)
    }
    if shape_markers:
        header.append(f"SHAPE_OVERRIDES = {shape_markers!r}")
        header += [""]
    header += [
        "",
        f"base = fields({base_name})",
        "",
        "",
        "@define",
        f"class {class_name}({base_name}):",
    ]
    class_docstring_text = (
        "Coefficients fit from empirical data; formula shapes are inherited from "
        f"`{base_name}` unless noted. See the accompanying fit report for what was fit vs. "
        "inherited, and from how many data points."
    )
    class_docstring_lines = textwrap.wrap(class_docstring_text, width=90)
    header.append('    """' + class_docstring_lines[0])
    header.extend("    " + line for line in class_docstring_lines[1:])
    header[-1] += '"""'
    header.append("")

    body = [line for line in (new_field_lines, overrides_body) if line]
    source = "\n".join(header) + "\n" + "\n".join(body)
    if method_blocks:
        source += "\n\n" + method_blocks
    if post_init_block:
        source += post_init_block
    return source + "\n"


def render_fit_report(report: list[FitResult], model_name: str | None) -> str:
    """Renders `report` (see :py:func:`build_custom_model`) as the plain-text table printed to
    the console and saved alongside a written model.
    """
    header = f"Fit report — {model_name or '(in-memory)'}"
    lines = [header, "=" * len(header), ""]
    lines.append(f"{'Component':<22}{'Kind':<17}{'Status':<48}{'R²':>8}{'n':>6}  Params")
    lines.append("-" * 130)
    for r in report:
        r2_str = f"{r.r_squared:.4f}" if r.r_squared is not None else "—"
        params_str = ", ".join(f"{k}={v:.6g}" for k, v in r.params.items())
        lines.append(
            f"{r.label:<22}{r.kind:<17}{r.status:<48}{r2_str:>8}{r.n_points:>6}  {params_str}"
        )
    return "\n".join(lines)


def build_custom_model(
    mass_csv: str | Path,
    benchmark_csv: str | Path | None = None,
    model_name: str | None = None,
    base_model_cls: type = Land2020NLR,
    shape_overrides: dict[str, type] | None = None,
    cost_coefficients: dict[str, float] | None = None,
    output_dir: str | Path = "output/custom_models",
) -> CustomModelResult:
    """Fits a new model from `mass_csv` (and, optionally, `benchmark_csv` for cost coefficients).

    Every component's mass formula defaults to `base_model_cls`'s shape (`Land2020NLR`, the
    latest model, unless overridden), but `shape_overrides` lets a specific component use a
    *different* model's shape instead — e.g. `{"Tower": Land2015NLR}` fits Tower's coefficients
    against `Land2015NLR`'s simpler hub-height-only formula while every other component still
    defaults to `Land2020NLR`'s. Cost fitting is unaffected by this choice: coefficients are
    always searched for against the benchmark data (including combinations of subsystems, e.g.
    "Bearings and Shaft" = Main Bearing + Low Speed Shaft + High Speed Shaft) regardless of which
    model each component's mass formula happens to be shaped like — see `_fit_cost_group`.

    Args:
        mass_csv: Empirical measurements CSV, same format as
            :py:func:`csm.tools.experimental.plotting.load_empirical_data`.
        benchmark_csv: Optional industry cost benchmark CSV, same format as
            :py:func:`csm.tools.experimental.plotting.load_benchmark_data`. Without it, every
            cost coefficient is inherited from `base_model_cls`.
        model_name: If given, the fitted model is written to `csm/models/<model_name>.py`
            (importable from there afterwards) using the repo's usual `nlr2015.py`/`nlr2020.py`
            subclass pattern. If None, the class is built in-memory only (nothing written to
            disk) via the exact same generated source, so the two modes can't drift apart.
        base_model_cls: The model whose formula shapes are used by default. Defaults to
            `Land2020NLR` (the latest model).
        shape_overrides: Optional per-component formula-shape source (keyed by `ComponentSpec`
            label, e.g. `"Tower"`), overriding `base_model_cls` for just that component's mass
            formula. Only combinations with a matching entry in `MASS_SHAPE_OVERRIDES` are
            supported when the requested shape isn't already native to `base_model_cls`.
        cost_coefficients: Optional user-supplied cost coefficients (keyed by field name, e.g.
            `"blade_mass_cost_coeff"`) that skip fitting for those specific components.
        output_dir: Where the rendered fit report is saved.

    Returns:
        CustomModelResult: the fitted model class, its class name, the file path it was written
            to (None for in-memory), and the full fit report.
    """
    base_kwargs = _base_config(DEFAULT_TURBINE_SPECS)
    empirical_df = _load_empirical_data(mass_csv)
    benchmark_df = _load_benchmark_data(benchmark_csv) if benchmark_csv else None
    reference_cache = _evaluate_all_configs(
        {"2015": Land2015NLR, "2020": Land2020NLR}, DEFAULT_TURBINE_SPECS
    )
    # The turbine sizes this comparison actually spans (DEFAULT_TURBINE_SPECS, padded the same way
    # csm.tools.experimental.plotting pads its own natural sweeps) — cost fits are
    # restricted/weighted to this window (see _restrict_to_realistic_range) rather than the
    # benchmark's full 1-10MW/<101-171+m extent.
    size_window = {
        "rated_power_kw": _driver_range(reference_cache, "rated_power_kw"),
        "rotor_diameter": _driver_range(reference_cache, "rotor_diameter"),
        "tower_length": _driver_range(reference_cache, "tower_length"),
    }
    mass_fit_specs = _resolve_mass_fit_specs(base_model_cls, shape_overrides)
    shape_default_sources = {
        label: _shape_default_source(label, spec, shape_overrides)
        for label, spec in mass_fit_specs.items()
    }

    report: list[FitResult] = []
    mass_params: dict[str, dict[str, float]] = {}
    for label in MASS_FIT_ORDER:
        spec = mass_fit_specs[label]
        result = _fit_mass_component(
            label,
            mass_fit_specs,
            shape_default_sources,
            empirical_df,
            base_kwargs,
            mass_params.get("Blade"),
            _plausibility_grid(spec, reference_cache),
        )
        mass_params[label] = result.params
        report.append(result)

    mass_overrides: dict[str, float] = {}
    for label in MASS_FIT_ORDER:
        mass_result = next(r for r in report if r.label == label and r.kind == "mass")
        if (
            mass_result.n_points > 0
            and mass_result.status.startswith("fit")
            and "rejected" not in mass_result.status
            and "failed" not in mass_result.status
        ):
            mass_overrides.update(mass_result.params)

    # An intermediate model with every OTHER component's fitted mass already applied (Pitch System
    # still at its stock default) — Pitch System has no empirical rows of its own, so it's fit
    # separately, against combined-assembly rows ("hub system", "rotor") that need Blade/Hub/
    # Spinner's real, model-consistent predicted mass backed out of them first. Running this
    # partial model per row (rather than reapplying each formula by hand) keeps that backed-out
    # target numerically identical to what the rest of the pipeline actually computes, and lets a
    # row that's invalid for reasons unrelated to Pitch System (e.g. a legacy sub-1MW "rotor" row
    # with inputs outside this model's valid range) drop out the same way it would anywhere else
    # (see the try/except ValueError below) instead of polluting the fit with a bad target.
    pre_pitch_system_cls = _build_class(
        "_PrePitchSystemIntermediate",
        mass_overrides,
        "Intermediate: mass overrides for every component except Pitch System, used internally "
        "while fitting Pitch System's own mass.",
        base_model_cls,
        mass_fit_specs,
    )
    pitch_system_result = _fit_pitch_system_mass(
        empirical_df,
        base_kwargs,
        base_model_cls,
        pre_pitch_system_cls,
        _plausibility_grid(mass_fit_specs["Hub"], reference_cache),
    )
    report.append(pitch_system_result)
    if (
        pitch_system_result.n_points > 0
        and pitch_system_result.status.startswith("fit")
        and "rejected" not in pitch_system_result.status
        and "failed" not in pitch_system_result.status
    ):
        mass_overrides.update(pitch_system_result.params)

    # An intermediate model with every fitted *mass* coefficient applied (no cost overrides yet)
    # — cost fitting runs this directly at each benchmark bin's inputs so every leaf component
    # (not just the ones with their own CSV mass data) gets a real, model-consistent predicted
    # mass to regress cost against.
    mass_fitted_cls = _build_class(
        "_MassFittedIntermediate",
        mass_overrides,
        "Intermediate: mass-only overrides, used internally while fitting cost coefficients.",
        base_model_cls,
        mass_fit_specs,
    )

    cost_coefficients = cost_coefficients or {}
    cost_overrides: dict[str, float] = {}
    # Cost is always searched for against the benchmark data — the mass-shape choices above never
    # change which WM categories are consulted or how subsystem combinations are summed. A leaf
    # with its own empirical cost data is fit purely from that, never the benchmark; the benchmark
    # only drives leaves with none of their own (see _fit_cost_group). Converter is handled
    # separately (see _fit_converter_cost) since its cost isn't proportional to mass at all —
    # there's no formula for it to inherit a shape/starting coefficient from.
    for category, mapping in WM_CATEGORY_MAPPING.items():
        if category == "Converter":
            continue
        leaf_labels = [label for label in mapping.csm_components if label in COST_COEFF_FIELD]
        if not leaf_labels:
            continue
        results = _fit_cost_group(
            category,
            mapping,
            mass_fitted_cls,
            benchmark_df,
            base_kwargs,
            base_model_cls,
            size_window,
            empirical_df,
        )
        for result in results:
            report.append(result)
            if result.status.startswith("fit"):
                cost_overrides.update(result.params)

    converter_result = _fit_converter_cost(benchmark_df, base_kwargs, size_window)
    report.append(converter_result)
    if converter_result.status.startswith("fit"):
        cost_overrides.update(converter_result.params)

    field_to_label = {
        _cost_coeff_field_for(label, base_model_cls): label for label in COST_COEFF_FIELD
    }
    for field_name, value in cost_coefficients.items():
        label = field_to_label.get(field_name, field_name)
        report.append(FitResult(label, "cost", {field_name: value}, None, 0, "user-supplied"))
        cost_overrides[field_name] = value

    overrides = {**mass_overrides, **cost_overrides}
    class_name = _class_name_for(model_name) if model_name else "CustomNLR"
    docstring = f"Fit from {Path(mass_csv).name}"
    if benchmark_csv:
        docstring += f" and {Path(benchmark_csv).name}"
    docstring += f". Mass formula shapes default to {base_model_cls.__name__}"
    if shape_overrides:
        overrides_text = ", ".join(
            f"{label}={cls.__name__}" for label, cls in shape_overrides.items()
        )
        docstring += f", except: {overrides_text}"
    docstring += "."
    source = _render_model_source(class_name, overrides, docstring, base_model_cls, mass_fit_specs)

    module_path: Path | None = None
    if model_name is not None:
        module_path = Path("csm/models") / f"{model_name}.py"
        module_path.write_text(source, encoding="utf-8")
        importlib.invalidate_caches()
        module_full_name = f"csm.models.{model_name}"
        if module_full_name in sys.modules:
            module = importlib.reload(sys.modules[module_full_name])
        else:
            module = importlib.import_module(module_full_name)
        model_cls = getattr(module, class_name)
    else:
        namespace: dict = {}
        exec(compile(source, f"<{class_name}>", "exec"), namespace)
        model_cls = namespace[class_name]

    for label, mass_attr in AGGREGATE_CHECKS.items():
        report.append(_fit_aggregate_check(label, mass_attr, empirical_df, base_kwargs, model_cls))
    for label, categories in COST_AGGREGATE_CHECKS.items():
        report.append(
            _fit_cost_aggregate_check(
                label, categories, model_cls, benchmark_df, base_kwargs, size_window
            )
        )

    output_dir = Path(output_dir) / (model_name or "custom")
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "fit_report.md").write_text(
        render_fit_report(report, model_name), encoding="utf-8"
    )

    return CustomModelResult(model_cls, class_name, module_path, report)


if __name__ == "__main__":
    result = build_custom_model(
        mass_csv="csm/tools/experimental/data/us_lbw_csm_2026_data.csv",
        benchmark_csv="csm/tools/experimental/data/WM_wind_capex_benchmark_data_geared.csv",
        model_name="nlr2026",
        # Every component defaults to Land2020NLR's (the latest model's) mass formula shape,
        # except Tower, which specifically uses Land2015NLR's simpler hub-height-only shape.
        # Bedplate also uses Land2015NLR's shape — not for the same reason as Tower, but because
        # it only has 1 empirical mass point (below MIN_MASS_FIT_POINTS): with no fit attempted,
        # this is what determines which model's curve it inherits unchanged (Main Bearing, the
        # other 1-point component, needs no entry here — it already defaults to Land2020NLR).
        shape_overrides={"Tower": Land2015NLR, "Bedplate": Land2015NLR},
    )
    # CLI entry point output, not a debug leftover.
    print(render_fit_report(result.report, "nlr2026"))  # noqa: T201
    print(f"\nWritten to: {result.module_path}")  # noqa: T201
