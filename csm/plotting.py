"""Cross-model comparison plots and slide deck generation for turbine component mass and cost.

For every turbine component (blade, hub, gearbox, tower, ...), this module sweeps the parameter
that actually drives that component's mass in each requested cost and scaling model, plots mass
vs. that driving parameter next to cost vs. its own relevant parameter (rotor diameter for the
blade/rotor family, hub height for the tower, turbine rating for everything else — see
:py:data:`COST_PANEL_DRIVER`), and marks a set of named turbine configurations on every curve.
Different models frequently use genuinely different formulas for the same component (e.g. the
2015 brake mass is a function of rotor torque while the 2020 brake mass is a function of turbine
rating), so the number of "mass vs. driver" panels adapts automatically: one panel per distinct
driver among the models being compared. The cost panel's title keeps showing "cost = k·mass"
regardless, since that's the literal formula CSMBase uses and remains useful on its own.

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

An empirical measurements CSV can optionally be overlaid as faint gray points behind the model
curves (see the `empirical_csv` argument on
:py:func:`generate_comparison`/:py:func:`generate_all_figures` and :py:func:`load_empirical_data`
for the expected columns); passing None (the default) leaves plots unchanged. A component only
gets an overlay on the panels the CSV actually has data for.

A 2026 industry cost benchmark CSV (Wood Mackenzie RACM-style, one row per turbine-rating/rotor-
diameter/hub-height bin combination and cost category, given as a $/MW rate) can similarly be
overlaid on cost panels, in a distinct color — see the `benchmark_csv` argument on the same
functions and :py:func:`load_benchmark_data`. Benchmark categories that bundle several CSM
components together (see :py:data:`WM_CATEGORY_MAPPING`) can't be shown as a direct overlay on any
single component's own figure; those instead get their own combined comparison figure via
:py:func:`generate_wm_comparison_figures`, plotting the *sum* of their mapped CSM components'
costs (with any needed multiplier, e.g. blades x num_blades) against the benchmark.
"""

import re
import sys
import math
import textwrap
from typing import NamedTuple
from pathlib import Path
from collections.abc import Callable

import numpy as np
import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt
from PIL import Image
from pptx import Presentation
from attrs import fields as attrs_fields
from pptx.util import Pt, Inches
from matplotlib.lines import Line2D
from matplotlib.ticker import MaxNLocator, FuncFormatter

from csm.models.nlr2015 import Land2015NLR
from csm.models.nlr2020 import Land2020NLR
from csm.models.nlr2026 import Land2026NLR


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

# Same information as AGGREGATE_COMPONENTS above, but as component labels rather than prose, so
# code can check whether an aggregate's *real* leaf subcomponents all agree on a driver (see
# _cost_line_valid) rather than checking the aggregate's own default_driver, which is just an
# assigned label for its cost panel, not a decomposition of what it actually sums.
AGGREGATE_LEAF_COMPONENTS: dict[str, list[str]] = {
    "Hub System": ["Hub", "Pitch System", "Spinner"],
    "Rotor (Total)": ["Blade", "Hub", "Pitch System", "Spinner"],
    "Nacelle (Total)": [
        "Low Speed Shaft",
        "Main Bearing",
        "Gearbox",
        "Brake",
        "High Speed Shaft",
        "Generator",
        "Bedplate",
        "Yaw System",
        "Hydraulic Cooling",
        "Nacelle Cover",
        "Platform & Mainframe",
        "Transformer",
        "Converter",
        "Controls",
        "Electrical Connection",
    ],
    "Turbine (Total)": [
        "Blade",
        "Hub",
        "Pitch System",
        "Spinner",
        "Low Speed Shaft",
        "Main Bearing",
        "Gearbox",
        "Brake",
        "High Speed Shaft",
        "Generator",
        "Bedplate",
        "Yaw System",
        "Hydraulic Cooling",
        "Nacelle Cover",
        "Platform & Mainframe",
        "Transformer",
        "Converter",
        "Controls",
        "Electrical Connection",
        "Tower",
    ],
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

# Which single turbine-level parameter each component's cost panel is plotted against, instead of
# mass (see the module docstring). A coarser, single-driver grouping than the mass panels' own
# (possibly multi-panel, composite) drivers, since there's one cost panel regardless of how many
# mass panels a component has. Matches WM_CATEGORY_MAPPING's driver choices where they overlap.
COST_PANEL_DRIVER: dict[str, str] = {
    "Blade": "rotor_diameter",
    "Hub": "rotor_diameter",
    "Pitch System": "rotor_diameter",
    "Spinner": "rotor_diameter",
    "Hub System": "rotor_diameter",
    "Rotor (Total)": "rotor_diameter",
    "Low Speed Shaft": "rotor_diameter",
    "Main Bearing": "rotor_diameter",
    "Bedplate": "rotor_diameter",
    "Yaw System": "rotor_diameter",
    "Platform & Mainframe": "rotor_diameter",
    "Tower": "tower_length",
    "Gearbox": "rated_power_kw",
    "Brake": "rated_power_kw",
    "High Speed Shaft": "rated_power_kw",
    "Generator": "rated_power_kw",
    "Hydraulic Cooling": "rated_power_kw",
    "Nacelle Cover": "rated_power_kw",
    "Transformer": "rated_power_kw",
    "Converter": "rated_power_kw",
    "Controls": "rated_power_kw",
    "Electrical Connection": "rated_power_kw",
    "Nacelle (Total)": "rated_power_kw",
    "Turbine (Total)": "rated_power_kw",
}


class WMMapping(NamedTuple):
    """How one 2026 industry cost benchmark category (a ``cost_element_item`` in the RACM data,
    e.g. "Hub and Pitch") relates to this module's CSM components.
    """

    csm_components: tuple[str, ...]
    """ComponentSpec labels that sum to this benchmark category."""
    multipliers: dict[str, str]
    """Component label -> a `base_kwargs`/configuration key (e.g. "num_bearings") to scale that
    component's cost by before summing, for benchmark categories priced per-turbine rather than
    per-part."""
    driver: str
    """Which of the three turbine-level parameters this category is benchmarked against."""


# From the Wood Mackenzie RACM category definitions, mapped onto CSM components. Used by
# generate_wm_comparison_figures for the three categories with no CSM component or aggregate that
# sums to exactly the same thing (Balance of Nacelle, Bearings and Shaft, Structure — see
# COMBINED_WM_CATEGORIES below): those get their own combined comparison figure, computing the
# *sum* of their mapped CSM components' costs (with any needed multiplier, e.g. blades x
# num_blades) since no single CSM field already represents that sum.
WM_CATEGORY_MAPPING: dict[str, WMMapping] = {
    "Balance of Nacelle": WMMapping(
        (
            "Nacelle Cover",
            "Electrical Connection",
            "Hydraulic Cooling",
            "Brake",
            "Transformer",
            "Controls",
        ),
        {},
        "rated_power_kw",
    ),
    "Bearings and Shaft": WMMapping(
        ("Main Bearing", "Low Speed Shaft", "High Speed Shaft"),
        {"Main Bearing": "num_bearings"},
        "rated_power_kw",
    ),
    "Blades": WMMapping(("Blade",), {"Blade": "num_blades"}, "rotor_diameter"),
    "Converter": WMMapping(("Converter",), {}, "rated_power_kw"),
    "Gearbox": WMMapping(("Gearbox",), {}, "rated_power_kw"),
    "Generator": WMMapping(("Generator",), {}, "rated_power_kw"),
    "Hub and Pitch": WMMapping(("Hub", "Pitch System", "Spinner"), {}, "rotor_diameter"),
    "Structure": WMMapping(
        ("Yaw System", "Bedplate", "Platform & Mainframe"), {}, "rated_power_kw"
    ),
    "Tower": WMMapping(("Tower",), {}, "tower_length"),
}

# Component (or CSM aggregate) label -> (WoodMac categories to compare it against, multiplier key
# or None). These overlay directly onto that component's *own* existing cost panel rather than
# needing a separate combined figure, because CSM already has a single field for the comparison:
#   - a lone WM category with a multiplier (Blades / num_blades) divides the benchmark by that
#     multiplier to become a per-part figure comparable to CSM's own per-part cost_attr;
#   - several WM categories with no multiplier are summed (see `_benchmark_points`) because CSM's
#     aggregate cost fields (hub_system_cost, nacelle_cost, rotor_cost, turbine_cost) already sum
#     the exact same set of components those categories cover, so no `_sweep_combined_cost` is
#     needed — Hub and Pitch sums to exactly CSM's Hub System, and Nacelle/Rotor/Turbine (Total)
#     sum every WoodMac "Turbine Purchase" sub-category that falls in each respective group.
BENCHMARK_OVERLAY: dict[str, tuple[list[str], str | None]] = {
    "Blade": (["Blades"], "num_blades"),
    "Gearbox": (["Gearbox"], None),
    "Generator": (["Generator"], None),
    "Converter": (["Converter"], None),
    "Tower": (["Tower"], None),
    "Hub System": (["Hub and Pitch"], None),
    "Rotor (Total)": (["Blades", "Hub and Pitch"], None),
    "Nacelle (Total)": (
        [
            "Balance of Nacelle",
            "Bearings and Shaft",
            "Converter",
            "Gearbox",
            "Generator",
            "Structure",
        ],
        None,
    ),
    "Turbine (Total)": (
        [
            "Balance of Nacelle",
            "Bearings and Shaft",
            "Blades",
            "Converter",
            "Gearbox",
            "Generator",
            "Hub and Pitch",
            "Structure",
            "Tower",
        ],
        None,
    ),
}

# The only WoodMac categories with no CSM component or aggregate summing to exactly the same
# thing (see BENCHMARK_OVERLAY above) — these still get their own combined comparison figure.
COMBINED_WM_CATEGORIES: list[str] = ["Balance of Nacelle", "Bearings and Shaft", "Structure"]

# Optional 2026 industry cost benchmark overlay (e.g.
# csm/WM_wind_capex_benchmark_data_geared.csv): one row per (turbine rating bin, rotor diameter
# bin, tower height bin, cost category) combination, given as a $/MW rate. Passing a path via the
# `benchmark_csv` argument on
# :py:func:`generate_comparison`/:py:func:`generate_all_figures`/
# :py:func:`generate_wm_comparison_figures` overlays it, in a distinct color from the empirical
# measurements overlay, on the cost panel of any component (or combined WM category) it covers;
# omitting it (the default) leaves plots unchanged.
BENCHMARK_ITEM_COLUMN = "cost_element_item"
BENCHMARK_VALUE_COLUMN = "value_$/MW"
BENCHMARK_CAPACITY_COLUMN = "turbine_nameplate_capacity"
BENCHMARK_RD_COLUMN = "rotor_diameter"
BENCHMARK_TOWER_COLUMN = "tower_height"
BENCHMARK_PERIOD_COLUMN = "time_period"
BENCHMARK_COLOR = "#3E8E7E"

# Shared styling for the empirical-measurement and industry-benchmark overlay scatter points:
# a thin black edge and a zorder well above every model line (~2), config marker (5), and each
# other, so both overlays always read as sitting on top of the rest of the plot regardless of
# panel or draw order — empirical data is real-world ground truth, and benchmark data is the
# external reference the fitted lines are calibrated against, so neither should ever be hidden
# behind a curve or marker.
OVERLAY_EDGE_COLOR = "black"
OVERLAY_EDGE_LINEWIDTH = 0.4
EMPIRICAL_ZORDER = 20
BENCHMARK_ZORDER = 21

# Which raw benchmark bin column corresponds to each simple driver. The turbine rating bin's own
# midpoint is already in MW, matching `rated_power_kw`'s MW display units.
BENCHMARK_DRIVER_COLUMNS: dict[str, str] = {
    "rotor_diameter": BENCHMARK_RD_COLUMN,
    "rated_power_kw": BENCHMARK_CAPACITY_COLUMN,
    "tower_length": BENCHMARK_TOWER_COLUMN,
}

_BIN_CLOSED_RE = re.compile(r"([\d.]+)\s*-\s*([\d.]+)")
_BIN_OPEN_HIGH_RE = re.compile(r"([\d.]+)\s*\+")
_BIN_OPEN_LOW_RE = re.compile(r"<\s*([\d.]+)")


def _bin_midpoints(labels) -> dict[str, float]:
    """Maps each distinct RACM range label (e.g. "B.) 101-111 Meters") to its numeric midpoint.

    Open-ended bins ("A.) <101 Meters", "I.) 9.0+ MW") are extrapolated using the median width of
    the closed bins in the same set, since no true bound is given for them.
    """
    widths = []
    closed = {}
    for label in labels:
        m = _BIN_CLOSED_RE.search(label)
        if m:
            lo, hi = float(m.group(1)), float(m.group(2))
            closed[label] = (lo + hi) / 2
            widths.append(hi - lo)
    typical_width = float(np.median(widths)) if widths else 10.0
    result = dict(closed)
    for label in labels:
        if label in result:
            continue
        m = _BIN_OPEN_HIGH_RE.search(label)
        if m:
            result[label] = float(m.group(1)) + typical_width / 2
            continue
        m = _BIN_OPEN_LOW_RE.search(label)
        if m:
            result[label] = float(m.group(1)) - typical_width / 2
            continue
        nums = re.findall(r"[\d.]+", label)
        result[label] = float(nums[0]) if nums else float("nan")
    return result


def load_benchmark_data(
    csv_path: str | Path | None, time_period: str | None = "2026Y"
) -> pd.DataFrame | None:
    """Loads an industry cost benchmark CSV for the overlay described above.

    Args:
        csv_path (str | Path | None): Path to the CSV, or None to disable the overlay.
        time_period (str | None, optional): Keep only rows matching this "time_period" value
            (quarterly-refreshed forecasts for different periods live in the same file); None
            keeps every period present. Defaults to "2026Y".

    Returns:
        pd.DataFrame | None: The loaded data, or None if `csv_path` is None.
    """
    if csv_path is None:
        return None
    df = pd.read_csv(csv_path)
    df.columns = [c.strip() for c in df.columns]
    if time_period is not None and BENCHMARK_PERIOD_COLUMN in df.columns:
        df = df[df[BENCHMARK_PERIOD_COLUMN] == time_period]
    return df


def _benchmark_points(
    benchmark_df: pd.DataFrame | None, wm_categories: list[str], driver: Driver
) -> tuple[np.ndarray, np.ndarray] | None:
    """(x_display, cost_$k) arrays of every raw benchmark row for `wm_categories`.

    x is the midpoint of the bin matching `driver`; y is `value_$/MW` converted to an absolute
    cost using each row's own turbine-rating-bin midpoint. With more than one category (e.g.
    summing every "Turbine Purchase" sub-category to compare against CSM's Turbine (Total), since
    WoodMac has no single row for that), costs are summed within each (turbine rating, rotor
    diameter, hub height) bin combination — a combination is only included if every category in
    `wm_categories` has a row for it, so a partial sum is never silently shown as if it were the
    whole group.

    Returns None if none of `wm_categories` are in the data, `driver` isn't one of the three raw
    binned columns (a composite or rotor-torque driver, say — the benchmark data has no way to
    express those), or (multi-category only) no bin combination has every category present.
    """
    if benchmark_df is None or not isinstance(driver, str):
        return None
    driver_col = BENCHMARK_DRIVER_COLUMNS.get(driver)
    if driver_col is None:
        return None
    rows = benchmark_df[benchmark_df[BENCHMARK_ITEM_COLUMN].isin(wm_categories)]
    if rows.empty:
        return None

    driver_mid = _bin_midpoints(rows[driver_col].unique())
    capacity_mid = _bin_midpoints(rows[BENCHMARK_CAPACITY_COLUMN].unique())
    rows = rows.copy()
    rows["_cost_usd"] = rows[BENCHMARK_VALUE_COLUMN] * rows[BENCHMARK_CAPACITY_COLUMN].map(
        capacity_mid
    )

    if len(wm_categories) == 1:
        cost_by_bin = rows.set_index(
            [BENCHMARK_CAPACITY_COLUMN, BENCHMARK_RD_COLUMN, BENCHMARK_TOWER_COLUMN]
        )["_cost_usd"]
    else:
        group_cols = [BENCHMARK_CAPACITY_COLUMN, BENCHMARK_RD_COLUMN, BENCHMARK_TOWER_COLUMN]
        present = rows.groupby(group_cols, observed=True)[BENCHMARK_ITEM_COLUMN].nunique()
        complete_bins = present[present == len(wm_categories)].index
        if len(complete_bins) == 0:
            return None
        cost_by_bin = rows.groupby(group_cols, observed=True)["_cost_usd"].sum().loc[complete_bins]

    cost_by_bin = cost_by_bin.reset_index()
    x = cost_by_bin[driver_col].map(driver_mid).to_numpy(dtype=float)
    y = cost_by_bin["_cost_usd"].to_numpy(dtype=float)
    return x, y * COST_SCALE


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
    """Renders `component_label`'s mass formula text for `model_cls`.

    Checks for an exact match in :py:data:`FORMULA_OVERRIDES` first. Then, same reasoning as
    :py:func:`_resolve_driver`: if `model_cls` is a generated model with a
    :py:func:`_generated_shape_overrides` marker for `component_label`, that marker decides —
    authoritative regardless of Python inheritance. Otherwise falls back to matching on
    `model_cls`'s base classes, so a hand-written model that subclasses e.g. `Land2020NLR`
    without overriding this component's `calculate_*` method inherits its formula *shape* too, so
    the displayed formula text should match, not silently fall back to the base (2015-style)
    template just because it's a different class object.
    """
    overrides = FORMULA_OVERRIDES.get(component_label, {})
    if model_cls in overrides:
        return overrides[model_cls](model_cls)
    marker = _generated_shape_overrides(model_cls).get(component_label)
    if marker is not None:
        uses_2020_shape = marker == "2020"
    else:
        uses_2020_shape = any(issubclass(model_cls, base_cls) for base_cls in overrides)
    if uses_2020_shape and Land2020NLR in overrides:
        return overrides[Land2020NLR](model_cls)
    template = FORMULA_DEFAULT.get(component_label)
    return template(model_cls) if template is not None else ""


def _blade_mass_definition(model_cls: type) -> str:
    """ "m_blade = ..." line, reusing the Blade component's own formula for `model_cls`."""
    return _resolve_mass_formula("Blade", model_cls).replace("m = ", "m_blade = ", 1)


def _bedplate_mass_definition(model_cls: type) -> str:
    """ "m_bedplate = ..." line, reusing the Bedplate component's own formula for `model_cls`."""
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
    "Tower": lambda cls: (
        f"m = {_fmt_num(_coeff(cls, 'tower_mass_coeff'))}·H^{_fmt_num(_coeff(cls, 'tower_mass_exp'))}"
    ),
    "Converter": lambda cls: "m = 0 (not modeled)",
    "Controls": lambda cls: "m = 0 (not modeled)",
    "Electrical Connection": lambda cls: "m = 0 (not modeled)",
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
    "2026": Land2026NLR,
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

# Optional empirical-measurements overlay (e.g. csm/us_lbw_csm_2026_data.csv): a CSV with one row
# per measured turbine component, columns "Component", "MW", "RD (m)", "hh (m)", "mass (kg)",
# and optionally "cost ($)" and "outlier?" ("Yes" rows are dropped). Passing a path via the
# `empirical_csv` argument on :py:func:`generate_comparison`/:py:func:`generate_all_figures`
# overlays it as faint points behind the model curves; omitting it (the default) leaves plots
# unchanged. A component only gets an overlay on the panels its rows actually have data for —
# it's skipped entirely wherever the CSV doesn't cover it, same principle as everywhere else in
# this module.
EMPIRICAL_COMPONENT_COLUMN = "Component"
EMPIRICAL_MASS_COLUMN = "mass (kg)"
EMPIRICAL_COST_COLUMN = "cost ($)"
EMPIRICAL_OUTLIER_COLUMN = "outlier?"

EMPIRICAL_COMPONENT_LABELS: dict[str, str] = {
    "blade": "Blade",
    "hub": "Hub",
    "spinner": "Spinner",
    "main bearing": "Main Bearing",
    "low speed shaft": "Low Speed Shaft",
    "bedplate": "Bedplate",
    "gearbox": "Gearbox",
    "generator": "Generator",
    "transformer": "Transformer",
    "tower": "Tower",
    "nacelle": "Nacelle (Total)",
    "rotor": "Rotor (Total)",
    "turbine": "Turbine (Total)",
}

# Raw CSV columns, mapped to the same raw kwarg names sweeps and configuration markers use, so
# a row's driver value can be computed via the same `_driver_display_value` they already go
# through. MW is scaled kW->none here since `_derive_empirical_entry` does that conversion.
EMPIRICAL_ROW_COLUMNS: dict[str, str] = {
    "rotor_diameter": "RD (m)",
    "rated_power_kw": "MW",
    "tower_length": "hh (m)",
}


def load_empirical_data(csv_path: str | Path | None) -> pd.DataFrame | None:
    """Loads an empirical measurements CSV for the overlay described above.

    Args:
        csv_path (str | Path | None): Path to the CSV, or None to disable the overlay (the
            functions that accept an `empirical_csv` argument call this for you).

    Returns:
        pd.DataFrame | None: The loaded data with "outlier?" rows removed, or None if `csv_path`
            is None.
    """
    if csv_path is None:
        return None
    df = pd.read_csv(csv_path)
    df.columns = [c.strip().lstrip("﻿") for c in df.columns]
    if EMPIRICAL_OUTLIER_COLUMN in df.columns:
        is_outlier = df[EMPIRICAL_OUTLIER_COLUMN].astype(str).str.strip().str.lower() == "yes"
        df = df[~is_outlier]
    return df


def _empirical_rows(
    empirical_df: pd.DataFrame | None, component: ComponentSpec
) -> pd.DataFrame | None:
    """Rows of `empirical_df` for `component`, or None if it isn't covered at all."""
    if empirical_df is None:
        return None
    csv_label = next(
        (k for k, v in EMPIRICAL_COMPONENT_LABELS.items() if v == component.label), None
    )
    if csv_label is None:
        return None
    names = empirical_df[EMPIRICAL_COMPONENT_COLUMN].astype(str).str.strip().str.lower()
    rows = empirical_df[names == csv_label]
    return rows if len(rows) else None


def _derive_empirical_entry(row: pd.Series, base_kwargs: dict) -> dict:
    """Builds a driver-lookup dict for one empirical CSV row from its raw RD/MW/hh columns,
    additionally deriving rotor torque with the exact same formula
    (:py:meth:`CSMBase.calculate_rotor_torque`) the swept model curves use — the CSV doesn't
    record the efficiency/tip-speed a torque calculation needs, so those are taken from
    `base_kwargs`, the same reference values used elsewhere for whatever a sweep isn't varying.
    This lets every driver this module supports, including rotor torque and any composite driver
    built from these four quantities, be evaluated for empirical data through the same
    :py:func:`_driver_display_value` used for model curves and configuration markers.
    """
    entry: dict = {}
    for attr, column in EMPIRICAL_ROW_COLUMNS.items():
        value = pd.to_numeric(row.get(column), errors="coerce")
        if pd.notna(value):
            entry[attr] = float(value) * 1000 if attr == "rated_power_kw" else float(value)
    if "rotor_diameter" in entry and "rated_power_kw" in entry:
        rotor_speed = base_kwargs["max_tip_speed"] / (0.5 * entry["rotor_diameter"])
        rated_hub_power = entry["rated_power_kw"] / base_kwargs["efficiency_max"]
        entry["rotor_torque"] = rated_hub_power / rotor_speed
    return entry


def _empirical_mass_points(
    empirical_df: pd.DataFrame | None,
    component: ComponentSpec,
    driver: Driver,
    base_kwargs: dict,
) -> tuple[np.ndarray, np.ndarray] | None:
    """(x_display, mass_tonnes) arrays of `component` rows with both a `driver` value (computed
    or derived — see :py:func:`_derive_empirical_entry`) and a measured mass, or None if
    unavailable.
    """
    rows = _empirical_rows(empirical_df, component)
    if rows is None:
        return None
    xs, ys = [], []
    for _, row in rows.iterrows():
        mass = row.get(EMPIRICAL_MASS_COLUMN)
        if pd.isna(mass):
            continue
        x = _driver_display_value(driver, _derive_empirical_entry(row, base_kwargs))
        if x is None:
            continue
        xs.append(x)
        ys.append(float(mass) * MASS_SCALE)
    if not xs:
        return None
    return np.array(xs), np.array(ys)


def _empirical_cost_points(
    empirical_df: pd.DataFrame | None,
    component: ComponentSpec,
    driver: Driver,
    base_kwargs: dict,
) -> tuple[np.ndarray, np.ndarray] | None:
    """(x_display, cost_$k) arrays of `component` rows with both a `driver` value (computed or
    derived — see :py:func:`_derive_empirical_entry`) and a measured cost, or None if unavailable.
    """
    rows = _empirical_rows(empirical_df, component)
    if rows is None or EMPIRICAL_COST_COLUMN not in rows.columns:
        return None
    xs, ys = [], []
    for _, row in rows.iterrows():
        cost = row.get(EMPIRICAL_COST_COLUMN)
        if pd.isna(cost):
            continue
        x = _driver_display_value(driver, _derive_empirical_entry(row, base_kwargs))
        if x is None:
            continue
        xs.append(x)
        ys.append(float(cost) * COST_SCALE)
    if not xs:
        return None
    return np.array(xs), np.array(ys)


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


def _generated_shape_overrides(model_cls: type) -> dict[str, str]:
    """The `SHAPE_OVERRIDES` marker `csm/build_custom_model.py` writes into a generated model's
    module (component label -> which named shape, `"2020"` or `"2015"`, that component's
    `calculate_*` method actually implements there), or `{}` for a hand-written model
    (`nlr2015.py`/`nlr2020.py`), which carries no such marker and doesn't need one.

    This is the only reliable way to tell which formula a *generated* model's method implements
    for a specific component. Neither field presence nor Python inheritance work in general:
    an attrs subclass keeps every parent field even when a method override stops using some of
    them (so checking "does it have `tower_mass_intercept`" can't tell a `Land2020NLR` subclass
    whose Tower was overridden to `Land2015NLR`'s shape apart from one that wasn't), and
    `issubclass` is equally unreliable in the other direction (a generated class overriding one
    component to match a *different* model's shape doesn't retroactively become a Python
    subclass of that model). The marker sidesteps both: it's written by the same code that
    decided the shape, so it's always authoritative for models that have it.
    """
    module = sys.modules.get(model_cls.__module__)
    return getattr(module, "SHAPE_OVERRIDES", {}) if module else {}


def _resolve_driver(component: ComponentSpec, model_cls: type) -> Driver | None:
    """Returns the driver `model_cls` actually uses for `component`.

    Checks for an exact match in :py:data:`COMPONENT_DRIVER_OVERRIDES` first. Then, if
    `model_cls` is a generated model with a :py:func:`_generated_shape_overrides` marker for
    `component.label`, that marker decides — authoritative regardless of Python inheritance (see
    its docstring). Otherwise falls back to matching on `model_cls`'s base classes, so a
    hand-written model that subclasses e.g. `Land2020NLR` without overriding this component's
    `calculate_*` method (a coefficients-only refit, say) is correctly treated as inheriting its
    driver too, rather than silently falling back to `component.default_driver` just because it's
    a different class object. Falls back to `component.default_driver` only when nothing matches,
    which is correct for any model that inherits the base formula (and therefore the base driver)
    for this component.
    """
    overrides = COMPONENT_DRIVER_OVERRIDES.get(component.label, {})
    if model_cls in overrides:
        return overrides[model_cls]
    marker = _generated_shape_overrides(model_cls).get(component.label)
    if marker is not None:
        uses_2020_shape = marker == "2020"
    else:
        uses_2020_shape = any(issubclass(model_cls, base_cls) for base_cls in overrides)
    if uses_2020_shape and Land2020NLR in overrides:
        return overrides[Land2020NLR]
    return component.default_driver


def _cost_driver_matches(component: ComponentSpec, model_cls: type, cost_driver: str) -> bool:
    """True if `model_cls`'s real mass-panel driver for `component` is exactly `cost_driver`.

    The cost panel always plots against one coarse, single-parameter driver per component (see
    :py:data:`COST_PANEL_DRIVER`), but a given model's actual cost formula might genuinely depend
    on something else entirely — a different single parameter (e.g. the 2015 brake depends on
    rotor torque, not turbine rating), or a composite of two (e.g. the 2015 low speed shaft
    depends on blade mass *and* rating). In either case, sweeping just `cost_driver` while holding
    the real driver fixed at an arbitrary reference value produces a line that's an artifact of
    that reference, not a faithful "cost as a function of `cost_driver`" — so the caller should
    skip drawing it (markers, computed from each configuration's real full inputs, stay valid
    either way).
    """
    return _resolve_driver(component, model_cls) == cost_driver


def _cost_line_valid(component: ComponentSpec, model_cls: type, cost_driver: str) -> bool:
    """Like :py:func:`_cost_driver_matches`, but for a "total" component (Hub System, Rotor/
    Nacelle/Turbine (Total)) checks whether *every one* of its real leaf subcomponents (see
    :py:data:`AGGREGATE_LEAF_COMPONENTS`) agrees on `cost_driver` for `model_cls` — not just
    whether the aggregate's own assigned default driver happens to equal `cost_driver`, which is
    trivially true by construction and wouldn't catch a mismatch buried in what it actually sums
    (e.g. Nacelle (Total) mixes rotor-diameter-, rotor-torque-, and rating-driven subcomponents
    for every current model, so its cost is never genuinely a function of turbine rating alone).
    """
    leaf_labels = AGGREGATE_LEAF_COMPONENTS.get(component.label)
    if leaf_labels is None:
        return _cost_driver_matches(component, model_cls, cost_driver)
    leaves = [c for c in ALL_COMPONENTS if c.label in leaf_labels]
    return all(_cost_driver_matches(leaf, model_cls, cost_driver) for leaf in leaves)


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


def _safe_upstream_kwargs(model_cls: type, base_kwargs: dict, *target_attrs: str) -> dict:
    """Reference-point values for every computed mass/cost attribute `model_cls` computes that
    `target_attrs` doesn't actually depend on (per the model's own `parameter_graph`).

    `run()` computes every subsystem's mass, *then* every subsystem's cost, each in one fixed
    sequence, aborting the whole phase on the first subsystem whose formula goes invalid (e.g. a
    negative mass at an extreme swept value, or — for a model whose coefficients came from a fit
    over too little data — even at an ordinary value). For a component computed *late* in either
    sequence, an earlier and completely unrelated failure means it never gets a chance to run at
    all — even though its own formula would have been perfectly fine, and even though the entire
    *cost* phase never starts if anything in the *mass* phase fails first. Pre-supplying every
    *unrelated* attribute's value from a reference run at `base_kwargs` (an average of real
    configurations, essentially never an extreme edge case, though see below) makes those upstream
    calculations short-circuit instead of re-running and failing, letting the sweep reach
    `target_attrs` regardless of where they fall in either sequence. Attributes `target_attrs`
    themselves transitively depend on are excluded, so they're still freshly (and correctly)
    recomputed at each swept point.

    Even the reference run itself can fail partway through (a poorly-generalizing fit can be
    invalid at literally every realistic value, not just extreme ones) — in that case whatever it
    did manage to compute is still used, and every *unrelated* attribute it never reached is
    plugged with a small positive placeholder rather than left missing. `target_attrs` never
    depend on those (they were excluded from `keep` for exactly this purpose), so the placeholder
    is never actually read by anything the caller computes from — it exists purely so the fixed
    calculate-in-sequence methods don't raise on their way past it to whatever comes next.
    """
    reference = model_cls(**base_kwargs)
    try:
        reference.run()
    except ValueError:
        pass
    keep = set(target_attrs)
    for attr in target_attrs:
        if attr in reference.parameter_graph:
            keep |= nx.descendants(reference.parameter_graph, attr)
    return {
        name: (value if value is not None else 1e-6)
        for name, value in reference.get_results().items()
        if name not in keep
    }


def _sweep_single(
    component: ComponentSpec,
    driver: Driver,
    model_cls: type,
    base_kwargs: dict,
    raw_range: tuple[float, float],
    n_points: int = 60,
) -> dict[str, np.ndarray]:
    """Sweeps `model_cls` across `raw_range` of `driver`'s underlying raw attribute.

    All non-driver model inputs are held fixed at `base_kwargs`, except for a set of "safe"
    upstream values (see :py:func:`_safe_upstream_kwargs`) that stop an unrelated subsystem's
    formula from going invalid partway through `model.run()`'s fixed calculation sequence and
    aborting it before `component` itself gets computed. Whatever `component` still couldn't
    compute at a given point (its own formula genuinely invalid there) is left as NaN, which
    matplotlib simply skips, leaving a gap rather than truncating the curve early.

    Returns:
        dict[str, np.ndarray]: "driver_display", "mass", "cost", "mass_sorted", and "cost_sorted"
            arrays. The sorted arrays are mass-ascending so the mass-vs-cost curve draws as a
            single line even if mass isn't perfectly monotonic in the driver.
    """
    override_attr = _override_attr(driver)
    raw_grid = np.linspace(*raw_range, n_points)
    masses = np.full(n_points, np.nan)
    costs = np.full(n_points, np.nan)
    display = np.full(n_points, np.nan)
    safe_kwargs = _safe_upstream_kwargs(
        model_cls, base_kwargs, component.mass_attr, component.cost_attr
    )
    for i, raw_value in enumerate(raw_grid):
        kwargs = {**base_kwargs, **safe_kwargs}
        kwargs[override_attr] = _cast_driver_value(override_attr, raw_value)
        try:
            model = model_cls(**kwargs)
        except ValueError:
            continue
        try:
            model.run()
        except ValueError:
            pass
        mass = getattr(model, component.mass_attr, None)
        if mass is None:
            continue
        masses[i] = mass
        cost = getattr(model, component.cost_attr, None)
        if cost is not None:
            costs[i] = cost
        if isinstance(driver, str):
            _label, _units, scale = DRIVER_INFO.get(driver, (driver, "", 1.0))
            display[i] = raw_value * scale
        else:
            try:
                display[i] = driver.display_from_entry({**kwargs, **model.get_results()})
            except TypeError:
                pass
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
        # Floor at a small positive raw value: the captured display bound can dip to (or below)
        # zero once empirical points are included in autoscale, but every model input this
        # inverts back to (rotor_diameter, rated_power_kw, tower_length, ...) must stay positive.
        return max(display_bounds[0] / scale, 1.0), max(display_bounds[1] / scale, 1.0)

    override_attr = _override_attr(driver)
    safe_kwargs = _safe_upstream_kwargs(
        model_cls, base_kwargs, component.mass_attr, component.cost_attr
    )

    def display_at(raw_value: float) -> float:
        """The composite driver's display value at `raw_value`. `model.run()` computes every
        component's mass as a side effect, in a fixed sequence, so it can raise on some *other*,
        later-computed component going invalid — `safe_kwargs` (see
        :py:func:`_safe_upstream_kwargs`) heads off most of that, and any failure that slips
        through is salvaged the same way :py:func:`_sweep_single` does rather than immediately
        giving up. Returns NaN only if the needed quantities genuinely aren't available, which the
        search below treats as "outside the domain" and backs off from rather than crashing.
        """
        kwargs = {**base_kwargs, **safe_kwargs}
        kwargs[override_attr] = _cast_driver_value(override_attr, raw_value)
        try:
            model = model_cls(**kwargs)
        except ValueError:
            return math.nan
        try:
            model.run()
        except ValueError:
            pass
        try:
            return driver.display_from_entry({**kwargs, **model.get_results()})
        except TypeError:
            return math.nan

    results = []
    for target in display_bounds:
        lo, hi = search_raw_range
        d_lo, d_hi = display_at(lo), display_at(hi)
        tries = 0
        while not math.isnan(d_hi) and d_hi < target and tries < 25:
            hi *= 1.5
            d_hi = display_at(hi)
            tries += 1
        tries = 0
        while not math.isnan(d_lo) and d_lo > target and tries < 25:
            lo = max(lo / 1.5, 1.0)
            d_lo = display_at(lo)
            tries += 1
        for _ in range(40):
            mid = (lo + hi) / 2
            d_mid = display_at(mid)
            if math.isnan(d_mid) or d_mid < target:
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
    ax,
    component: ComponentSpec,
    driver: Driver,
    curves: dict,
    config_cache: dict,
    models: dict[str, type],
    configs: dict[str, dict],
    marker_map: dict,
    color_map: dict,
) -> None:
    if component.label not in NO_LINE_COMPONENTS:
        for model_name, data in curves.items():
            ax.plot(
                data["driver_display"],
                data["mass"] * MASS_SCALE,
                color=color_map[model_name],
                lw=2.5,
            )
    for model_name in models:
        for config_name in configs:
            entry = config_cache[model_name].get(config_name)
            if entry is None:
                continue
            x = _driver_display_value(driver, entry)
            if x is None:
                continue
            ax.scatter(
                x,
                entry[component.mass_attr] * MASS_SCALE,
                marker=marker_map[config_name],
                color=color_map[model_name],
                s=110,
                edgecolor="black",
                linewidth=0.6,
                zorder=5,
            )


def _place_legend(fig, handles: list, max_cols_per_row: int = 7) -> int:
    """Places `handles` as a figure-level legend, wrapped onto as few rows as fit within
    `max_cols_per_row` columns each, rather than forcing every handle onto a single hard-coded-
    width row — which silently overflowed (entries truncated or spilling past the figure edge)
    once enough models/configs/overlays were present, e.g. after a third model was added.

    Returns:
        int: The number of rows the legend used, so the caller can reserve proportional bottom
            margin for it in ``fig.tight_layout(rect=...)``.
    """
    n_total = len(handles)
    n_rows = max(1, math.ceil(n_total / max_cols_per_row))
    ncol = math.ceil(n_total / n_rows)
    fig.legend(
        handles=handles,
        loc="lower center",
        ncol=ncol,
        bbox_to_anchor=(0.5, 0.01),
        frameon=False,
        fontsize=9,
    )
    return n_rows


def _draw_cost_panel(
    ax,
    component: ComponentSpec,
    driver: Driver,
    curves: dict,
    config_cache: dict,
    models: dict[str, type],
    configs: dict[str, dict],
    marker_map: dict,
    color_map: dict,
) -> None:
    # Unlike the mass panels, "total" components (NO_LINE_COMPONENTS) still get a real cost line
    # here: this panel's cost is always a direct sweep of one real attrs field (e.g.
    # `nacelle_cost`) against one canonical driver, not an approximation reused across mismatched
    # per-model mass drivers, so there's no reason to suppress it.
    for model_name, data in curves.items():
        ax.plot(
            data["driver_display"], data["cost"] * COST_SCALE, color=color_map[model_name], lw=2.5
        )
    for model_name in models:
        for config_name in configs:
            entry = config_cache[model_name].get(config_name)
            if entry is None:
                continue
            x = _driver_display_value(driver, entry)
            if x is None:
                continue
            ax.scatter(
                x,
                entry[component.cost_attr] * COST_SCALE,
                marker=marker_map[config_name],
                color=color_map[model_name],
                s=110,
                edgecolor="black",
                linewidth=0.6,
                zorder=5,
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
    empirical_df: pd.DataFrame | None = None,
    benchmark_df: pd.DataFrame | None = None,
):
    """Plots `component` mass vs. each driving parameter next to cost vs. its own relevant
    parameter (rotor diameter for the blade/rotor family, hub height for the tower, turbine
    rating for everything else — see :py:data:`COST_PANEL_DRIVER`).

    One mass panel is drawn per distinct driver among `models` for this component (adapting to
    however many different drivers they actually use), followed by a single cost panel. Every
    model is its own colored line and every named configuration is marked with a consistent
    marker shape on every panel. Axis limits are set from each panel's natural (padded) sweep
    range, then every curve — including a flat reference line for any model whose mass is a
    constant for this component — is redrawn stretched across those frozen limits, so every line
    reaches the edges of its panel. Each mass panel's title shows the literal formula (with live
    coefficient values) for every model drawn there, including a defining line for any
    intermediate quantity (blade mass, bedplate mass, rotor torque) the formula is written in
    terms of; the cost panel's title keeps showing "cost = k·mass" (still useful even though the
    panel's own x-axis isn't mass). "Total" components show what they sum instead of a formula,
    and the nacelle/turbine totals additionally skip lines entirely (see module docstring).

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
    cost_driver = COST_PANEL_DRIVER[component.label]

    config_names = list(configs)
    marker_map = {
        name: CONFIG_MARKERS[i % len(CONFIG_MARKERS)] for i, name in enumerate(config_names)
    }
    model_names = list(models)
    color_map = {name: _model_color(name, i) for i, name in enumerate(model_names)}
    constant_models = _constant_models(component, models)
    is_aggregate = component.label in AGGREGATE_COMPONENTS
    show_lines = component.label not in NO_LINE_COMPONENTS

    # ---- pass 1: natural (padded) ranges, draw curves + markers + empirical/benchmark points,
    # then capture axis limits. The overlays are drawn here (not after limits are frozen) so every
    # overlaid point participates in autoscale and stays visible inside the plot, even one that
    # falls outside the model curves' own natural sweep range. Applies regardless of `show_lines`,
    # since a no-line total (nacelle, turbine, ...) can still be directly measured in the data even
    # though it has no single driving parameter to sweep.
    natural_curves: dict[str, dict] = {}
    owners_by_key: dict[str, dict[str, type]] = {}
    natural_raw_ranges: dict[str, tuple[float, float]] = {}
    has_empirical = False
    for ax, driver in zip(mass_axes, panel_drivers):
        owners = _owners_for_driver(component, models, driver)
        owners_by_key[_driver_key(driver)] = owners
        raw_range = _driver_range(config_cache, _override_attr(driver))
        natural_raw_ranges[_driver_key(driver)] = raw_range
        curves = _sweep_curve(component, driver, owners, base_kwargs, raw_range, n_points)
        natural_curves[_driver_key(driver)] = curves
        _draw_mass_panel(
            ax, component, driver, curves, config_cache, models, configs, marker_map, color_map
        )
        points = _empirical_mass_points(empirical_df, component, driver, base_kwargs)
        if points is not None:
            ax.scatter(
                *points,
                color="0.55",
                s=16,
                alpha=0.35,
                edgecolor=OVERLAY_EDGE_COLOR,
                linewidth=OVERLAY_EDGE_LINEWIDTH,
                zorder=EMPIRICAL_ZORDER,
            )
            has_empirical = True

    cost_line_models = {
        name: cls for name, cls in models.items() if _cost_line_valid(component, cls, cost_driver)
    }
    cost_raw_range = _driver_range(config_cache, cost_driver)
    cost_natural_curves = _sweep_curve(
        component, cost_driver, cost_line_models, base_kwargs, cost_raw_range, n_points
    )
    _draw_cost_panel(
        ax_cost,
        component,
        cost_driver,
        cost_natural_curves,
        config_cache,
        models,
        configs,
        marker_map,
        color_map,
    )
    cost_points = _empirical_cost_points(empirical_df, component, cost_driver, base_kwargs)
    if cost_points is not None:
        ax_cost.scatter(
            *cost_points,
            color="0.55",
            s=16,
            alpha=0.35,
            edgecolor=OVERLAY_EDGE_COLOR,
            linewidth=OVERLAY_EDGE_LINEWIDTH,
            zorder=EMPIRICAL_ZORDER,
        )
        has_empirical = True
    benchmark_overlay = BENCHMARK_OVERLAY.get(component.label)
    has_benchmark = False
    if benchmark_overlay is not None:
        wm_categories, mult_key = benchmark_overlay
        bench_points = _benchmark_points(benchmark_df, wm_categories, cost_driver)
        if bench_points is not None:
            bench_x, bench_y = bench_points
            if mult_key is not None:
                bench_y = bench_y / base_kwargs[mult_key]
            ax_cost.scatter(
                bench_x,
                bench_y,
                color=BENCHMARK_COLOR,
                s=14,
                alpha=0.4,
                edgecolor=OVERLAY_EDGE_COLOR,
                linewidth=OVERLAY_EDGE_LINEWIDTH,
                zorder=BENCHMARK_ZORDER,
            )
            has_benchmark = True

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
    # Mass panels stay gated by `show_lines`: for a "total" component, its subcomponents don't
    # share one driving parameter, so a single swept mass curve would misrepresent it. The cost
    # panel isn't gated the same way — it always sweeps one real attrs field (e.g. `nacelle_cost`)
    # against one canonical driver, which is well-defined regardless of component.
    if show_lines:
        for ax, driver in zip(mass_axes, panel_drivers):
            xlim, _ylim = captured[ax]
            owners = owners_by_key[_driver_key(driver)]
            for model_name, model_cls in owners.items():
                raw_lo, raw_hi = _raw_range_for_display(
                    component,
                    driver,
                    model_cls,
                    base_kwargs,
                    xlim,
                    natural_raw_ranges[_driver_key(driver)],
                )
                raw_range = (min(raw_lo, raw_hi), max(raw_lo, raw_hi))
                data = _sweep_single(component, driver, model_cls, base_kwargs, raw_range, n_points)
                ax.plot(
                    data["driver_display"],
                    data["mass"] * MASS_SCALE,
                    color=color_map[model_name],
                    lw=2.5,
                )
            for model_name in constant_models:
                const_mass = _constant_value(model_name, config_cache, component.mass_attr)
                if const_mass is not None:
                    ax.plot(
                        xlim,
                        [const_mass * MASS_SCALE, const_mass * MASS_SCALE],
                        color=color_map[model_name],
                        lw=2.5,
                        ls="--",
                    )

    cost_xlim, _cost_ylim = captured[ax_cost]
    for model_name, model_cls in cost_line_models.items():
        raw_lo, raw_hi = _raw_range_for_display(
            component, cost_driver, model_cls, base_kwargs, cost_xlim, cost_raw_range
        )
        raw_range = (min(raw_lo, raw_hi), max(raw_lo, raw_hi))
        data = _sweep_single(component, cost_driver, model_cls, base_kwargs, raw_range, n_points)
        ax_cost.plot(
            data["driver_display"],
            data["cost"] * COST_SCALE,
            color=color_map[model_name],
            lw=2.5,
        )

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
            max_title_lines = max(
                max_title_lines, _set_stacked_title(ax, [(n, t) for n, t in lines if t])
            )

    cost_label, cost_units = _driver_label_units(cost_driver)
    ax_cost.set_xlabel(f"{cost_label} ({cost_units})" if cost_units else cost_label)
    ax_cost.set_ylabel("Cost ($k)")
    ax_cost.xaxis.set_major_locator(MaxNLocator(nbins=6))
    ax_cost.xaxis.set_major_formatter(FuncFormatter(_fmt_tick))
    ax_cost.yaxis.set_major_formatter(FuncFormatter(_fmt_tick))
    plt.setp(ax_cost.get_xticklabels(), rotation=20, ha="right")
    ax_cost.grid(alpha=0.3)
    if not is_aggregate:
        # Kept as "cost = k·mass" (not cost vs. this panel's own x-axis) since it's the actual
        # formula CSMBase computes cost from, and remains a useful reference regardless of what
        # the panel is plotted against.
        cost_lines = []
        for model_name in model_names:
            slope = _average_slope(model_name, config_cache, component)
            if slope is not None:
                cost_lines.append((model_name, f"cost = {_fmt_num(slope)}·mass"))
        max_title_lines = max(max_title_lines, _set_stacked_title(ax_cost, cost_lines))

    model_handles = [
        Line2D([0], [0], color=color_map[name], lw=2.5, label=name) for name in model_names
    ]
    config_handles = [
        Line2D(
            [0],
            [0],
            marker=marker_map[name],
            color="none",
            markerfacecolor="white",
            markeredgecolor="black",
            markersize=9,
            label=name,
        )
        for name in config_names
    ]
    empirical_handle = (
        [
            Line2D(
                [0],
                [0],
                marker="o",
                color="none",
                markerfacecolor="0.55",
                markeredgecolor="none",
                alpha=0.6,
                markersize=7,
                label="Empirical data",
            )
        ]
        if has_empirical
        else []
    )
    benchmark_handle = (
        [
            Line2D(
                [0],
                [0],
                marker="o",
                color="none",
                markerfacecolor=BENCHMARK_COLOR,
                markeredgecolor="none",
                alpha=0.7,
                markersize=7,
                label="2026 Benchmark",
            )
        ]
        if has_benchmark
        else []
    )
    n_legend_rows = _place_legend(
        fig, model_handles + config_handles + empirical_handle + benchmark_handle
    )

    fig.tight_layout(rect=(0, 0.045 + 0.045 * n_legend_rows, 1, 0.90))

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
    empirical_csv: str | Path | None = None,
    benchmark_csv: str | Path | None = None,
) -> dict[str, Path]:
    """Generates and saves one mass-and-cost figure per component.

    Args:
        output_dir (str | Path): Directory the figures are saved into (created if missing).
        models (dict[str, type] | None, optional): Mapping of model name to a ``CSMBase``
            subclass to compare. Defaults to :py:data:`DEFAULT_MODELS`.
        configs (dict[str, dict] | None, optional): Mapping of configuration name to a raw
            turbine spec (see :py:func:`to_model_kwargs`). Defaults to
            :py:data:`DEFAULT_TURBINE_SPECS`.
        components (list[ComponentSpec] | None, optional): Components to plot. Defaults to
            :py:data:`ALL_COMPONENTS` (every component, including the always-zero-mass ones —
            Converter, Controls, Electrical Connection — since their cost is still meaningful;
            pass :py:data:`PLOT_COMPONENTS` instead to skip those three).
        empirical_csv (str | Path | None, optional): Path to an empirical measurements CSV to
            overlay as faint points behind the model curves (see :py:func:`load_empirical_data`
            for the expected columns). Defaults to None (no overlay).
        benchmark_csv (str | Path | None, optional): Path to a 2026 industry cost benchmark CSV
            to overlay on the cost panel of any component with a direct mapping (see
            :py:func:`load_benchmark_data`, :py:data:`BENCHMARK_OVERLAY`). Defaults to
            None (no overlay).

    Returns:
        dict[str, Path]: Mapping of component label to the saved PNG path.
    """
    models = models or DEFAULT_MODELS
    configs = configs or DEFAULT_TURBINE_SPECS
    components = components or ALL_COMPONENTS

    output_dir = Path(output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    base_kwargs = _base_config(configs)
    config_cache = _evaluate_all_configs(models, configs)
    empirical_df = load_empirical_data(empirical_csv)
    benchmark_df = load_benchmark_data(benchmark_csv)

    figure_paths = {}
    for component in components:
        fig = plot_component(
            component,
            models,
            config_cache,
            base_kwargs,
            configs,
            empirical_df=empirical_df,
            benchmark_df=benchmark_df,
        )
        path = output_dir / f"{_slugify(component.label)}.png"
        fig.savefig(path, dpi=175)
        plt.close(fig)
        figure_paths[component.label] = path
    return figure_paths


def _combined_cost_multiplier(
    component_label: str, multipliers: dict[str, str], values: dict
) -> float:
    mult_key = multipliers.get(component_label)
    return values[mult_key] if mult_key else 1.0


def _sweep_combined_cost(
    csm_components: list[ComponentSpec],
    multipliers: dict[str, str],
    model_cls: type,
    base_kwargs: dict,
    driver: str,
    raw_range: tuple[float, float],
    n_points: int = 60,
) -> dict[str, np.ndarray]:
    """Sweeps `driver` for `model_cls`, summing the cost of `csm_components` (each optionally
    scaled by a `base_kwargs` quantity via `multipliers`, e.g. num_bearings) at every point.

    Uses `_safe_upstream_kwargs` (see :py:func:`_sweep_single`) to stop an unrelated subsystem's
    formula from going invalid partway through `model.run()`'s fixed sequence and blocking a
    later-computed member of `csm_components`; whichever of their costs still couldn't be
    computed at a given point are simply left out of that point's sum, and a point is only left
    NaN if none of them were reached at all.
    """
    raw_grid = np.linspace(*raw_range, n_points)
    _label, _units, scale = DRIVER_INFO.get(driver, (driver, "", 1.0))
    display = raw_grid * scale
    costs = np.full(n_points, np.nan)
    target_attrs = [attr for c in csm_components for attr in (c.mass_attr, c.cost_attr)]
    safe_kwargs = _safe_upstream_kwargs(model_cls, base_kwargs, *target_attrs)
    for i, raw_value in enumerate(raw_grid):
        kwargs = {**base_kwargs, **safe_kwargs}
        kwargs[driver] = _cast_driver_value(driver, raw_value)
        model = model_cls(**kwargs)
        try:
            model.run()
        except ValueError:
            pass
        total = 0.0
        any_found = False
        for component in csm_components:
            cost = getattr(model, component.cost_attr, None)
            if cost is None:
                continue
            any_found = True
            total += cost * _combined_cost_multiplier(component.label, multipliers, kwargs)
        if any_found:
            costs[i] = total
    return {"driver_display": display, "cost": costs}


def _combined_cost_from_entry(
    entry: dict, csm_components: list[ComponentSpec], multipliers: dict[str, str]
) -> float | None:
    """Sums `csm_components`' costs (each optionally scaled per `multipliers`) from a config-cache
    entry (merged kwargs + :py:meth:`CSMBase.get_results`), or None if any component's cost is
    missing from `entry`.
    """
    costs = [entry.get(c.cost_attr) for c in csm_components]
    if any(c is None for c in costs):
        return None
    return sum(
        cost * _combined_cost_multiplier(component.label, multipliers, entry)
        for component, cost in zip(csm_components, costs)
    )


def plot_wm_comparison(
    wm_category: str,
    models: dict[str, type],
    config_cache: dict[str, dict[str, dict | None]],
    base_kwargs: dict,
    configs: dict[str, dict],
    benchmark_df: pd.DataFrame | None,
    panel_width: float = 9.5,
    height: float = 5.8,
    n_points: int = 60,
):
    """Compares CSM's combined cost for `wm_category` — the sum of its mapped CSM components, per
    :py:data:`WM_CATEGORY_MAPPING` — against the 2026 industry benchmark for that category, on a
    single cost-vs-driving-parameter panel. Follows the same natural-range-then-extend-to-frozen-
    limits approach as :py:func:`plot_component`'s panels.

    Returns:
        matplotlib.figure.Figure
    """
    mapping = WM_CATEGORY_MAPPING[wm_category]
    csm_components = [c for c in ALL_COMPONENTS if c.label in mapping.csm_components]
    driver = mapping.driver

    fig, ax = plt.subplots(figsize=(panel_width, height))
    config_names = list(configs)
    marker_map = {
        name: CONFIG_MARKERS[i % len(CONFIG_MARKERS)] for i, name in enumerate(config_names)
    }
    model_names = list(models)
    color_map = {name: _model_color(name, i) for i, name in enumerate(model_names)}

    # Only draw a line for a model if *every* mapped CSM component genuinely uses `driver` as its
    # own real (mass-panel) driver for that model — otherwise the combined-sum line would be an
    # artifact of holding some component's actual driver fixed at an arbitrary reference value
    # rather than a faithful "cost as a function of `driver`" (see `_cost_driver_matches`).
    # Markers, computed from each configuration's real full inputs, stay valid regardless.
    line_models = {
        name: cls
        for name, cls in models.items()
        if all(_cost_driver_matches(c, cls, driver) for c in csm_components)
    }
    raw_range = _driver_range(config_cache, driver)
    natural_curves = {
        name: _sweep_combined_cost(
            csm_components, mapping.multipliers, cls, base_kwargs, driver, raw_range, n_points
        )
        for name, cls in line_models.items()
    }
    for model_name, data in natural_curves.items():
        ax.plot(
            data["driver_display"], data["cost"] * COST_SCALE, color=color_map[model_name], lw=2.5
        )
    for model_name in models:
        for config_name in configs:
            entry = config_cache[model_name].get(config_name)
            if entry is None:
                continue
            x = _driver_display_value(driver, entry)
            cost = _combined_cost_from_entry(entry, csm_components, mapping.multipliers)
            if x is None or cost is None:
                continue
            ax.scatter(
                x,
                cost * COST_SCALE,
                marker=marker_map[config_name],
                color=color_map[model_name],
                s=110,
                edgecolor="black",
                linewidth=0.6,
                zorder=5,
            )
    bench_points = _benchmark_points(benchmark_df, [wm_category], driver)
    has_benchmark = bench_points is not None
    if has_benchmark:
        ax.scatter(
            *bench_points,
            color=BENCHMARK_COLOR,
            s=14,
            alpha=0.4,
            edgecolor=OVERLAY_EDGE_COLOR,
            linewidth=OVERLAY_EDGE_LINEWIDTH,
            zorder=BENCHMARK_ZORDER,
        )

    xlim, ylim = ax.get_xlim(), ax.get_ylim()
    for line in list(ax.get_lines()):
        line.remove()
    ax.set_xlim(*xlim)
    ax.set_ylim(*ylim)

    # `_raw_range_for_display` only needs a ComponentSpec for its (unused, on this plain-string
    # driver) composite-driver branch, so any of `csm_components` works as a placeholder.
    placeholder_component = csm_components[0]
    for model_name, model_cls in line_models.items():
        raw_lo, raw_hi = _raw_range_for_display(
            placeholder_component, driver, model_cls, base_kwargs, xlim, raw_range
        )
        extended_range = (min(raw_lo, raw_hi), max(raw_lo, raw_hi))
        data = _sweep_combined_cost(
            csm_components,
            mapping.multipliers,
            model_cls,
            base_kwargs,
            driver,
            extended_range,
            n_points,
        )
        ax.plot(
            data["driver_display"], data["cost"] * COST_SCALE, color=color_map[model_name], lw=2.5
        )

    ax.set_xlim(*xlim)
    ax.set_ylim(*ylim)

    label, units = _driver_label_units(driver)
    ax.set_xlabel(f"{label} ({units})" if units else label)
    ax.set_ylabel("Cost ($k)")
    ax.xaxis.set_major_locator(MaxNLocator(nbins=6))
    ax.xaxis.set_major_formatter(FuncFormatter(_fmt_tick))
    ax.yaxis.set_major_formatter(FuncFormatter(_fmt_tick))
    plt.setp(ax.get_xticklabels(), rotation=20, ha="right")
    ax.grid(alpha=0.3)

    model_handles = [
        Line2D([0], [0], color=color_map[name], lw=2.5, label=name) for name in model_names
    ]
    config_handles = [
        Line2D(
            [0],
            [0],
            marker=marker_map[name],
            color="none",
            markerfacecolor="white",
            markeredgecolor="black",
            markersize=9,
            label=name,
        )
        for name in config_names
    ]
    benchmark_handle = (
        [
            Line2D(
                [0],
                [0],
                marker="o",
                color="none",
                markerfacecolor=BENCHMARK_COLOR,
                markeredgecolor="none",
                alpha=0.7,
                markersize=7,
                label="2026 Benchmark",
            )
        ]
        if has_benchmark
        else []
    )
    n_legend_rows = _place_legend(fig, model_handles + config_handles + benchmark_handle)

    fig.tight_layout(rect=(0, 0.045 + 0.045 * n_legend_rows, 1, 0.90))

    wrapped = textwrap.fill(f"= {' + '.join(mapping.csm_components)}", width=70)
    n_lines = wrapped.count("\n") + 1
    fig.suptitle(f"{wm_category} (Industry Benchmark)", fontsize=15, fontweight="bold", y=0.99)
    fig.text(0.5, 0.955, wrapped, ha="center", va="top", fontsize=9, style="italic")
    fig.subplots_adjust(top=0.90 - 0.045 * n_lines)

    return fig


def generate_wm_comparison_figures(
    output_dir: str | Path,
    models: dict[str, type] | None = None,
    configs: dict[str, dict] | None = None,
    benchmark_csv: str | Path | None = None,
    wm_categories: list[str] | None = None,
) -> dict[str, Path]:
    """Generates and saves one combined CSM-vs-industry-benchmark figure per multi-component WM
    category (see :py:data:`COMBINED_WM_CATEGORIES`) — the categories from
    :py:data:`WM_CATEGORY_MAPPING` that sum more than one CSM component, or apply a multiplier,
    and so can't be shown as a direct overlay on a single existing component figure.

    Args:
        output_dir (str | Path): Directory the figures are saved into (created if missing).
        models (dict[str, type] | None, optional): Mapping of model name to a ``CSMBase``
            subclass to compare. Defaults to :py:data:`DEFAULT_MODELS`.
        configs (dict[str, dict] | None, optional): Mapping of configuration name to a raw
            turbine spec. Defaults to :py:data:`DEFAULT_TURBINE_SPECS`.
        benchmark_csv (str | Path | None, optional): Path to a 2026 industry cost benchmark CSV
            (see :py:func:`load_benchmark_data`). Defaults to None (no overlay, CSM-only lines).
        wm_categories (list[str] | None, optional): Which categories to generate. Defaults to
            :py:data:`COMBINED_WM_CATEGORIES` (all of them).

    Returns:
        dict[str, Path]: Mapping of WM category name to the saved PNG path.
    """
    models = models or DEFAULT_MODELS
    configs = configs or DEFAULT_TURBINE_SPECS
    wm_categories = wm_categories or COMBINED_WM_CATEGORIES

    output_dir = Path(output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    base_kwargs = _base_config(configs)
    config_cache = _evaluate_all_configs(models, configs)
    benchmark_df = load_benchmark_data(benchmark_csv)

    figure_paths = {}
    for wm_category in wm_categories:
        fig = plot_wm_comparison(
            wm_category, models, config_cache, base_kwargs, configs, benchmark_df
        )
        path = output_dir / f"wm_{_slugify(wm_category)}.png"
        fig.savefig(path, dpi=175)
        plt.close(fig)
        figure_paths[wm_category] = path
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
    empirical_csv: str | Path | None = None,
    benchmark_csv: str | Path | None = None,
) -> dict[str, Path]:
    """Runs the full pipeline: per-component figures, combined WM-category comparison figures, a
    summary report, and a slide deck.

    Args:
        output_dir (str | Path, optional): Directory the figures, report image, and deck are
            saved into. Defaults to "output/csm_comparison".
        models (dict[str, type] | None, optional): Mapping of model name to a ``CSMBase``
            subclass to compare. Defaults to :py:data:`DEFAULT_MODELS`.
        configs (dict[str, dict] | None, optional): Mapping of configuration name to a raw
            turbine spec. Defaults to :py:data:`DEFAULT_TURBINE_SPECS`.
        empirical_csv (str | Path | None, optional): Path to an empirical measurements CSV to
            overlay behind the figures' model curves (see :py:func:`load_empirical_data`).
            Defaults to None (no overlay); the summary report table is unaffected either way.
        benchmark_csv (str | Path | None, optional): Path to a 2026 industry cost benchmark CSV
            to overlay on cost panels and to compare against in the combined WM-category figures
            (see :py:func:`load_benchmark_data`). Defaults to None (CSM-only lines/no overlay).

    Returns:
        dict[str, Path]: Paths to the figures directory, summary report image, and presentation.
    """
    output_dir = Path(output_dir).resolve()
    figures_dir = output_dir / "figures"
    figure_paths = generate_all_figures(
        figures_dir,
        models=models,
        configs=configs,
        empirical_csv=empirical_csv,
        benchmark_csv=benchmark_csv,
    )
    wm_figure_paths = generate_wm_comparison_figures(
        figures_dir,
        models=models,
        configs=configs,
        benchmark_csv=benchmark_csv,
    )

    report_df = build_report_dataframe(models=models, configs=configs)
    report_image_path = render_report_image(report_df, output_dir / "summary_report.png")

    pptx_path = build_presentation(
        output_dir / "csm_comparison.pptx", {**figure_paths, **wm_figure_paths}, report_image_path
    )
    return {
        "figures_dir": figures_dir,
        "report_image": report_image_path,
        "presentation": pptx_path,
    }


if __name__ == "__main__":
    # Set empirical_csv/benchmark_csv to None to fall back to the plain model-vs-model comparison.
    paths = generate_comparison(
        empirical_csv="csm/us_lbw_csm_2026_data.csv",
        benchmark_csv="csm/WM_wind_capex_benchmark_data_geared.csv",
    )
    for key, path in paths.items():
        print(f"{key}: {path}")
