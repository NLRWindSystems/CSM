"""Cross-model comparison plots and slide deck generation for turbine component mass and cost.

For every turbine component (blade, hub, gearbox, tower, ...), this module sweeps the parameter
that actually drives that component's mass in each requested cost and scaling model, plots mass
vs. that driving parameter next to cost vs. mass, and marks a set of named turbine configurations
on every curve. Different models frequently use genuinely different formulas for the same
component (e.g. the 2015 brake mass is a function of rotor torque while the 2020 brake mass is a
function of turbine rating), so the number of "mass vs. driver" panels adapts automatically: one
panel per distinct driver among the models being compared.

Every x-axis is a turbine-level parameter — rotor diameter, hub height, or turbine rating — even
for components whose formula is actually written in terms of another component's mass (e.g. hub
mass depends on blade mass) or of rotor torque: those quantities are still computed from and
attributed to whichever root parameter(s) actually drive them (see :py:class:`CompositeDriver`
for the two-parameter cases, like the 2015 low speed shaft depending on blade mass times turbine
rating), and the panel title spells out that intermediate quantity's own formula so the whole
chain is traceable back to hub height / rotor diameter / turbine rating.

Every panel's axis limits are first set from the natural (padded) sweep range, then every curve is
redrawn stretched across those frozen limits so no line stops short of the plot box, and each
panel's title shows the literal formula (with live coefficient values) for every model drawn on
it. "Total" components (hub system, rotor, nacelle, turbine) get a plain-language list of what
they sum instead of a formula; the nacelle and turbine totals additionally skip drawing lines
altogether since their subcomponents don't share a single driving parameter, so a single swept
curve would be misleading (their markers are still shown).

It then saves one figure per component and assembles them into a slide deck with a final summary
table of every component's mass and cost for every configuration and model.

Which models are compared is an input (see :py:data:`DEFAULT_MODELS`), so new models (e.g. a
future empirically-fit "Custom" model) can be included simply by adding them to the ``models``
dictionary passed to :py:func:`generate_comparison` — no other changes are required. If a new
model doesn't override a component's ``calculate_*`` method, it inherits the base (2015) formula
and therefore its driver and formula text, via each lookup's fallback to the component's default.
"""

import math
import textwrap
from pathlib import Path
from typing import NamedTuple
from collections.abc import Callable

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from PIL import Image
from attrs import fields as attrs_fields
from pptx import Presentation
from pptx.util import Inches, Pt
from matplotlib.lines import Line2D
from matplotlib.ticker import FuncFormatter, MaxNLocator

from csm.models.nlr2015 import Land2015NLR
from csm.models.nlr2020 import Land2020NLR


class CompositeDriver(NamedTuple):
    """A driver whose displayed value is a combination of two real model attributes.

    The sweep varies `vary_attr` (a real, directly-overridable turbine-level attribute — e.g.
    ``rotor_diameter``) while holding everything else fixed at the base configuration, and
    `display_from_entry` computes the displayed x-axis value from the *actual* merged
    kwargs+results dictionary of a model run (whether that run came from the sweep or from a real
    named configuration). Because both the swept curve and each configuration's marker read this
    same real, model-computed dictionary (rather than a hand-derived closed-form substitution),
    markers land exactly on the curve whenever the model's mass is genuinely a function of the
    combined quantity `display_from_entry` represents.
    """

    key: str
    label: str
    units: str
    vary_attr: str
    display_from_entry: Callable[[dict], float]


Driver = str | CompositeDriver

LSS_LOAD_DRIVER = CompositeDriver(
    key="lss_load",
    label="Blade Mass × Turbine Rating",
    units="t·MW",
    vary_attr="rotor_diameter",
    display_from_entry=lambda entry: entry["blade_mass"] * entry["rated_power_kw"] * 1e-6,
)

TOWER_SWEPT_VOLUME_DRIVER = CompositeDriver(
    key="tower_swept_volume",
    label="Hub Height × Swept Area",
    units="m³",
    vary_attr="tower_length",
    display_from_entry=(
        lambda entry: entry["tower_length"] * math.pi * (entry["rotor_diameter"] / 2) ** 2
    ),
)


class ComponentSpec(NamedTuple):
    """Describes how to compute and plot a single turbine component.

    `default_driver` is the driver used for any model that isn't listed in
    :py:data:`COMPONENT_DRIVER_OVERRIDES` for this component's label — i.e. the driver implied by
    the base (:py:class:`~csm.models.base_model.CSMBase`) formula, which any model inherits unless
    it overrides the corresponding ``calculate_*`` method.
    """

    label: str
    mass_attr: str
    cost_attr: str
    default_driver: Driver
    has_mass_scaling: bool = True


# Component groupings follow the CSM's own subsystem breakdown (see `nacelle_mass`/`rotor_mass`
# in csm/models/base_model.py). Every driver below is (or, for composites, is built from) one of
# the three turbine-level parameters: rotor diameter, hub height, or turbine rating — even where a
# component's own formula is written in terms of another component's mass (blade mass, bedplate
# mass) or of rotor torque, since those are themselves fully determined by the root parameters
# once the other inputs (num_blades, efficiency, tip speed, ...) are held fixed at the sweep's
# base configuration. `COMPONENT_DRIVER_OVERRIDES` below captures the components where a model's
# actual formula uses a different (or combined) driver than the default.
ALL_COMPONENTS = [
    ComponentSpec("Blade", "blade_mass", "blade_cost", "rotor_diameter"),
    ComponentSpec("Hub", "hub_mass", "hub_cost", "rotor_diameter"),
    ComponentSpec("Pitch System", "pitch_system_mass", "pitch_system_cost", "rotor_diameter"),
    ComponentSpec("Spinner", "spinner_mass", "spinner_cost", "rotor_diameter"),
    ComponentSpec("Hub System", "hub_system_mass", "hub_system_cost", "rotor_diameter"),
    ComponentSpec("Rotor (Total)", "rotor_mass", "rotor_cost", "rotor_diameter"),
    ComponentSpec(
        "Low Speed Shaft", "low_speed_shaft_mass", "low_speed_shaft_cost", LSS_LOAD_DRIVER
    ),
    ComponentSpec("Main Bearing", "bearing_mass", "bearing_cost", "rotor_diameter"),
    ComponentSpec("Gearbox", "gearbox_mass", "gearbox_cost", "rotor_torque"),
    ComponentSpec("Brake", "brake_mass", "brake_cost", "rotor_torque"),
    ComponentSpec(
        "High Speed Shaft", "high_speed_shaft_mass", "high_speed_shaft_cost", "rated_power_kw"
    ),
    ComponentSpec("Generator", "generator_mass", "generator_cost", "rated_power_kw"),
    ComponentSpec("Bedplate", "bedplate_mass", "bedplate_cost", "rotor_diameter"),
    ComponentSpec("Yaw System", "yaw_system_mass", "yaw_system_cost", "rotor_diameter"),
    ComponentSpec(
        "Hydraulic Cooling", "hydraulic_cooling_mass", "hydraulic_cooling_cost", "rated_power_kw"
    ),
    ComponentSpec("Nacelle Cover", "nacelle_cover_mass", "nacelle_cover_cost", "rated_power_kw"),
    ComponentSpec(
        "Platform & Mainframe",
        "platform_mainframe_mass",
        "platform_mainframe_cost",
        "rotor_diameter",
    ),
    ComponentSpec("Transformer", "transformer_mass", "transformer_cost", "rated_power_kw"),
    ComponentSpec(
        "Converter", "converter_mass", "converter_cost", "rated_power_kw", has_mass_scaling=False
    ),
    ComponentSpec(
        "Controls", "controls_mass", "controls_cost", "rated_power_kw", has_mass_scaling=False
    ),
    ComponentSpec(
        "Electrical Connection",
        "electrical_connection_mass",
        "electrical_connection_cost",
        "rated_power_kw",
        has_mass_scaling=False,
    ),
    ComponentSpec("Nacelle (Total)", "nacelle_mass", "nacelle_cost", "rated_power_kw"),
    ComponentSpec("Tower", "tower_mass", "tower_cost", "tower_length"),
    ComponentSpec("Turbine (Total)", "turbine_mass", "turbine_cost", "rated_power_kw"),
]

PLOT_COMPONENTS = [c for c in ALL_COMPONENTS if c.has_mass_scaling]

# What each "total" component actually sums, shown as a subtitle instead of a formula.
AGGREGATE_COMPONENTS: dict[str, str] = {
    "Hub System": "Hub + Pitch System + Spinner",
    "Rotor (Total)": "Blades (× num_blades) + Hub System",
    "Nacelle (Total)": (
        "Low Speed Shaft + Main Bearing (× num_bearings) + Gearbox + Brake + High Speed Shaft + "
        "Generator + Bedplate + Yaw System + Hydraulic Cooling + Nacelle Cover + "
        "Platform & Mainframe (incl. Crane) + Transformer + Converter + Controls + "
        "Electrical Connection"
    ),
    "Turbine (Total)": "Rotor (Total) + Nacelle (Total) + Tower",
}

# "Total" components sum subcomponents that scale at different rates (even Hub System / Rotor
# (Total), whose subcomponents are all rotor-diameter driven but not at the same rate), so a
# single swept curve would misrepresent them. Markers are still shown for these; only the
# curve/reference lines are skipped.
NO_LINE_COMPONENTS: set[str] = set(AGGREGATE_COMPONENTS)

# Per-component, per-model-class driver overrides, keyed by component label then model class (not
# model name, since a model can be registered under any user-chosen name). Only deviations from a
# component's `default_driver` need an entry. A value of None means that model's mass is a
# constant for this component (no formula to sweep), so it contributes markers and a flat
# reference line but no swept curve.
COMPONENT_DRIVER_OVERRIDES: dict[str, dict[type, Driver | None]] = {
    "Low Speed Shaft": {Land2020NLR: "rotor_diameter"},
    "Brake": {Land2020NLR: "rated_power_kw"},
    "High Speed Shaft": {Land2020NLR: None},
    "Hydraulic Cooling": {Land2020NLR: None},
    "Tower": {Land2020NLR: TOWER_SWEPT_VOLUME_DRIVER},
}

# Display label, units, and a multiplier applied to the raw (model-native) value for plotting.
DRIVER_INFO: dict[str, tuple[str, str, float]] = {
    "rotor_diameter": ("Rotor Diameter", "m", 1.0),
    "rated_power_kw": ("Turbine Rating", "MW", 1e-3),
    "tower_length": ("Hub Height", "m", 1.0),
    "rotor_torque": ("Rotor Torque", "MN·m", 1e-3),
}

MASS_SCALE = 1e-3  # kg -> t, used for every mass axis
COST_SCALE = 1e-3  # USD -> $k, used for every cost axis


def _fmt_num(x: float) -> str:
    return f"{x:.4g}"


def _fmt_coef(x: float) -> str:
    """Formats a coefficient with an explicit sign, for use as a trailing "+ b" / "- b" term."""
    return f"{x:+.4g}"


def _coeff(model_cls: type, name: str) -> float:
    """Reads a model class's default (coefficient) value for one of its attrs fields."""
    for f in attrs_fields(model_cls):
        if f.name == name:
            return f.default
    raise AttributeError(f"{model_cls.__name__} has no field '{name}'")


def _resolve_mass_formula(component_label: str, model_cls: type) -> str:
    overrides = FORMULA_OVERRIDES.get(component_label, {})
    if model_cls in overrides:
        return overrides[model_cls](model_cls)
    template = FORMULA_DEFAULT.get(component_label)
    return template(model_cls) if template is not None else ""


def _blade_mass_definition(model_cls: type) -> str:
    """"m_blade = ..." line, reusing the Blade component's own formula for `model_cls`."""
    return _resolve_mass_formula("Blade", model_cls).replace("m = ", "m_blade = ", 1)


def _bedplate_mass_definition(model_cls: type) -> str:
    """"m_bedplate = ..." line, reusing the Bedplate component's own formula for `model_cls`."""
    return _resolve_mass_formula("Bedplate", model_cls).replace("m = ", "m_bedplate = ", 1)


# Rotor torque is a base-model (CSMBase) calculation shared unchanged by every model, so unlike
# m_blade/m_bedplate it needs no per-model coefficients to define.
TORQUE_DEFINITION = "τ = 0.5·P·D / (η·v_tip)"


# Mass formula text, matching the base (2015-inherited) `calculate_*_mass` implementations. Where
# a formula is written in terms of another component's mass or of rotor torque, a second line
# defines that quantity so the whole formula is traceable back to D (rotor diameter), H (hub
# height), and P (turbine rating).
FORMULA_DEFAULT: dict[str, Callable[[type], str]] = {
    "Blade": lambda cls: (
        f"m = {_fmt_num(_coeff(cls, 'blade_mass_coeff'))}·(D/2)^b  (b: 2.44–2.54 by class/carbon)"
    ),
    "Hub": lambda cls: (
        f"m = {_fmt_num(_coeff(cls, 'hub_mass_coeff'))}·m_blade "
        f"{_fmt_coef(_coeff(cls, 'hub_mass_intercept'))}\n{_blade_mass_definition(cls)}"
    ),
    "Pitch System": lambda cls: (
        f"m = (1+{_fmt_num(_coeff(cls, 'bearing_housing_fraction'))})·"
        f"({_fmt_num(_coeff(cls, 'pitch_bearing_mass_coeff'))}·n·m_blade "
        f"{_fmt_coef(_coeff(cls, 'pitch_bearing_mass_intercept'))}) "
        f"{_fmt_coef(_coeff(cls, 'mass_sys_offset'))}\n{_blade_mass_definition(cls)}"
    ),
    "Spinner": lambda cls: (
        f"m = {_fmt_num(_coeff(cls, 'spinner_mass_coeff'))}·D "
        f"{_fmt_coef(_coeff(cls, 'spinner_mass_intercept'))}"
    ),
    "Low Speed Shaft": lambda cls: (
        f"m = {_fmt_num(_coeff(cls, 'lss_mass_coeff'))}·x^{_fmt_num(_coeff(cls, 'lss_mass_exp'))} "
        f"{_fmt_coef(_coeff(cls, 'lss_mass_intercept'))}  (x = m_blade·P/1000)\n"
        f"{_blade_mass_definition(cls)}"
    ),
    "Main Bearing": lambda cls: (
        f"m = {_fmt_num(_coeff(cls, 'bearing_mass_coeff'))}·D^{_fmt_num(_coeff(cls, 'bearing_mass_exp'))}"
    ),
    "Gearbox": lambda cls: (
        f"m = 1000·τ / {_fmt_num(_coeff(cls, 'gearbox_torque_density'))}\n{TORQUE_DEFINITION}"
    ),
    "Brake": lambda cls: (
        f"m = 1000·{_fmt_num(_coeff(cls, 'brake_mass_coeff'))}·τ\n{TORQUE_DEFINITION}"
    ),
    "High Speed Shaft": lambda cls: f"m = {_fmt_num(_coeff(cls, 'hss_mass_coeff'))}·P",
    "Generator": lambda cls: (
        f"m = {_fmt_num(_coeff(cls, 'generator_mass_coeff'))}·P "
        f"{_fmt_coef(_coeff(cls, 'generator_mass_intercept'))}"
    ),
    "Bedplate": lambda cls: f"m = D^{_fmt_num(_coeff(cls, 'bedplate_mass_exp'))}",
    "Yaw System": lambda cls: (
        f"m = {_fmt_num(_coeff(cls, 'yaw_system_non_bearing_mass_coeff'))}·"
        f"({_fmt_num(_coeff(cls, 'yaw_system_mass_coeff'))}·"
        f"D^{_fmt_num(_coeff(cls, 'yaw_system_mass_exp'))})"
    ),
    "Hydraulic Cooling": lambda cls: f"m = {_fmt_num(_coeff(cls, 'hvac_mass_coeff'))}·P",
    "Nacelle Cover": lambda cls: (
        f"m = {_fmt_num(_coeff(cls, 'nacelle_cover_mass_coeff'))}·P "
        f"{_fmt_coef(_coeff(cls, 'nacelle_cover_mass_intercept'))}"
    ),
    "Platform & Mainframe": lambda cls: (
        f"m = {_fmt_num(_coeff(cls, 'platform_mainframe_mass_coeff'))}·m_bedplate + crane\n"
        f"{_bedplate_mass_definition(cls)}"
    ),
    "Transformer": lambda cls: (
        f"m = {_fmt_num(_coeff(cls, 'transformer_mass_coeff'))}·P "
        f"{_fmt_coef(_coeff(cls, 'transformer_mass_intercept'))}"
    ),
    "Tower": lambda cls: f"m = {_fmt_num(_coeff(cls, 'tower_mass_coeff'))}·H^{_fmt_num(_coeff(cls, 'tower_mass_exp'))}",
}

# Overrides for components whose 2020 `calculate_*_mass` structurally differs from the base.
FORMULA_OVERRIDES: dict[str, dict[type, Callable[[type], str]]] = {
    "Blade": {
        Land2020NLR: lambda cls: (
            f"m = {_fmt_num(_coeff(cls, 'blade_mass_coeff'))}·"
            f"(D/2)^{_fmt_num(_coeff(cls, 'blade_mass_exp'))}"
        ),
    },
    "Pitch System": {
        Land2020NLR: lambda cls: (
            f"m = {_fmt_num(_coeff(cls, 'pitch_system_mass_coeff'))}·"
            f"({_fmt_num(_coeff(cls, 'pitch_blade_mass_coeff'))}·n·m_blade "
            f"{_fmt_coef(_coeff(cls, 'pitch_blade_mass_intercept'))}) "
            f"{_fmt_coef(_coeff(cls, 'mass_sys_offset'))}\n{_blade_mass_definition(cls)}"
        ),
    },
    "Low Speed Shaft": {
        Land2020NLR: lambda cls: (
            f"m = {_fmt_num(_coeff(cls, 'lss_mass_coeff1'))}·D² "
            f"{_fmt_coef(_coeff(cls, 'lss_mass_coeff2'))}·D "
            f"{_fmt_coef(_coeff(cls, 'lss_mass_intercept'))}"
        ),
    },
    "Gearbox": {
        Land2020NLR: lambda cls: (
            f"m = {_fmt_num(_coeff(cls, 'gearbox_torque_density'))}·"
            f"τ^{_fmt_num(_coeff(cls, 'gearbox_torque_exp'))}\n{TORQUE_DEFINITION}"
        ),
    },
    "Brake": {
        Land2020NLR: lambda cls: (
            f"m = {_fmt_num(_coeff(cls, 'brake_mass_coeff'))}·P "
            f"{_fmt_coef(_coeff(cls, 'brake_mass_intercept'))}"
        ),
    },
    "High Speed Shaft": {
        Land2020NLR: lambda cls: "m = 0 (not modeled)",
    },
    "Bedplate": {
        Land2020NLR: lambda cls: (
            f"m = {_fmt_num(_coeff(cls, 'bedplate_mass_coeff'))}·D "
            f"{_fmt_coef(_coeff(cls, 'bedplate_mass_intercept'))}"
        ),
    },
    "Hydraulic Cooling": {
        Land2020NLR: lambda cls: (
            f"m = {_fmt_num(_coeff(cls, 'hydraulic_cooling_mass'))} kg (constant)"
        ),
    },
    "Platform & Mainframe": {
        Land2020NLR: lambda cls: (
            f"m = {_fmt_num(_coeff(cls, 'platform_mainframe_mass_coeff'))}·m_bedplate\n"
            f"{_bedplate_mass_definition(cls)}"
        ),
    },
    "Tower": {
        Land2020NLR: lambda cls: (
            f"m = {_fmt_num(_coeff(cls, 'tower_mass_coeff'))}·H·(π/4)·D² "
            f"{_fmt_coef(_coeff(cls, 'tower_mass_intercept'))}"
        ),
    },
}

DEFAULT_MODELS = {
    "2015": Land2015NLR,
    "2020": Land2020NLR,
}

# Example turbine configurations to mark on every curve. `turbine_class` and `blade_has_carbon`
# are not part of the ATB specs and are assumed (Class I, no carbon) via `to_model_kwargs`.
DEFAULT_TURBINE_SPECS = {
    "ATB T3 (3.3MW)": {
        "turbine_rating_MW": 3.3,
        "rotor_diameter": 148.0,
        "hub_height": 100.0,
        "tip_speed_max": 90.0,
        "num_bearings": 1,
        "num_blades": 3,
        "rotor_efficiency_max": 0.9,
        "BOS_cost": 0.0,
    },
    "ATB T1 (6.0MW)": {
        "turbine_rating_MW": 6.0,
        "rotor_diameter": 170.0,
        "hub_height": 115.0,
        "tip_speed_max": 90.0,
        "num_bearings": 1,
        "num_blades": 3,
        "rotor_efficiency_max": 0.9,
        "BOS_cost": 0.0,
    },
    "SG 5.2-165": {
        "turbine_rating_MW": 5.2,
        "rotor_diameter": 165.0,
        "hub_height": 105.0,
        "tip_speed_max": 90.0,
        "num_bearings": 1,
        "num_blades": 3,
        "rotor_efficiency_max": 0.9,
        "BOS_cost": 0.0,
    },
    "SG 7.0-170": {
        "turbine_rating_MW": 7.0,
        "rotor_diameter": 170.0,
        "hub_height": 135.0,
        "tip_speed_max": 90.0,
        "num_bearings": 1,
        "num_blades": 3,
        "rotor_efficiency_max": 0.9,
        "BOS_cost": 0.0,
    },
    "V150-4.5": {
        "turbine_rating_MW": 4.5,
        "rotor_diameter": 150.0,
        "hub_height": 105.0,
        "tip_speed_max": 82.0,
        "num_bearings": 1,
        "num_blades": 3,
        "rotor_efficiency_max": 0.9,
        "BOS_cost": 0.0,
    },
}

MODEL_COLORS = {"2015": "#4C72B0", "2020": "#DD5A48", "Custom": "#E8A33D"}
CONFIG_MARKERS = ["*", "^", "s", "D", "P", "X", "o"]


def to_model_kwargs(spec: dict) -> dict:
    """Converts a raw turbine specification into ``CSMBase`` subclass constructor kwargs.

    Args:
        spec (dict): Turbine specification with keys ``turbine_rating_MW``, ``rotor_diameter``,
            ``hub_height``, ``tip_speed_max``, ``num_bearings``, ``num_blades``, and
            ``rotor_efficiency_max``. Any ``BOS_cost`` key is ignored since it is not a model
            input.

    Returns:
        dict: Keyword arguments accepted by :py:class:`csm.models.nlr2015.Land2015NLR` and
            :py:class:`csm.models.nlr2020.Land2020NLR`.
    """
    return {
        "rated_power_kw": int(round(spec["turbine_rating_MW"] * 1000)),
        "rotor_diameter": float(spec["rotor_diameter"]),
        "tower_length": float(spec["hub_height"]),
        "max_tip_speed": float(spec["tip_speed_max"]),
        "num_bearings": int(spec["num_bearings"]),
        "num_blades": int(spec["num_blades"]),
        "efficiency_max": float(spec["rotor_efficiency_max"]),
        "turbine_class": int(spec.get("turbine_class", 1)),
        "blade_has_carbon": bool(spec.get("blade_has_carbon", False)),
    }


def _cast_driver_value(attr: str, value: float) -> int | float:
    """Casts a swept raw attribute value to the type the model constructor requires."""
    if attr == "rated_power_kw":
        return int(round(value))
    return float(value)


def _base_config(configs: dict[str, dict]) -> dict:
    """Computes a reference set of model kwargs by averaging the given configurations."""
    kwargs_list = [to_model_kwargs(spec) for spec in configs.values()]
    base = {}
    for key in kwargs_list[0]:
        values = [kw[key] for kw in kwargs_list]
        if isinstance(values[0], bool):
            base[key] = values[0]
        elif isinstance(values[0], int):
            base[key] = int(round(sum(values) / len(values)))
        else:
            base[key] = sum(values) / len(values)
    return base


def _resolve_driver(component: ComponentSpec, model_cls: type) -> Driver | None:
    """Returns the driver `model_cls` actually uses for `component`.

    Falls back to `component.default_driver` for any model class without an explicit entry in
    :py:data:`COMPONENT_DRIVER_OVERRIDES`, which is correct for any model that inherits the base
    formula (and therefore the base driver) for this component.
    """
    overrides = COMPONENT_DRIVER_OVERRIDES.get(component.label, {})
    if model_cls in overrides:
        return overrides[model_cls]
    return component.default_driver


def _driver_key(driver: Driver) -> str:
    return driver if isinstance(driver, str) else driver.key


def _driver_label_units(driver: Driver) -> tuple[str, str]:
    if isinstance(driver, str):
        label, units, _scale = DRIVER_INFO.get(driver, (driver, "", 1.0))
        return label, units
    return driver.label, driver.units


def _override_attr(driver: Driver) -> str:
    """The real model attribute that gets overridden while sweeping `driver`."""
    return driver if isinstance(driver, str) else driver.vary_attr


def _driver_display_value(driver: Driver, entry: dict) -> float | None:
    """Computes the display x-value for `driver` from a config-cache entry (merged kwargs +
    :py:meth:`CSMBase.get_results`).
    """
    if isinstance(driver, str):
        if driver not in entry:
            return None
        _label, _units, scale = DRIVER_INFO.get(driver, (driver, "", 1.0))
        return entry[driver] * scale
    try:
        return driver.display_from_entry(entry)
    except KeyError:
        return None


def _panel_drivers(component: ComponentSpec, models: dict[str, type]) -> list[Driver]:
    """Distinct drivers actually used by `models` for `component`, in first-seen order.

    A model whose resolved driver is None (a constant, unmodeled mass) contributes no panel.
    """
    seen_keys: list[str] = []
    drivers: list[Driver] = []
    for model_cls in models.values():
        driver = _resolve_driver(component, model_cls)
        if driver is None:
            continue
        key = _driver_key(driver)
        if key not in seen_keys:
            seen_keys.append(key)
            drivers.append(driver)
    return drivers


def _owners_for_driver(
    component: ComponentSpec, models: dict[str, type], driver: Driver
) -> dict[str, type]:
    """The subset of `models` whose resolved driver for `component` matches `driver`."""
    key = _driver_key(driver)
    owners = {}
    for name, cls in models.items():
        resolved = _resolve_driver(component, cls)
        if resolved is not None and _driver_key(resolved) == key:
            owners[name] = cls
    return owners


def _constant_models(component: ComponentSpec, models: dict[str, type]) -> dict[str, type]:
    """Models whose mass is a constant (no driver at all) for `component`."""
    return {name: cls for name, cls in models.items() if _resolve_driver(component, cls) is None}


def _evaluate_all_configs(
    models: dict[str, type], configs: dict[str, dict]
) -> dict[str, dict[str, dict | None]]:
    """Runs every model against every named configuration once.

    Returns:
        dict[str, dict[str, dict | None]]: Per-model, per-configuration dictionary merging that
            configuration's raw model kwargs with :py:meth:`CSMBase.get_results`, or None if the
            model raised while evaluating that configuration. Reused across figure generation and
            the summary report so every (model, configuration) pair is only computed once.
    """
    cache = {}
    for model_name, model_cls in models.items():
        cache[model_name] = {}
        for config_name, spec in configs.items():
            kwargs = to_model_kwargs(spec)
            try:
                model = model_cls(**kwargs)
                model.run()
                cache[model_name][config_name] = {**kwargs, **model.get_results()}
            except (ValueError, AttributeError, TypeError):
                cache[model_name][config_name] = None
    return cache


def _constant_value(model_name: str, config_cache: dict, attr: str) -> float | None:
    """Any one cached value of `attr` for `model_name` (they're all equal since it's constant)."""
    for entry in config_cache[model_name].values():
        if entry is not None and attr in entry:
            return entry[attr]
    return None


def _average_slope(model_name: str, config_cache: dict, component: ComponentSpec) -> float | None:
    """Average cost/mass ratio for `model_name` across all cached configurations.

    Exact for the vast majority of components (cost is a simple per-kg multiple of mass with no
    intercept), and a representative approximation for "total" components whose cost/mass ratio
    isn't perfectly constant since it's a sum of differently-scaling subcomponents. Unit-invariant
    (uniformly scaling both mass and cost by the same factor before plotting leaves this ratio
    unchanged), so it can be used directly against display-scaled ($k, t) axes.
    """
    ratios = [
        entry[component.cost_attr] / entry[component.mass_attr]
        for entry in config_cache[model_name].values()
        if entry is not None and entry.get(component.mass_attr)
    ]
    return sum(ratios) / len(ratios) if ratios else None


def _driver_range(
    config_cache: dict[str, dict[str, dict | None]], attr: str, pad: float = 0.15
) -> tuple[float, float]:
    """Computes a sweep range for raw attribute `attr`, padded around its spread across all cached
    (model, configuration) values.
    """
    values = [
        entry[attr]
        for model_entries in config_cache.values()
        for entry in model_entries.values()
        if entry is not None and attr in entry
    ]
    lo, hi = min(values), max(values)
    span = (hi - lo) or hi * 0.2
    return max(lo - span * pad, 1e-6), hi + span * pad


def _sweep_single(
    component: ComponentSpec,
    driver: Driver,
    model_cls: type,
    base_kwargs: dict,
    raw_range: tuple[float, float],
    n_points: int = 60,
) -> dict[str, np.ndarray]:
    """Sweeps `model_cls` across `raw_range` of `driver`'s underlying raw attribute.

    All non-driver model inputs are held fixed at `base_kwargs`.

    Returns:
        dict[str, np.ndarray]: "driver_display", "mass", "cost", "mass_sorted", and "cost_sorted"
            arrays. The sorted arrays are mass-ascending so the mass-vs-cost curve draws as a
            single line even if mass isn't perfectly monotonic in the driver.
    """
    override_attr = _override_attr(driver)
    raw_grid = np.linspace(*raw_range, n_points)
    masses = np.empty(n_points)
    costs = np.empty(n_points)
    display = np.empty(n_points)
    for i, raw_value in enumerate(raw_grid):
        kwargs = dict(base_kwargs)
        kwargs[override_attr] = _cast_driver_value(override_attr, raw_value)
        model = model_cls(**kwargs)
        model.run()
        masses[i] = getattr(model, component.mass_attr)
        costs[i] = getattr(model, component.cost_attr)
        if isinstance(driver, str):
            _label, _units, scale = DRIVER_INFO.get(driver, (driver, "", 1.0))
            display[i] = raw_value * scale
        else:
            display[i] = driver.display_from_entry({**kwargs, **model.get_results()})
    order = np.argsort(masses)
    return {
        "driver_display": display,
        "mass": masses,
        "cost": costs,
        "mass_sorted": masses[order],
        "cost_sorted": costs[order],
    }


def _sweep_curve(
    component: ComponentSpec,
    driver: Driver,
    owners: dict[str, type],
    base_kwargs: dict,
    raw_range: tuple[float, float],
    n_points: int = 60,
) -> dict[str, dict[str, np.ndarray]]:
    """Sweeps every model in `owners` over the same raw range. Used for the natural (pass-1)
    sweep, where the range comes purely from the configurations' spread and is shared regardless
    of model.
    """
    return {
        name: _sweep_single(component, driver, cls, base_kwargs, raw_range, n_points)
        for name, cls in owners.items()
    }


def _raw_range_for_display(
    component: ComponentSpec,
    driver: Driver,
    model_cls: type,
    base_kwargs: dict,
    display_bounds: tuple[float, float],
    search_raw_range: tuple[float, float],
) -> tuple[float, float]:
    """Inverts a (display_lo, display_hi) range back to raw `driver.vary_attr` values for
    `model_cls`: exact division for a simple (str) driver, or bisection (assuming a monotonic
    relationship, true of every current composite) for a :py:class:`CompositeDriver`, since a
    closed-form inverse would have to duplicate each model's own branching mass formula.
    """
    if isinstance(driver, str):
        _label, _units, scale = DRIVER_INFO.get(driver, (driver, "", 1.0))
        return display_bounds[0] / scale, display_bounds[1] / scale

    override_attr = _override_attr(driver)

    def display_at(raw_value: float) -> float:
        kwargs = dict(base_kwargs)
        kwargs[override_attr] = _cast_driver_value(override_attr, raw_value)
        model = model_cls(**kwargs)
        model.run()
        return driver.display_from_entry({**kwargs, **model.get_results()})

    results = []
    for target in display_bounds:
        lo, hi = search_raw_range
        d_lo, d_hi = display_at(lo), display_at(hi)
        tries = 0
        while d_hi < target and tries < 25:
            hi *= 1.5
            d_hi = display_at(hi)
            tries += 1
        tries = 0
        while d_lo > target and tries < 25:
            lo = max(lo / 1.5, 1e-6)
            d_lo = display_at(lo)
            tries += 1
        for _ in range(40):
            mid = (lo + hi) / 2
            if display_at(mid) < target:
                lo = mid
            else:
                hi = mid
        results.append((lo + hi) / 2)
    return tuple(results)


def _model_color(model_name: str, index: int) -> str:
    if model_name in MODEL_COLORS:
        return MODEL_COLORS[model_name]
    return plt.get_cmap("tab10").colors[index % 10]


def _fmt_mass(value: float, _pos=None) -> str:
    """Used only for the summary report table's cell text, not plot axes (see module docstring:
    axis units live in the axis label, not per-tick).
    """
    if abs(value) >= 1000:
        return f"{value / 1000:,.1f} t"
    return f"{value:,.0f} kg"


def _fmt_cost(value: float, _pos=None) -> str:
    """Used only for the summary report table's cell text; see :py:func:`_fmt_mass`."""
    if abs(value) >= 1e6:
        return f"${value / 1e6:,.1f}M"
    if abs(value) >= 1e3:
        return f"${value / 1e3:,.0f}k"
    return f"${value:,.0f}"


def _fmt_tick(value: float, _pos=None) -> str:
    """Plain, comma-delimited tick label (no unit — units live in the axis label) used on every
    plot axis, so large values (e.g. the tower's hub-height-x-swept-area composite, in the
    millions) read as "1,700,000" rather than matplotlib's default "1e6" offset notation.
    """
    if value == 0 or abs(value) >= 100:
        return f"{value:,.0f}"
    if abs(value) >= 1:
        return f"{value:,.1f}"
    return f"{value:,.2f}"


def _slugify(label: str) -> str:
    keep = "".join(c.lower() if c.isalnum() else "_" for c in label)
    while "__" in keep:
        keep = keep.replace("__", "_")
    return keep.strip("_")


def _draw_mass_panel(
    ax, component: ComponentSpec, driver: Driver, curves: dict, config_cache: dict,
    models: dict[str, type], configs: dict[str, dict], marker_map: dict, color_map: dict,
) -> None:
    if component.label not in NO_LINE_COMPONENTS:
        for model_name, data in curves.items():
            ax.plot(data["driver_display"], data["mass"] * MASS_SCALE, color=color_map[model_name], lw=2)
    for model_name in models:
        for config_name in configs:
            entry = config_cache[model_name].get(config_name)
            if entry is None:
                continue
            x = _driver_display_value(driver, entry)
            if x is None:
                continue
            ax.scatter(
                x, entry[component.mass_attr] * MASS_SCALE, marker=marker_map[config_name],
                color=color_map[model_name], s=110, edgecolor="black", linewidth=0.6, zorder=5,
            )


def _draw_cost_panel(
    ax, component: ComponentSpec, curves_by_key: dict, config_cache: dict,
    models: dict[str, type], configs: dict[str, dict], marker_map: dict, color_map: dict,
) -> None:
    if component.label not in NO_LINE_COMPONENTS:
        for curves in curves_by_key.values():
            for model_name, data in curves.items():
                ax.plot(
                    data["mass_sorted"] * MASS_SCALE, data["cost_sorted"] * COST_SCALE,
                    color=color_map[model_name], lw=2,
                )
    for model_name in models:
        for config_name in configs:
            entry = config_cache[model_name].get(config_name)
            if entry is None:
                continue
            ax.scatter(
                entry[component.mass_attr] * MASS_SCALE, entry[component.cost_attr] * COST_SCALE,
                marker=marker_map[config_name], color=color_map[model_name],
                s=110, edgecolor="black", linewidth=0.6, zorder=5,
            )


def _set_stacked_title(ax, lines: list[tuple[str, str]]) -> int:
    """Sets `ax`'s title to one "model: text" line per entry, stacked. Uses a real
    ``ax.set_title`` (rather than floating text) so :py:meth:`Figure.tight_layout` sizes the
    surrounding margins around it automatically instead of leaving a fixed, often oversized gap.

    Returns:
        int: The number of physical text lines set (some formulas span two lines themselves, e.g.
            a mass formula plus its "m_blade = ..." definition), so the caller can reserve enough
            headroom for the figure-level suptitle above the tallest panel title.
    """
    if not lines:
        return 0
    text = "\n".join(f"{model_name}: {formula}" for model_name, formula in lines)
    ax.set_title(text, fontsize=7.5, linespacing=1.6)
    return text.count("\n") + 1


def plot_component(
    component: ComponentSpec,
    models: dict[str, type],
    config_cache: dict[str, dict[str, dict | None]],
    base_kwargs: dict,
    configs: dict[str, dict],
    panel_width: float = 4.6,
    height: float = 5.8,
    n_points: int = 60,
):
    """Plots `component` mass vs. each driving parameter next to cost vs. mass.

    One mass panel is drawn per distinct driver among `models` for this component (adapting to
    however many different drivers they actually use), followed by a single shared mass-vs-cost
    panel. Every model is its own colored line and every named configuration is marked with a
    consistent marker shape on every panel. Axis limits are set from each panel's natural (padded)
    sweep range; every mass-panel curve — including a flat reference line for any model whose mass
    is a constant for this component — is then redrawn stretched across those frozen limits, and
    every cost-panel line is drawn as its own average cost/mass ratio spanning the full frozen
    cost-panel width (exact for ordinary components; an visibly-dashed approximation for "total"
    components, whose cost/mass ratio isn't perfectly constant), so every line reaches the edges
    of its panel regardless of how differently two models' mass ranges happen to fall. Each
    panel's title shows the literal formula (with live coefficient values) for every model drawn
    there, including a defining line for any intermediate quantity (blade mass, bedplate mass,
    rotor torque) the formula is written in terms of; "total" components show what they sum
    instead, and the nacelle/turbine totals skip lines entirely (see module docstring).

    Returns:
        matplotlib.figure.Figure: The multi-panel figure.
    """
    panel_drivers = _panel_drivers(component, models)
    n_left = len(panel_drivers)
    n_panels = n_left + 1
    fig, axes = plt.subplots(1, n_panels, figsize=(panel_width * n_panels, height))
    axes = list(np.atleast_1d(axes))
    mass_axes = axes[:n_left]
    ax_cost = axes[-1]

    config_names = list(configs)
    marker_map = {
        name: CONFIG_MARKERS[i % len(CONFIG_MARKERS)] for i, name in enumerate(config_names)
    }
    model_names = list(models)
    color_map = {name: _model_color(name, i) for i, name in enumerate(model_names)}
    constant_models = _constant_models(component, models)
    is_aggregate = component.label in AGGREGATE_COMPONENTS
    show_lines = component.label not in NO_LINE_COMPONENTS

    # ---- pass 1: natural (padded) ranges, draw curves + markers, then capture axis limits ----
    natural_curves: dict[str, dict] = {}
    owners_by_key: dict[str, dict[str, type]] = {}
    natural_raw_ranges: dict[str, tuple[float, float]] = {}
    for ax, driver in zip(mass_axes, panel_drivers):
        owners = _owners_for_driver(component, models, driver)
        owners_by_key[_driver_key(driver)] = owners
        raw_range = _driver_range(config_cache, _override_attr(driver))
        natural_raw_ranges[_driver_key(driver)] = raw_range
        curves = _sweep_curve(component, driver, owners, base_kwargs, raw_range, n_points)
        natural_curves[_driver_key(driver)] = curves
        _draw_mass_panel(ax, component, driver, curves, config_cache, models, configs, marker_map, color_map)

    _draw_cost_panel(ax_cost, component, natural_curves, config_cache, models, configs, marker_map, color_map)

    captured = {}
    for ax in axes:
        captured[ax] = (ax.get_xlim(), ax.get_ylim())
        for line in list(ax.get_lines()):
            line.remove()
        ax.set_xlim(*captured[ax][0])
        ax.set_ylim(*captured[ax][1])

    # When there's more than one mass-vs-driver panel, share one y (mass) range across all of
    # them so their scales are directly comparable, rather than each panel autoscaling to its own
    # (possibly very different) mass range.
    if n_left > 1:
        shared_ylim = (
            min(captured[ax][1][0] for ax in mass_axes),
            max(captured[ax][1][1] for ax in mass_axes),
        )
        for ax in mass_axes:
            captured[ax] = (captured[ax][0], shared_ylim)
            ax.set_ylim(*shared_ylim)

    # ---- pass 2: redraw every curve stretched across the frozen (captured) limits ----
    if show_lines:
        for ax, driver in zip(mass_axes, panel_drivers):
            xlim, _ylim = captured[ax]
            owners = owners_by_key[_driver_key(driver)]
            for model_name, model_cls in owners.items():
                raw_lo, raw_hi = _raw_range_for_display(
                    component, driver, model_cls, base_kwargs, xlim, natural_raw_ranges[_driver_key(driver)]
                )
                raw_range = (min(raw_lo, raw_hi), max(raw_lo, raw_hi))
                data = _sweep_single(component, driver, model_cls, base_kwargs, raw_range, n_points)
                ax.plot(data["driver_display"], data["mass"] * MASS_SCALE, color=color_map[model_name], lw=2)
            for model_name in constant_models:
                const_mass = _constant_value(model_name, config_cache, component.mass_attr)
                if const_mass is not None:
                    ax.plot(
                        xlim, [const_mass * MASS_SCALE, const_mass * MASS_SCALE],
                        color=color_map[model_name], lw=2, ls="--",
                    )

        cost_xlim, _cost_ylim = captured[ax_cost]
        mass_line = np.array(cost_xlim)  # already in tonnes: pass 1 plotted mass * MASS_SCALE
        for model_name in model_names:
            slope = _average_slope(model_name, config_cache, component)
            if slope is None:
                continue
            style = "--" if is_aggregate else "-"
            ax_cost.plot(mass_line, mass_line * slope, color=color_map[model_name], lw=2, ls=style)

    for ax in axes:
        ax.set_xlim(*captured[ax][0])
        ax.set_ylim(*captured[ax][1])

    # ---- cosmetics: labels, formula titles, legend, suptitle ----
    max_title_lines = 0
    for ax, driver in zip(mass_axes, panel_drivers):
        label, units = _driver_label_units(driver)
        ax.set_xlabel(f"{label} ({units})" if units else label)
        ax.set_ylabel("Mass (t)")
        ax.xaxis.set_major_locator(MaxNLocator(nbins=6))
        ax.xaxis.set_major_formatter(FuncFormatter(_fmt_tick))
        ax.yaxis.set_major_formatter(FuncFormatter(_fmt_tick))
        plt.setp(ax.get_xticklabels(), rotation=20, ha="right")
        ax.grid(alpha=0.3)
        if not is_aggregate:
            title_models = {**owners_by_key[_driver_key(driver)], **constant_models}
            lines = [
                (name, _resolve_mass_formula(component.label, cls))
                for name, cls in title_models.items()
            ]
            max_title_lines = max(max_title_lines, _set_stacked_title(ax, [(n, t) for n, t in lines if t]))

    ax_cost.set_xlabel("Mass (t)")
    ax_cost.set_ylabel("Cost ($k)")
    ax_cost.xaxis.set_major_locator(MaxNLocator(nbins=6))
    ax_cost.xaxis.set_major_formatter(FuncFormatter(_fmt_tick))
    ax_cost.yaxis.set_major_formatter(FuncFormatter(_fmt_tick))
    plt.setp(ax_cost.get_xticklabels(), rotation=20, ha="right")
    ax_cost.grid(alpha=0.3)
    if not is_aggregate:
        cost_lines = []
        for model_name in model_names:
            slope = _average_slope(model_name, config_cache, component)
            if slope is not None:
                cost_lines.append((model_name, f"cost = {_fmt_num(slope)}·mass"))
        max_title_lines = max(max_title_lines, _set_stacked_title(ax_cost, cost_lines))

    model_handles = [
        Line2D([0], [0], color=color_map[name], lw=2, label=name) for name in model_names
    ]
    config_handles = [
        Line2D(
            [0], [0], marker=marker_map[name], color="none", markerfacecolor="white",
            markeredgecolor="black", markersize=9, label=name,
        )
        for name in config_names
    ]
    fig.legend(
        handles=model_handles + config_handles,
        loc="lower center",
        ncol=len(model_handles) + len(config_handles),
        bbox_to_anchor=(0.5, 0.01),
        frameon=False,
        fontsize=9,
    )

    fig.tight_layout(rect=(0, 0.09, 1, 0.90))

    if is_aggregate:
        wrapped = textwrap.fill(f"= {AGGREGATE_COMPONENTS[component.label]}", width=18 * n_panels)
        n_lines = wrapped.count("\n") + 1
        fig.suptitle(component.label, fontsize=15, fontweight="bold", y=0.99)
        fig.text(0.5, 0.955, wrapped, ha="center", va="top", fontsize=9, style="italic")
        fig.subplots_adjust(top=0.90 - 0.045 * n_lines)
    else:
        fig.suptitle(component.label, fontsize=15, fontweight="bold", y=0.99)
        # Reserve extra headroom for panel titles taller than the common 2-line (one formula line
        # per model) case, e.g. components whose formula needs an "m_blade = ..." definition line.
        fig.subplots_adjust(top=0.86 - 0.029 * max(max_title_lines - 2, 0))

    return fig


def generate_all_figures(
    output_dir: str | Path,
    models: dict[str, type] | None = None,
    configs: dict[str, dict] | None = None,
    components: list[ComponentSpec] | None = None,
) -> dict[str, Path]:
    """Generates and saves one mass-vs-cost figure per component.

    Args:
        output_dir (str | Path): Directory the figures are saved into (created if missing).
        models (dict[str, type] | None, optional): Mapping of model name to a ``CSMBase``
            subclass to compare. Defaults to :py:data:`DEFAULT_MODELS`.
        configs (dict[str, dict] | None, optional): Mapping of configuration name to a raw
            turbine spec (see :py:func:`to_model_kwargs`). Defaults to
            :py:data:`DEFAULT_TURBINE_SPECS`.
        components (list[ComponentSpec] | None, optional): Components to plot. Defaults to
            :py:data:`PLOT_COMPONENTS` (all components with a non-trivial mass relationship).

    Returns:
        dict[str, Path]: Mapping of component label to the saved PNG path.
    """
    models = models or DEFAULT_MODELS
    configs = configs or DEFAULT_TURBINE_SPECS
    components = components or PLOT_COMPONENTS

    output_dir = Path(output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    base_kwargs = _base_config(configs)
    config_cache = _evaluate_all_configs(models, configs)

    figure_paths = {}
    for component in components:
        fig = plot_component(component, models, config_cache, base_kwargs, configs)
        path = output_dir / f"{_slugify(component.label)}.png"
        fig.savefig(path, dpi=150)
        plt.close(fig)
        figure_paths[component.label] = path
    return figure_paths


def build_report_dataframe(
    models: dict[str, type] | None = None,
    configs: dict[str, dict] | None = None,
    components: list[ComponentSpec] | None = None,
) -> pd.DataFrame:
    """Builds a component x (configuration, model) summary table of mass and cost.

    Cells are left blank (NaN) when a model failed to evaluate a configuration, so a future model
    with partial coverage (e.g. an in-progress custom fit) degrades gracefully instead of breaking
    the report.

    Returns:
        pd.DataFrame: Rows are component labels; columns are a
            ``(configuration, model)`` :py:class:`pandas.MultiIndex`; cells are "<mass>\\n<cost>"
            strings.
    """
    models = models or DEFAULT_MODELS
    configs = configs or DEFAULT_TURBINE_SPECS
    components = components or ALL_COMPONENTS

    config_cache = _evaluate_all_configs(models, configs)
    columns = pd.MultiIndex.from_product(
        [list(configs), list(models)], names=["configuration", "model"]
    )
    df = pd.DataFrame(index=[c.label for c in components], columns=columns, dtype=object)

    for config_name in configs:
        for model_name in models:
            entry = config_cache[model_name].get(config_name)
            if entry is None:
                continue
            for component in components:
                mass = entry.get(component.mass_attr)
                cost = entry.get(component.cost_attr)
                if mass is None or cost is None:
                    continue
                df.loc[component.label, (config_name, model_name)] = (
                    f"{_fmt_mass(mass)}\n{_fmt_cost(cost)}"
                )
    return df


def render_report_image(
    df: pd.DataFrame, output_path: str | Path, figsize: tuple[float, float] = (20.0, 11.0)
) -> Path:
    """Rasterizes the summary DataFrame from :py:func:`build_report_dataframe` into a PNG."""
    output_path = Path(output_path).resolve()
    fig, ax = plt.subplots(figsize=figsize)
    ax.axis("off")

    col_labels = [f"{config}\n{model}" for config, model in df.columns]
    cell_text = df.fillna("—").to_numpy().tolist()

    table = ax.table(
        cellText=cell_text,
        rowLabels=df.index,
        colLabels=col_labels,
        loc="center",
        cellLoc="center",
    )
    table.auto_set_font_size(False)
    table.set_fontsize(7)
    table.scale(1, 1.8)
    for (row, col), cell in table.get_celld().items():
        if row == 0 or col == -1:
            cell.set_text_props(fontweight="bold")
            cell.set_facecolor("#EFEFEF")

    fig.suptitle("Turbine Component Mass & Cost Summary", fontsize=16, fontweight="bold")
    fig.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return output_path


def _fit_dimensions(
    image_path: str | Path, max_width_in: float, max_height_in: float
) -> tuple[float, float]:
    """Scales an image's pixel dimensions to fit within a (max_width, max_height) box in inches,
    preserving aspect ratio.
    """
    with Image.open(image_path) as img:
        px_w, px_h = img.size
    aspect = px_w / px_h
    width_in, height_in = max_width_in, max_width_in / aspect
    if height_in > max_height_in:
        height_in = max_height_in
        width_in = height_in * aspect
    return width_in, height_in


def build_presentation(
    output_path: str | Path,
    figure_paths: dict[str, Path],
    report_image_path: Path,
    title: str = "CSM Model Comparison",
) -> Path:
    """Assembles a widescreen slide deck: a title slide, one slide per component figure, and a
    final summary report slide.

    Every figure is scaled to fit within the same content area regardless of how many panels it
    has (components with more than one mass-vs-driver panel produce a wider image), so no picture
    overflows the slide.

    Returns:
        Path: The saved .pptx path.
    """
    output_path = Path(output_path).resolve()
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    blank_layout = prs.slide_layouts[6]

    content_top = 1.3
    max_width, max_height = 12.33, 7.5 - content_top - 0.2

    def _add_image_slide(slide_title: str, image_path: Path):
        slide = prs.slides.add_slide(blank_layout)
        title_box = slide.shapes.add_textbox(Inches(0.5), Inches(0.25), Inches(12.33), Inches(0.9))
        paragraph = title_box.text_frame.paragraphs[0]
        paragraph.text = slide_title
        paragraph.font.size = Pt(30)
        paragraph.font.bold = True

        width_in, height_in = _fit_dimensions(image_path, max_width, max_height)
        left = (prs.slide_width - Inches(width_in)) // 2
        top = Inches(content_top) + (Inches(max_height) - Inches(height_in)) // 2
        slide.shapes.add_picture(str(image_path), left, top, width=Inches(width_in))
        return slide

    title_slide = prs.slides.add_slide(blank_layout)
    title_box = title_slide.shapes.add_textbox(Inches(1), Inches(3.1), Inches(11.33), Inches(1.5))
    paragraph = title_box.text_frame.paragraphs[0]
    paragraph.text = title
    paragraph.font.size = Pt(40)
    paragraph.font.bold = True

    for label, path in figure_paths.items():
        _add_image_slide(label, path)

    _add_image_slide("Summary Report", report_image_path)

    prs.save(str(output_path))
    return output_path


def generate_comparison(
    output_dir: str | Path = "output/csm_comparison",
    models: dict[str, type] | None = None,
    configs: dict[str, dict] | None = None,
) -> dict[str, Path]:
    """Runs the full pipeline: per-component figures, a summary report, and a slide deck.

    Args:
        output_dir (str | Path, optional): Directory the figures, report image, and deck are
            saved into. Defaults to "output/csm_comparison".
        models (dict[str, type] | None, optional): Mapping of model name to a ``CSMBase``
            subclass to compare. Defaults to :py:data:`DEFAULT_MODELS`.
        configs (dict[str, dict] | None, optional): Mapping of configuration name to a raw
            turbine spec. Defaults to :py:data:`DEFAULT_TURBINE_SPECS`.

    Returns:
        dict[str, Path]: Paths to the figures directory, summary report image, and presentation.
    """
    output_dir = Path(output_dir).resolve()
    figures_dir = output_dir / "figures"
    figure_paths = generate_all_figures(figures_dir, models=models, configs=configs)

    report_df = build_report_dataframe(models=models, configs=configs)
    report_image_path = render_report_image(report_df, output_dir / "summary_report.png")

    pptx_path = build_presentation(
        output_dir / "csm_comparison.pptx", figure_paths, report_image_path
    )
    return {
        "figures_dir": figures_dir,
        "report_image": report_image_path,
        "presentation": pptx_path,
    }


if __name__ == "__main__":
    for key, path in generate_comparison().items():
        print(f"{key}: {path}")
