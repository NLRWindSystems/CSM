"""Comparison figures for the offshore wind (OSW) models — :py:class:`csm.models.nlr2024_osw_fb.
OffshoreFB2024NLR` and :py:class:`csm.models.nlr2024_osw_fl.OffshoreFL2024NLR` — the offshore
analog of :py:mod:`csm.tools.experimental.plotting`, scoped to
:py:class:`csm.models.base_osw_model.OSWBase`'s four top-level assemblies (see that module for why
there's no subcomponent breakdown).

Mass is shared between fixed-bottom and floating, so every mass panel shows one line. Cost is fit
separately per offshore type, so every cost panel shows two — fixed-bottom and floating — plus
the benchmark points they were each fit from. Turbine's cost panel is the one exception: since it
has no closed-form fit of its own (see :py:func:`_plot_turbine_cost_panel`), it shows only the
model's own value at each reference turbine, not a connecting line.
"""

from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from pptx import Presentation
from attrs import fields as attrs_fields
from pptx.util import Pt, Inches
from matplotlib.lines import Line2D

from csm.models.nlr2024_osw_fb import OffshoreFB2024NLR
from csm.models.nlr2024_osw_fl import OffshoreFL2024NLR
from csm.tools.experimental.plotting import _fit_dimensions
from csm.tools.experimental.build_custom_osw_model import (
    MASS_SPECS,
    load_benchmark_data,
    load_empirical_data,
)


MODELS = {"Fixed-Bottom": OffshoreFB2024NLR, "Floating": OffshoreFL2024NLR}
OFFSHORE_TYPE_FOR = {"Fixed-Bottom": "fixed-bottom", "Floating": "floating"}

# Same house style csm.tools.experimental.plotting uses for the land-based comparison figures —
# BENCHMARK_COLOR, the OVERLAY_*/*_ZORDER constants, and CONFIG_MARKER_* are its exact values.
MODEL_COLORS = {"Fixed-Bottom": "#1F77B4", "Floating": "#FF7F0E"}
MASS_COLOR = "#2CA02C"
EMPIRICAL_COLOR = "0.55"
BENCHMARK_COLOR = "#17BECF"
OVERLAY_EDGE_COLOR = "black"
OVERLAY_EDGE_LINEWIDTH = 0.4
MODEL_LINE_WIDTH = 1.5
MODEL_LINE_ZORDER = 1
EMPIRICAL_ALPHA = 1.0
GRID_ALPHA = 0.4
CONFIG_MARKER_SIZE = 40
CONFIG_MARKER_EDGE_LINEWIDTH = 0.6
CONFIG_MARKER_ZORDER = 5
CONFIG_MARKERS = ["*", "^", "s", "D", "P", "X", "o", "v"]

# Real-world data is always drawn last/highest, regardless of panel or draw order, so a model
# line or config marker never hides it — matching csm.tools.experimental.plotting's own
# EMPIRICAL_ZORDER/BENCHMARK_ZORDER convention (benchmark on top of empirical, both well above
# every line and config marker).
EMPIRICAL_ZORDER = 20
BENCHMARK_ZORDER = 21

# Per your request: fixed-bottom benchmark points are a small filled circle, floating a small thin
# "x" — both the same BENCHMARK_COLOR, distinguished by shape alone rather than color.
BENCHMARK_MARKERS = {"Fixed-Bottom": "o", "Floating": "x"}
BENCHMARK_MARKER_SIZE = 26

# Legend layout (see _place_legend): four fixed columns — every turbine configuration (marker
# shape only, colored neutrally since the same config renders in a different series color on
# almost every panel) split across two columns so it doesn't dwarf the other groups, then the
# real-world data sources, then the model lines/points, in that order.
LEGEND_NEUTRAL_COLOR = "0.35"
DATA_COLUMN_LABELS = ["Empirical data", "Benchmark (Fixed-Bottom)", "Benchmark (Floating)"]
MODEL_COLUMN_LABELS = ["2024 (mass, both)", "2024 (Fixed-Bottom)", "2024 (Floating)"]

# Seven real, distinct offshore turbines spanning the utility-scale range this data actually
# covers, used as marked reference points on every figure and, for Turbine specifically, as the
# points its own panels evaluate the assembled model at (see _plot_turbine_mass_panel/
# _plot_turbine_cost_panel — Turbine draws no connecting line, so each of these needs its own
# real rotor diameter, hub height, *and* rated power all at once, unlike Rotor/Nacelle/Tower
# which each need only one). Rotor diameter/hub height/rated power are real values from the same
# turbine model wherever osw_csm_2026_data.csv's own rows give them together (V164-7.0 and
# SWT-6.0-154 don't — their hub heights are estimated from comparable real-world installations,
# since the CSV itself never reports hub height for either).
DEFAULT_TURBINE_SPECS: dict[str, dict[str, float]] = {
    "SWT-6.0-154": {"rotor_diameter": 154.0, "hub_height": 97.0, "rated_power_kw": 6000.0},
    "V164-7.0": {"rotor_diameter": 164.0, "hub_height": 100.0, "rated_power_kw": 7000.0},
    "V174-9.5": {"rotor_diameter": 174.0, "hub_height": 119.0, "rated_power_kw": 9500.0},
    "SG-11.0-200": {"rotor_diameter": 200.0, "hub_height": 133.0, "rated_power_kw": 11000.0},
    "Haliade-X 13MW": {"rotor_diameter": 220.0, "hub_height": 138.0, "rated_power_kw": 13000.0},
    "SG-14.0-236": {"rotor_diameter": 236.0, "hub_height": 144.0, "rated_power_kw": 14000.0},
    "V236-15": {"rotor_diameter": 236.0, "hub_height": 143.0, "rated_power_kw": 15000.0},
}

# Component -> which DEFAULT_TURBINE_SPECS key (and axis label) its own natural driver reads from.
DRIVER_KEY = {
    "Blade": ("rotor_diameter", "Rotor Diameter (m)"),
    "Rotor": ("rotor_diameter", "Rotor Diameter (m)"),
    "Tower": ("hub_height", "Hub Height (m)"),
    "Nacelle": ("rated_power_kw", "Rated Power (MW)"),
}

# Rated power is fit and stored in kW throughout (matching OSWBase's own units), but displayed in
# MW — the industry-standard unit for turbine nameplate capacity. Applied only at the point a
# rated-power x-value is actually plotted; every formula evaluation still uses the raw kW value
# the fitted coefficients are calibrated against.
RATED_POWER_DISPLAY_DIVISOR = 1000.0


def _display_x(x_key: str, x):
    """Converts a raw driver value (or array) to display units — currently only rated power,
    kW -> MW (see `RATED_POWER_DISPLAY_DIVISOR`); every other driver displays in its own native
    units already.
    """
    return x / RATED_POWER_DISPLAY_DIVISOR if x_key == "rated_power_kw" else x


def _format_thousands(ax) -> None:
    """Comma-delimits both axes' tick labels (e.g. "250,000" instead of matplotlib's default
    "1e6"-offset scientific notation).
    """
    formatter = mticker.StrMethodFormatter("{x:,.0f}")
    ax.xaxis.set_major_formatter(formatter)
    ax.yaxis.set_major_formatter(formatter)


# Symbol standing in for each driver in the formula titles (see _mass_formula_text).
DRIVER_SYMBOL = {"rotor_diameter": "D", "hub_height": "H", "rated_power_kw": "P"}


def _coeff(model_cls: type, name: str) -> float:
    """Reads a model class's default (coefficient) value for one of its attrs fields."""
    for f in attrs_fields(model_cls):
        if f.name == name:
            return f.default
    raise AttributeError(f"{model_cls.__name__} has no field '{name}'")


def _fmt_num(x: float) -> str:
    return f"{x:.4g}"


def _fmt_coef(x: float) -> str:
    """Formats a coefficient with an explicit sign, for use as a trailing "+ b" / "- b" term."""
    return f"{x:+.4g}"


def _mass_coeffs(label: str) -> list[float]:
    """The already-fitted mass coefficients for `label`, read straight off `OffshoreFB2024NLR` —
    mass is shared with `OffshoreFL2024NLR`, so either subclass gives the same values.
    """
    spec = MASS_SPECS[label]
    return [_coeff(OffshoreFB2024NLR, p) for p in spec.params]


def _mass_formula_text(label: str) -> str:
    """`m = ...` formula text for `label`'s (shared) mass fit, in the same style
    :py:mod:`csm.tools.experimental.plotting` uses for the land-based models.
    """
    x_key, _ = DRIVER_KEY[label]
    x_symbol = DRIVER_SYMBOL[x_key]
    coeffs = _mass_coeffs(label)
    if label == "Blade":
        coeff, exp = coeffs
        return f"m = {_fmt_num(coeff)}·(D/2)^{_fmt_num(exp)}"
    if label == "Nacelle":
        coeff, intercept = coeffs
        return f"m = {_fmt_num(coeff)}·{x_symbol} {_fmt_coef(intercept)}"
    coeff, exp = coeffs
    return f"m = {_fmt_num(coeff)}·{x_symbol}^{_fmt_num(exp)}"


def _cost_formula_text(label: str) -> dict[str, str]:
    """`cost = k·mass` formula text per offshore type for `label`'s cost fit."""
    field_name = f"{MASS_SPECS[label].csv_component}_mass_cost_coeff"
    return {
        model_label: f"cost = {_fmt_num(_coeff(model_cls, field_name))}·mass"
        for model_label, model_cls in MODELS.items()
    }


def _set_title(ax, lines: list[tuple[str, str]]) -> None:
    """Sets `ax`'s title to one "label: text" line per entry, stacked — the same
    :py:func:`csm.tools.experimental.plotting._set_stacked_title` convention (a real
    `ax.set_title` so `tight_layout` reserves space for it automatically).
    """
    if not lines:
        return
    text = "\n".join(f"{label}: {formula}" for label, formula in lines)
    ax.set_title(text, fontsize=8, linespacing=1.6)


def _empirical_points(label: str, empirical_df: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    """(x, mass) pairs for `label`'s own empirical rows, in the units `MASS_SPECS[label]`'s
    formula expects (already unit-converted, e.g. MW -> kW for Nacelle).
    """
    spec = MASS_SPECS[label]
    rows = empirical_df[empirical_df["Component"] == spec.csv_component]
    xs, ys = [], []
    for _, row in rows.iterrows():
        x = pd.to_numeric(row.get(spec.x_column), errors="coerce")
        mass = pd.to_numeric(row.get("mass (kg)"), errors="coerce")
        if pd.isna(x) or pd.isna(mass):
            continue
        xs.append(spec.x_transform(float(x)) if spec.x_transform else float(x))
        ys.append(float(mass))
    return np.array(xs, dtype=float), np.array(ys, dtype=float)


def _benchmark_rows(label: str, offshore_type: str, benchmark_df: pd.DataFrame) -> pd.DataFrame:
    spec = MASS_SPECS[label]
    if spec.benchmark_x_column is None:
        return benchmark_df.iloc[0:0]
    return benchmark_df[
        (benchmark_df["component"] == spec.csv_component)
        & (benchmark_df["offshore_type"] == offshore_type)
    ]


def _mass_benchmark_points(
    label: str, offshore_type: str, benchmark_df: pd.DataFrame
) -> tuple[np.ndarray, np.ndarray]:
    """(x, weight_kg) pairs for `label`'s own benchmark rows under `offshore_type` — the
    benchmark CSV's own weight readings, independent of the empirical CSV's.
    """
    spec = MASS_SPECS[label]
    xs, masses = [], []
    for _, row in _benchmark_rows(label, offshore_type, benchmark_df).iterrows():
        x = pd.to_numeric(row.get(spec.benchmark_x_column), errors="coerce")
        mass = pd.to_numeric(row.get("weight_kg"), errors="coerce")
        if pd.isna(x) or pd.isna(mass):
            continue
        xs.append(spec.x_transform(float(x)) if spec.x_transform else float(x))
        masses.append(float(mass))
    return np.array(xs, dtype=float), np.array(masses, dtype=float)


def _cost_benchmark_points(
    label: str, offshore_type: str, benchmark_df: pd.DataFrame
) -> tuple[np.ndarray, np.ndarray]:
    """(x, cost_usd) pairs for `label`'s own benchmark rows under `offshore_type`, converting
    each row's `value_$/MW` rate to an absolute dollar figure via its own nameplate capacity.
    """
    spec = MASS_SPECS[label]
    xs, costs = [], []
    for _, row in _benchmark_rows(label, offshore_type, benchmark_df).iterrows():
        x = pd.to_numeric(row.get(spec.benchmark_x_column), errors="coerce")
        capacity_mw = pd.to_numeric(row.get("turbine_nameplate_capacity"), errors="coerce")
        rate = pd.to_numeric(row.get("value_$/MW"), errors="coerce")
        if pd.isna(x) or pd.isna(capacity_mw) or pd.isna(rate):
            continue
        xs.append(spec.x_transform(float(x)) if spec.x_transform else float(x))
        costs.append(float(rate) * float(capacity_mw))
    return np.array(xs, dtype=float), np.array(costs, dtype=float)


def _turbine_rows(offshore_type: str, benchmark_df: pd.DataFrame) -> pd.DataFrame:
    return benchmark_df[
        (benchmark_df["component"] == "turbine") & (benchmark_df["offshore_type"] == offshore_type)
    ]


def _cost_empirical_points(label: str, empirical_df: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    """(x, cost_usd) pairs for `label`'s own empirical CSV rows with a usable cost value — shown
    once regardless of offshore type, the same way empirical mass points are, since there are so
    few (currently only Tower has any at all) that splitting them further would lose them.
    """
    spec = MASS_SPECS[label]
    rows = empirical_df[empirical_df["Component"] == spec.csv_component]
    xs, costs = [], []
    for _, row in rows.iterrows():
        x = pd.to_numeric(row.get(spec.x_column), errors="coerce")
        cost = pd.to_numeric(row.get("cost ($)"), errors="coerce")
        if pd.isna(x) or pd.isna(cost):
            continue
        xs.append(spec.x_transform(float(x)) if spec.x_transform else float(x))
        costs.append(float(cost))
    return np.array(xs, dtype=float), np.array(costs, dtype=float)


def _turbine_empirical_points(empirical_df: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    """(rated_power_kw, mass) pairs for the empirical CSV's own whole-turbine rows."""
    rows = empirical_df[empirical_df["Component"] == "turbine"]
    xs, ys = [], []
    for _, row in rows.iterrows():
        mw = pd.to_numeric(row.get("MW"), errors="coerce")
        mass = pd.to_numeric(row.get("mass (kg)"), errors="coerce")
        if pd.isna(mw) or pd.isna(mass):
            continue
        xs.append(float(mw) * 1000.0)
        ys.append(float(mass))
    return np.array(xs, dtype=float), np.array(ys, dtype=float)


def _turbine_cost_empirical_points(empirical_df: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    """(rated_power_kw, cost_usd) pairs for the empirical CSV's own whole-turbine rows with a
    usable cost value.
    """
    rows = empirical_df[empirical_df["Component"] == "turbine"]
    xs, costs = [], []
    for _, row in rows.iterrows():
        mw = pd.to_numeric(row.get("MW"), errors="coerce")
        cost = pd.to_numeric(row.get("cost ($)"), errors="coerce")
        if pd.isna(mw) or pd.isna(cost):
            continue
        xs.append(float(mw) * 1000.0)
        costs.append(float(cost))
    return np.array(xs, dtype=float), np.array(costs, dtype=float)


def _turbine_mass_benchmark_points(
    offshore_type: str, benchmark_df: pd.DataFrame
) -> tuple[np.ndarray, np.ndarray]:
    """(rated_power_kw, weight_kg) pairs for the benchmark CSV's own `component == "turbine"`
    rows under `offshore_type`.
    """
    xs, masses = [], []
    for _, row in _turbine_rows(offshore_type, benchmark_df).iterrows():
        capacity_mw = pd.to_numeric(row.get("turbine_nameplate_capacity"), errors="coerce")
        mass = pd.to_numeric(row.get("weight_kg"), errors="coerce")
        if pd.isna(capacity_mw) or pd.isna(mass):
            continue
        xs.append(float(capacity_mw) * 1000.0)
        masses.append(float(mass))
    return np.array(xs, dtype=float), np.array(masses, dtype=float)


def _turbine_cost_benchmark_points(
    offshore_type: str, benchmark_df: pd.DataFrame
) -> tuple[np.ndarray, np.ndarray]:
    """(rated_power_kw, cost_usd) pairs for the benchmark CSV's own `component == "turbine"` rows
    under `offshore_type` — including the capacity-only rows with no rotor diameter/hub height at
    all, since rated power is all a Turbine-vs-rated-power panel needs.
    """
    xs, costs = [], []
    for _, row in _turbine_rows(offshore_type, benchmark_df).iterrows():
        capacity_mw = pd.to_numeric(row.get("turbine_nameplate_capacity"), errors="coerce")
        rate = pd.to_numeric(row.get("value_$/MW"), errors="coerce")
        if pd.isna(capacity_mw) or pd.isna(rate):
            continue
        xs.append(float(capacity_mw) * 1000.0)
        costs.append(float(rate) * float(capacity_mw))
    return np.array(xs, dtype=float), np.array(costs, dtype=float)


def _driver_range(
    xs: np.ndarray, pad_low: float = 0.9, pad_high: float = 1.05
) -> tuple[float, float]:
    return float(np.min(xs)) * pad_low, float(np.max(xs)) * pad_high


def _legend_bottom_margin(nrows: int) -> float:
    """The `tight_layout(rect=(0, bottom, 1, 1))` fraction to reserve below the axes for a
    `_place_legend` legend that used `nrows` rows — the fixed four-column layout means one of the
    two config columns is almost always the tallest, so unlike the old shrink-to-fit legend, the
    space it needs is knowable directly from its row count rather than by measuring a rendered
    legend after the fact.
    """
    if nrows == 0:
        return 0.02
    return min(0.08 + 0.06 * nrows, 0.48)


def _config_legend_handle(index: int) -> Line2D:
    """A legend-only proxy marker for the `index`-th `DEFAULT_TURBINE_SPECS` entry, in
    `LEGEND_NEUTRAL_COLOR` rather than whatever series color it happens to render in on a given
    panel (mass panels draw every config in green, cost panels in blue/orange) — the marker
    *shape* is what identifies a turbine, so its legend swatch shouldn't imply one fixed color.
    """
    return Line2D(
        [],
        [],
        marker=CONFIG_MARKERS[index % len(CONFIG_MARKERS)],
        linestyle="none",
        markersize=7,
        markerfacecolor=LEGEND_NEUTRAL_COLOR,
        markeredgecolor="black",
        markeredgewidth=CONFIG_MARKER_EDGE_LINEWIDTH,
    )


def _place_legend(fig, *axes) -> int:
    """Places a below-axes legend in four fixed columns: every turbine configuration (split
    across the first two columns, so a 7-entry config list doesn't tower over the other groups),
    the real-world data sources (`DATA_COLUMN_LABELS`), and the model lines/points
    (`MODEL_COLUMN_LABELS`) — matplotlib fills a multi-column legend column-major (confirmed by
    inspecting rendered legend-text positions: consecutive entries in the handles/labels list
    share an x-coordinate, i.e. stack down one column, before the next chunk starts a new
    column), so getting four *columns* is just each group's entries concatenated in order, each
    padded to the tallest column's length with invisible blanks so every column lines up on the
    same `nrows` grid.

    Returns:
        int: The number of rows the legend used (the taller of the two config columns), so the
            caller can reserve enough bottom margin for it in `fig.tight_layout(rect=...)` —
            fixed at four columns rather than shrinking to fit like
            :py:mod:`csm.tools.experimental.plotting`'s own legend does, so the row count (and
            therefore the margin needed) is knowable up front instead.
    """
    handles, labels = [], []
    seen = set()
    for ax in axes:
        for handle, label in zip(*ax.get_legend_handles_labels(), strict=True):
            if label not in seen and label not in DEFAULT_TURBINE_SPECS:
                seen.add(label)
                handles.append(handle)
                labels.append(label)

    config_entries = [
        (_config_legend_handle(i), name) for i, name in enumerate(DEFAULT_TURBINE_SPECS)
    ]
    split = -(-len(config_entries) // 2)  # ceil(n / 2)
    config_column_1 = config_entries[:split]
    config_column_2 = config_entries[split:]
    data_column = sorted(
        (
            (handle, label)
            for handle, label in zip(handles, labels, strict=True)
            if label in DATA_COLUMN_LABELS
        ),
        key=lambda hl: DATA_COLUMN_LABELS.index(hl[1]),
    )
    model_column = sorted(
        (
            (handle, label)
            for handle, label in zip(handles, labels, strict=True)
            if label in MODEL_COLUMN_LABELS
        ),
        key=lambda hl: MODEL_COLUMN_LABELS.index(hl[1]),
    )
    columns = [config_column_1, config_column_2, data_column, model_column]
    nrows = max(len(column) for column in columns)
    if nrows == 0:
        return 0

    blank_handle = Line2D([], [], color="none")
    grid_handles, grid_labels = [], []
    for column in columns:
        for row in range(nrows):
            handle, label = column[row] if row < len(column) else (blank_handle, " ")
            grid_handles.append(handle)
            grid_labels.append(label)

    fig.legend(
        grid_handles,
        grid_labels,
        loc="lower center",
        ncol=len(columns),
        frameon=False,
        bbox_to_anchor=(0.5, 0.01),
        handletextpad=0.6,
        columnspacing=1.4,
        fontsize=8,
    )
    return nrows


def _config_markers(x_key: str) -> list[tuple[str, float, str]]:
    """(config name, x value, marker) triples for every `DEFAULT_TURBINE_SPECS` entry, reading
    `x_key` (one of "rotor_diameter", "hub_height", "rated_power_kw") out of each config.
    """
    return [
        (name, spec[x_key], CONFIG_MARKERS[i % len(CONFIG_MARKERS)])
        for i, (name, spec) in enumerate(DEFAULT_TURBINE_SPECS.items())
    ]


def _scatter_benchmark(ax, xs, ys, model_label: str, note: str = "") -> None:
    if not xs.size:
        return
    marker = BENCHMARK_MARKERS[model_label]
    kwargs = (
        {"edgecolor": OVERLAY_EDGE_COLOR, "linewidth": OVERLAY_EDGE_LINEWIDTH}
        if marker == "o"
        else {"linewidth": 1.2}
    )
    ax.scatter(
        xs,
        ys,
        marker=marker,
        s=BENCHMARK_MARKER_SIZE,
        c=BENCHMARK_COLOR,
        zorder=BENCHMARK_ZORDER,
        label=f"Benchmark{note} ({model_label})",
        **kwargs,
    )


def _plot_mass_panel(
    ax, label: str, empirical_df: pd.DataFrame, benchmark_df: pd.DataFrame
) -> None:
    spec = MASS_SPECS[label]
    x_key, driver_label = DRIVER_KEY[label]
    coeffs = _mass_coeffs(label)

    xs_emp, ys_emp = _empirical_points(label, empirical_df)
    config_xs = np.array([x for _, x, _ in _config_markers(x_key)])
    x_lo, x_hi = _driver_range(np.concatenate([xs_emp, config_xs]) if xs_emp.size else config_xs)
    x_grid = np.linspace(x_lo, x_hi, 200)
    ax.plot(
        _display_x(x_key, x_grid),
        spec.formula(x_grid, *coeffs),
        color=MASS_COLOR,
        lw=MODEL_LINE_WIDTH,
        zorder=MODEL_LINE_ZORDER,
        label="2024 (mass, both)",
    )

    for name, x_val, marker in _config_markers(x_key):
        ax.scatter(
            [_display_x(x_key, x_val)],
            [spec.formula(x_val, *coeffs)],
            marker=marker,
            s=CONFIG_MARKER_SIZE,
            facecolor=MASS_COLOR,
            edgecolor="black",
            linewidth=CONFIG_MARKER_EDGE_LINEWIDTH,
            zorder=CONFIG_MARKER_ZORDER,
            label=name,
        )

    if xs_emp.size:
        ax.scatter(
            _display_x(x_key, xs_emp),
            ys_emp,
            c=EMPIRICAL_COLOR,
            alpha=EMPIRICAL_ALPHA,
            s=18,
            edgecolor=OVERLAY_EDGE_COLOR,
            linewidth=OVERLAY_EDGE_LINEWIDTH,
            zorder=EMPIRICAL_ZORDER,
            label="Empirical data",
        )
    for model_label in MODELS:
        xs_bench, masses_bench = _mass_benchmark_points(
            label, OFFSHORE_TYPE_FOR[model_label], benchmark_df
        )
        _scatter_benchmark(ax, _display_x(x_key, xs_bench), masses_bench, model_label)

    ax.set_xlabel(driver_label)
    ax.set_ylabel("Mass (kg)")
    ax.grid(alpha=GRID_ALPHA)
    _format_thousands(ax)
    _set_title(ax, [("2024", _mass_formula_text(label))])


def _plot_cost_panel(
    ax, label: str, empirical_df: pd.DataFrame, benchmark_df: pd.DataFrame
) -> None:
    spec = MASS_SPECS[label]
    x_key, driver_label = DRIVER_KEY[label]
    mass_coeffs = _mass_coeffs(label)
    config_xs = np.array([x for _, x, _ in _config_markers(x_key)])
    xs_emp, costs_emp = _cost_empirical_points(label, empirical_df)

    for model_label, model_cls in MODELS.items():
        offshore_type = OFFSHORE_TYPE_FOR[model_label]
        cost_coeff = _coeff(model_cls, f"{spec.csv_component}_mass_cost_coeff")
        xs_bench, costs_bench = _cost_benchmark_points(label, offshore_type, benchmark_df)
        x_lo, x_hi = _driver_range(
            np.concatenate([xs_bench, xs_emp, config_xs])
            if xs_bench.size or xs_emp.size
            else config_xs
        )
        x_grid = np.linspace(x_lo, x_hi, 200)
        mass_grid = spec.formula(x_grid, *mass_coeffs)
        ax.plot(
            _display_x(x_key, x_grid),
            cost_coeff * mass_grid,
            color=MODEL_COLORS[model_label],
            lw=MODEL_LINE_WIDTH,
            zorder=MODEL_LINE_ZORDER,
            label=f"2024 ({model_label})",
        )
        for name, x_val, marker in _config_markers(x_key):
            mass_val = spec.formula(x_val, *mass_coeffs)
            ax.scatter(
                [_display_x(x_key, x_val)],
                [cost_coeff * mass_val],
                marker=marker,
                s=CONFIG_MARKER_SIZE,
                facecolor=MODEL_COLORS[model_label],
                edgecolor="black",
                linewidth=CONFIG_MARKER_EDGE_LINEWIDTH,
                zorder=CONFIG_MARKER_ZORDER,
                label=name,
            )
        _scatter_benchmark(ax, _display_x(x_key, xs_bench), costs_bench, model_label)

    if xs_emp.size:
        ax.scatter(
            _display_x(x_key, xs_emp),
            costs_emp,
            c=EMPIRICAL_COLOR,
            alpha=EMPIRICAL_ALPHA,
            s=18,
            edgecolor=OVERLAY_EDGE_COLOR,
            linewidth=OVERLAY_EDGE_LINEWIDTH,
            zorder=EMPIRICAL_ZORDER,
            label="Empirical data",
        )

    ax.set_xlabel(driver_label)
    ax.set_ylabel("Cost (USD)")
    ax.grid(alpha=GRID_ALPHA)
    _format_thousands(ax)
    _set_title(ax, list(_cost_formula_text(label).items()))


def _plot_turbine_mass_panel(ax, empirical_df: pd.DataFrame, benchmark_df: pd.DataFrame) -> None:
    """No connecting line here either, for the same reason as
    :py:func:`_plot_turbine_cost_panel`: Turbine mass is a sum of three independently-driven
    formulas (rotor diameter, hub height, rated power), so a smooth curve against rated power
    alone would have to invent rotor diameter/hub height values in between the reference
    turbines rather than show anything actually computed. Shows each model's own value at every
    reference turbine instead (mass is shared, so there's exactly one point per turbine, not one
    per offshore type).
    """
    rotor_spec, tower_spec, nacelle_spec = (
        MASS_SPECS["Rotor"],
        MASS_SPECS["Tower"],
        MASS_SPECS["Nacelle"],
    )
    rotor_coeffs, tower_coeffs, nacelle_coeffs = (
        _mass_coeffs("Rotor"),
        _mass_coeffs("Tower"),
        _mass_coeffs("Nacelle"),
    )
    xs_emp, ys_emp = _turbine_empirical_points(empirical_df)

    for i, (name, config) in enumerate(DEFAULT_TURBINE_SPECS.items()):
        kw, rd, hh = config["rated_power_kw"], config["rotor_diameter"], config["hub_height"]
        mass = (
            rotor_spec.formula(rd, *rotor_coeffs)
            + tower_spec.formula(hh, *tower_coeffs)
            + nacelle_spec.formula(kw, *nacelle_coeffs)
        )
        ax.scatter(
            [_display_x("rated_power_kw", kw)],
            [mass],
            marker=CONFIG_MARKERS[i % len(CONFIG_MARKERS)],
            s=CONFIG_MARKER_SIZE,
            facecolor=MASS_COLOR,
            edgecolor="black",
            linewidth=CONFIG_MARKER_EDGE_LINEWIDTH,
            zorder=CONFIG_MARKER_ZORDER,
            label=name,
        )

    if xs_emp.size:
        ax.scatter(
            _display_x("rated_power_kw", xs_emp),
            ys_emp,
            c=EMPIRICAL_COLOR,
            alpha=EMPIRICAL_ALPHA,
            s=18,
            edgecolor=OVERLAY_EDGE_COLOR,
            linewidth=OVERLAY_EDGE_LINEWIDTH,
            zorder=EMPIRICAL_ZORDER,
            label="Empirical data",
        )
    for model_label in MODELS:
        xs_bench, masses_bench = _turbine_mass_benchmark_points(
            OFFSHORE_TYPE_FOR[model_label], benchmark_df
        )
        _scatter_benchmark(ax, _display_x("rated_power_kw", xs_bench), masses_bench, model_label)

    # Empty, invisible point purely to register a "2024 (mass, both)" legend swatch — a plain
    # dot, matching what's actually drawn (no line; see the docstring above), since the
    # config-marker scatter above only ever labels each point with its own turbine name.
    ax.scatter(
        [],
        [],
        marker="o",
        s=CONFIG_MARKER_SIZE,
        facecolor=MASS_COLOR,
        edgecolor="black",
        linewidth=CONFIG_MARKER_EDGE_LINEWIDTH,
        label="2024 (mass, both)",
    )

    ax.set_xlabel("Rated Power (MW)")
    ax.set_ylabel("Mass (kg)")
    ax.grid(alpha=GRID_ALPHA)
    _format_thousands(ax)


def _plot_turbine_cost_panel(ax, empirical_df: pd.DataFrame, benchmark_df: pd.DataFrame) -> None:
    """Turbine's cost panel has no line: unlike Rotor/Nacelle/Tower (each a direct closed-form
    fit), Turbine cost only ever existed as a linear interpolation across the reference
    turbines — not a real fitted relationship — so drawing it as a smooth curve would overstate
    how much is actually known between those points. Shows each model's own value at every
    reference turbine instead, plus the benchmark's and empirical CSV's own turbine-level cost
    figures.
    """
    rotor_spec, tower_spec, nacelle_spec = (
        MASS_SPECS["Rotor"],
        MASS_SPECS["Tower"],
        MASS_SPECS["Nacelle"],
    )
    for model_label, model_cls in MODELS.items():
        offshore_type = OFFSHORE_TYPE_FOR[model_label]
        rotor_coeffs = [_coeff(model_cls, p) for p in rotor_spec.params]
        tower_coeffs = [_coeff(model_cls, p) for p in tower_spec.params]
        nacelle_coeffs = [_coeff(model_cls, p) for p in nacelle_spec.params]
        rotor_cost_coeff = _coeff(model_cls, "rotor_mass_cost_coeff")
        tower_cost_coeff = _coeff(model_cls, "tower_mass_cost_coeff")
        nacelle_cost_coeff = _coeff(model_cls, "nacelle_mass_cost_coeff")

        for i, (name, config) in enumerate(DEFAULT_TURBINE_SPECS.items()):
            kw = config["rated_power_kw"]
            rotor_mass = rotor_spec.formula(config["rotor_diameter"], *rotor_coeffs)
            tower_mass = tower_spec.formula(config["hub_height"], *tower_coeffs)
            nacelle_mass = nacelle_spec.formula(kw, *nacelle_coeffs)
            cost = (
                rotor_cost_coeff * rotor_mass
                + tower_cost_coeff * tower_mass
                + nacelle_cost_coeff * nacelle_mass
            )
            ax.scatter(
                [_display_x("rated_power_kw", kw)],
                [cost],
                marker=CONFIG_MARKERS[i % len(CONFIG_MARKERS)],
                s=CONFIG_MARKER_SIZE,
                facecolor=MODEL_COLORS[model_label],
                edgecolor="black",
                linewidth=CONFIG_MARKER_EDGE_LINEWIDTH,
                zorder=CONFIG_MARKER_ZORDER,
                label=name,
            )

        xs_bench, costs_bench = _turbine_cost_benchmark_points(offshore_type, benchmark_df)
        _scatter_benchmark(ax, _display_x("rated_power_kw", xs_bench), costs_bench, model_label)

    xs_emp, costs_emp = _turbine_cost_empirical_points(empirical_df)
    if xs_emp.size:
        ax.scatter(
            _display_x("rated_power_kw", xs_emp),
            costs_emp,
            c=EMPIRICAL_COLOR,
            alpha=EMPIRICAL_ALPHA,
            s=18,
            edgecolor=OVERLAY_EDGE_COLOR,
            linewidth=OVERLAY_EDGE_LINEWIDTH,
            zorder=EMPIRICAL_ZORDER,
            label="Empirical data",
        )

    # Empty, invisible points purely to register a "2024 (Fixed-Bottom)"/"2024 (Floating)" legend
    # swatch — a plain dot, not a line, matching what's actually drawn (no line in this panel;
    # see the docstring above) — since the config-marker scatter above only ever labels each
    # point with its own turbine name, never the offshore type.
    for model_label in MODELS:
        ax.scatter(
            [],
            [],
            marker="o",
            s=CONFIG_MARKER_SIZE,
            facecolor=MODEL_COLORS[model_label],
            edgecolor="black",
            linewidth=CONFIG_MARKER_EDGE_LINEWIDTH,
            label=f"2024 ({model_label})",
        )

    ax.set_xlabel("Rated Power (MW)")
    ax.set_ylabel("Cost (USD)")
    ax.grid(alpha=GRID_ALPHA)
    _format_thousands(ax)


def generate_all_figures(
    output_dir: str | Path,
    empirical_csv: str | Path,
    benchmark_csv: str | Path,
) -> dict[str, Path]:
    """Generates one figure per component — Blade (mass only), Rotor/Nacelle/Tower/Turbine (mass
    and cost side by side) — and returns their paths keyed by component label.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    empirical_df = load_empirical_data(empirical_csv)
    benchmark_df = load_benchmark_data(benchmark_csv)

    paths: dict[str, Path] = {}

    fig, ax = plt.subplots(figsize=(6, 5.8))
    fig.suptitle("Blade", fontweight="bold")
    _plot_mass_panel(ax, "Blade", empirical_df, benchmark_df)
    nrows = _place_legend(fig, ax)
    fig.tight_layout(rect=(0, _legend_bottom_margin(nrows), 1, 1))
    path = output_dir / "blade.png"
    fig.savefig(path, dpi=150)
    plt.close(fig)
    paths["Blade"] = path

    for label in ("Rotor", "Nacelle", "Tower"):
        fig, axes = plt.subplots(1, 2, figsize=(11, 5.8))
        fig.suptitle(label, fontweight="bold")
        _plot_mass_panel(axes[0], label, empirical_df, benchmark_df)
        _plot_cost_panel(axes[1], label, empirical_df, benchmark_df)
        nrows = _place_legend(fig, axes[0], axes[1])
        fig.tight_layout(rect=(0, _legend_bottom_margin(nrows), 1, 1))
        path = output_dir / f"{label.lower()}.png"
        fig.savefig(path, dpi=150)
        plt.close(fig)
        paths[label] = path

    fig, axes = plt.subplots(1, 2, figsize=(11, 5.8))
    fig.suptitle("Turbine (Total) = Rotor + Nacelle + Tower", fontweight="bold")
    _plot_turbine_mass_panel(axes[0], empirical_df, benchmark_df)
    _plot_turbine_cost_panel(axes[1], empirical_df, benchmark_df)
    nrows = _place_legend(fig, axes[0], axes[1])
    fig.tight_layout(rect=(0, _legend_bottom_margin(nrows), 1, 1))
    path = output_dir / "turbine.png"
    fig.savefig(path, dpi=150)
    plt.close(fig)
    paths["Turbine"] = path

    return paths


def build_presentation(
    output_path: str | Path,
    figure_paths: dict[str, Path],
    title: str = "OSW Model Comparison",
) -> Path:
    """Assembles a widescreen slide deck: a title slide, then one slide per component figure —
    the same layout :py:func:`csm.tools.experimental.plotting.build_presentation` uses, minus its
    closing summary-report slide (there's no equivalent table for this model).

    Every figure is scaled to fit within the same content area regardless of how many panels it
    has (Blade's single-panel figure is narrower than the two-panel ones), so no picture
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

    prs.save(str(output_path))
    return output_path


def generate_comparison(
    output_dir: str | Path = "output/osw_comparison",
    empirical_csv: str | Path = "csm/tools/experimental/data/osw_csm_2026_data.csv",
    benchmark_csv: str | Path = "csm/tools/experimental/data/osw_benchmark_data.csv",
) -> dict[str, Path]:
    """Runs the full pipeline: per-component figures and a slide deck — the same entry point
    :py:func:`csm.tools.experimental.plotting.generate_comparison` provides for the land-based
    models.

    Returns:
        dict[str, Path]: Paths to the figures directory and the presentation.
    """
    output_dir = Path(output_dir).resolve()
    figures_dir = output_dir / "figures"
    figure_paths = generate_all_figures(figures_dir, empirical_csv, benchmark_csv)
    pptx_path = build_presentation(output_dir / "osw_comparison.pptx", figure_paths)
    return {"figures_dir": figures_dir, "presentation": pptx_path}


if __name__ == "__main__":
    paths = generate_comparison()
    for key, path in paths.items():
        print(f"{key}: {path}")  # noqa: T201
