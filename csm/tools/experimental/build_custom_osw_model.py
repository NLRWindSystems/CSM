"""Fits :py:class:`csm.models.base_osw_model.OSWBase`'s coefficients from a CSV of empirical
offshore wind turbine measurements and an offshore cost benchmark CSV, writing two generated
subclasses — ``csm/models/nlr2024_osw_fb.py`` (fixed-bottom) and ``csm/models/nlr2024_osw_fl.py``
(floating).

Unlike :py:mod:`csm.tools.experimental.build_custom_model` (the land-based equivalent), there is
no subcomponent decomposition here: the offshore data only supports four top-level assemblies
(Blade, Rotor, Tower, Nacelle), each fit directly against its own empirical rows, with Turbine
mass/cost simply the sum of Rotor + Nacelle + Tower. See :py:mod:`csm.models.base_osw_model` for
why.

Mass is fit once and shared between fixed-bottom and floating (the empirical CSV's `offshore
type` column is "not specified" for nearly all rows, so there's no real basis to split it — see
:py:func:`_fit_mass`). Cost is fit separately per offshore type from the benchmark CSV's
`offshore_type` column (see :py:func:`_fit_cost`), since that's exactly what it distinguishes.
"""

import sys
import textwrap
from pathlib import Path
from dataclasses import dataclass
from collections.abc import Callable

import numpy as np
import pandas as pd
from scipy.optimize import curve_fit


# Empirical CSV's `Component` column uses lowercase labels; OSWBase's own field-name convention
# capitalizes them for display. `x_from_row` reads the row's own independent variable (already
# unit-converted where needed — MW -> kW); `formula` is `OSWBase`'s exact calculate_*_mass shape,
# duplicated here (rather than introspected from the class) so this fit can run before any
# coefficients exist to introspect.
MASS_SPECS: dict[str, "MassSpec"] = {}


@dataclass
class MassSpec:
    """How to fit one of OSWBase's four mass formulas: `csv_component` selects rows from the
    empirical CSV, `x_column`/`x_transform` build the independent variable from it, `params`
    names the two coefficient fields (in `OSWBase.calculate_<label>_mass`'s own order) that
    `curve_fit(formula, ...)` solves for, and `driver_label` is just the display name for the fit
    report. `benchmark_x_column` is the *separate* column name the offshore benchmark CSV uses
    for this same quantity (its own schema doesn't match the empirical CSV's column names) — used
    only when the component also has a cost fit (see `COST_SPECS`); `None` for Blade, which has
    no cost benchmark at all.
    """

    csv_component: str
    x_column: str
    formula: Callable[..., float]
    params: tuple[str, str]
    x_transform: Callable[[float], float] | None = None
    driver_label: str = ""
    benchmark_x_column: str | None = None


MASS_SPECS = {
    "Blade": MassSpec(
        csv_component="blade",
        x_column="RD (m)",
        formula=lambda x, coeff, exp: coeff * (x / 2) ** exp,
        params=("blade_mass_coeff", "blade_mass_exp"),
        driver_label="Rotor Diameter (m)",
    ),
    "Rotor": MassSpec(
        csv_component="rotor",
        x_column="RD (m)",
        formula=lambda x, coeff, exp: coeff * x**exp,
        params=("rotor_mass_coeff", "rotor_mass_exp"),
        driver_label="Rotor Diameter (m)",
        benchmark_x_column="rotor_diameter",
    ),
    "Tower": MassSpec(
        csv_component="tower",
        x_column="hh (m)",
        formula=lambda x, coeff, exp: coeff * x**exp,
        params=("tower_mass_coeff", "tower_mass_exp"),
        driver_label="Hub Height (m)",
        benchmark_x_column="tower_height",
    ),
    "Nacelle": MassSpec(
        csv_component="nacelle",
        x_column="MW",
        x_transform=lambda mw: mw * 1000.0,
        formula=lambda x, coeff, intercept: coeff * x + intercept,
        params=("nacelle_mass_coeff", "nacelle_mass_intercept"),
        driver_label="Rated Power (kW)",
        benchmark_x_column="turbine_nameplate_capacity",
    ),
}

# Which mass field each cost-bearing component divides its benchmark cost by, and which
# MassSpec/x-column supplies the row's own independent variable for evaluating that mass formula
# at the benchmark row's own turbine size (rather than reusing some other reference turbine's).
COST_SPECS: dict[str, str] = {
    "Rotor": "rotor_mass_cost_coeff",
    "Nacelle": "nacelle_mass_cost_coeff",
    "Tower": "tower_mass_cost_coeff",
}

OFFSHORE_TYPES = ("fixed-bottom", "floating")


@dataclass
class FitResult:
    """One row of the fit report."""

    label: str
    kind: str  # "mass" | "cost" | "aggregate_check"
    offshore_type: str | None
    params: dict[str, float]
    r_squared: float | None
    n_points: int
    status: str


def _r_squared(y: np.ndarray, y_pred: np.ndarray) -> float:
    ss_res = np.sum((y - y_pred) ** 2)
    ss_tot = np.sum((y - np.mean(y)) ** 2)
    if ss_tot == 0:
        return 1.0 if ss_res == 0 else float("nan")
    return float(1.0 - ss_res / ss_tot)


def load_empirical_data(path: str | Path) -> pd.DataFrame:
    """Loads the offshore empirical CSV (`osw_csm_2026_data.csv`'s own format)."""
    return pd.read_csv(path)


def load_benchmark_data(path: str | Path) -> pd.DataFrame:
    """Loads the offshore benchmark CSV (`osw_benchmark_data.csv`'s own format), dropping the
    trailing unnamed/empty columns the source spreadsheet export leaves behind.
    """
    df = pd.read_csv(path)
    return df.loc[:, ~df.columns.str.startswith("Unnamed")]


def _fit_mass(
    label: str, spec: MassSpec, empirical_df: pd.DataFrame, benchmark_df: pd.DataFrame
) -> FitResult:
    """Fits one component's mass formula by least-squares (maximizing R²) against every
    empirical row *and* every benchmark row (its own `weight_kg` column, pooled in across both
    offshore types) with a usable mass value — shared between fixed-bottom and floating (see
    module docstring), so there's no reason to leave either type's real weight readings out of a
    fit that applies to both.
    """
    xs, ys = [], []
    rows = empirical_df[empirical_df["Component"] == spec.csv_component]
    for _, row in rows.iterrows():
        mass = pd.to_numeric(row.get("mass (kg)"), errors="coerce")
        x = pd.to_numeric(row.get(spec.x_column), errors="coerce")
        if pd.isna(mass) or pd.isna(x):
            continue
        xs.append(spec.x_transform(x) if spec.x_transform else x)
        ys.append(float(mass))

    if spec.benchmark_x_column is not None:
        bench_rows = benchmark_df[benchmark_df["component"] == spec.csv_component]
        for _, row in bench_rows.iterrows():
            mass = pd.to_numeric(row.get("weight_kg"), errors="coerce")
            x = pd.to_numeric(row.get(spec.benchmark_x_column), errors="coerce")
            if pd.isna(mass) or pd.isna(x):
                continue
            xs.append(spec.x_transform(x) if spec.x_transform else x)
            ys.append(float(mass))

    n_points = len(xs)
    defaults = dict.fromkeys(spec.params, 1.0)
    if n_points < 2:
        return FitResult(
            label, "mass", None, defaults, None, n_points, f"sample size too low (n={n_points})"
        )

    xs_arr, ys_arr = np.array(xs, dtype=float), np.array(ys, dtype=float)
    try:
        popt, _ = curve_fit(spec.formula, xs_arr, ys_arr, p0=[1.0, 1.0], maxfev=20000)
    except RuntimeError:
        return FitResult(label, "mass", None, defaults, None, n_points, "fit failed, inherited")

    fitted = dict(zip(spec.params, popt, strict=True))
    r2 = _r_squared(ys_arr, spec.formula(xs_arr, *popt))
    return FitResult(label, "mass", None, fitted, r2, n_points, "fit")


def _empirical_cost_points(
    mass_spec: MassSpec,
    mass_params: dict[str, float],
    offshore_type: str,
    empirical_df: pd.DataFrame,
) -> tuple[list[float], list[float]]:
    """(predicted mass, cost) pairs for `mass_spec`'s own empirical CSV rows with a usable cost
    value. A row counts as usable for `offshore_type` if it's an exact match *or* the row's own
    `offshore type` is "not specified" — true of nearly every empirical row, so treating it as
    applicable to either type (rather than excluded from both) is what actually lets this real
    data inform the fit at all.
    """
    rows = empirical_df[
        (empirical_df["Component"] == mass_spec.csv_component)
        & empirical_df["offshore type"].isin([offshore_type, "not specified"])
    ]
    masses, costs = [], []
    for _, row in rows.iterrows():
        cost = pd.to_numeric(row.get("cost ($)"), errors="coerce")
        x = pd.to_numeric(row.get(mass_spec.x_column), errors="coerce")
        if pd.isna(cost) or pd.isna(x):
            continue
        x = mass_spec.x_transform(x) if mass_spec.x_transform else x
        predicted_mass = mass_spec.formula(x, *(mass_params[p] for p in mass_spec.params))
        if predicted_mass <= 0:
            continue
        masses.append(predicted_mass)
        costs.append(float(cost))
    return masses, costs


def _fit_cost(
    label: str,
    field_name: str,
    mass_spec: MassSpec,
    mass_params: dict[str, float],
    offshore_type: str,
    benchmark_df: pd.DataFrame,
    empirical_df: pd.DataFrame,
) -> FitResult:
    """Fits one component's cost-per-kilogram rate, for one offshore type, pooling the benchmark
    CSV's own rows with any of the empirical CSV's own cost rows for the same component (see
    :py:func:`_empirical_cost_points`) — a weighted least-squares ratio (`cost = coeff * mass`,
    maximizing R²) when there are 2+ usable rows total, or the single row's own ratio taken
    exactly when there's only one (the same "a real measurement is a real measurement, not a
    sample to average" treatment used throughout
    :py:mod:`csm.tools.experimental.build_custom_model`).

    Each row's predicted mass comes from evaluating `mass_spec`'s already-fitted formula at that
    *same row's own* rotor diameter/hub height/rated power — never a different reference
    turbine's — since both CSVs give geometry alongside each cost figure directly.
    """
    csv_component = mass_spec.csv_component
    bench_rows = benchmark_df[
        (benchmark_df["component"] == csv_component)
        & (benchmark_df["offshore_type"] == offshore_type)
    ]

    masses, costs = [], []
    for _, row in bench_rows.iterrows():
        capacity_mw = pd.to_numeric(row.get("turbine_nameplate_capacity"), errors="coerce")
        rate = pd.to_numeric(row.get("value_$/MW"), errors="coerce")
        x = pd.to_numeric(row.get(mass_spec.benchmark_x_column), errors="coerce")
        if pd.isna(capacity_mw) or pd.isna(rate) or pd.isna(x):
            continue
        x = mass_spec.x_transform(x) if mass_spec.x_transform else x
        predicted_mass = mass_spec.formula(x, *(mass_params[p] for p in mass_spec.params))
        if predicted_mass <= 0:
            continue
        masses.append(predicted_mass)
        costs.append(float(rate) * float(capacity_mw))
    n_benchmark = len(masses)

    emp_masses, emp_costs = _empirical_cost_points(
        mass_spec, mass_params, offshore_type, empirical_df
    )
    masses += emp_masses
    costs += emp_costs
    n_empirical = len(emp_masses)

    n_points = len(masses)
    if n_points == 0:
        return FitResult(label, "cost", offshore_type, {field_name: 1.0}, None, 0, "no data")

    masses_arr, costs_arr = np.array(masses, dtype=float), np.array(costs, dtype=float)
    coeff = float(np.sum(costs_arr * masses_arr) / np.sum(masses_arr**2))
    source_note = f" ({n_benchmark} benchmark + {n_empirical} empirical)" if n_empirical else ""
    if n_points == 1:
        return FitResult(
            label,
            "cost",
            offshore_type,
            {field_name: coeff},
            None,
            1,
            f"fit (1 point — exact){source_note}",
        )
    r2 = _r_squared(costs_arr, coeff * masses_arr)
    return FitResult(
        label,
        "cost",
        offshore_type,
        {field_name: coeff},
        r2,
        n_points,
        f"fit (n={n_points}){source_note}",
    )


def _predicted_turbine_cost(
    rd: float,
    hh: float,
    capacity_kw: float,
    mass_params: dict[str, dict[str, float]],
    cost_params: dict[str, dict[str, float]],
) -> float:
    """Rotor + Nacelle + Tower cost at a specific rotor diameter/hub height/rated power, using
    the already-fitted mass and cost coefficients — the same sum `OSWBase.calculate_turbine_cost`
    computes, evaluated directly here since the aggregate check runs before any model class with
    these coefficients actually exists.
    """
    rotor_mass = MASS_SPECS["Rotor"].formula(
        rd, *(mass_params["Rotor"][p] for p in MASS_SPECS["Rotor"].params)
    )
    tower_mass = MASS_SPECS["Tower"].formula(
        hh, *(mass_params["Tower"][p] for p in MASS_SPECS["Tower"].params)
    )
    nacelle_mass = MASS_SPECS["Nacelle"].formula(
        capacity_kw, *(mass_params["Nacelle"][p] for p in MASS_SPECS["Nacelle"].params)
    )
    return (
        cost_params["Rotor"]["rotor_mass_cost_coeff"] * rotor_mass
        + cost_params["Nacelle"]["nacelle_mass_cost_coeff"] * nacelle_mass
        + cost_params["Tower"]["tower_mass_cost_coeff"] * tower_mass
    )


def _turbine_aggregate_check(
    mass_params: dict[str, dict[str, float]],
    cost_params: dict[str, dict[str, float]],
    offshore_type: str,
    benchmark_df: pd.DataFrame,
    empirical_df: pd.DataFrame,
) -> FitResult:
    """Validates (does not fit) the fully-assembled Turbine total — Rotor + Nacelle + Tower mass
    and cost — against both the benchmark's and the empirical CSV's own `component == "turbine"`
    rows for `offshore_type` (the empirical CSV's own "not specified" rows count for either type,
    same as :py:func:`_empirical_cost_points`), which give real turbine-level cost figures
    independent of the per-assembly rows used to fit those assemblies individually.
    """
    predicted, observed = [], []
    bench_rows = benchmark_df[
        (benchmark_df["component"] == "turbine") & (benchmark_df["offshore_type"] == offshore_type)
    ]
    for _, row in bench_rows.iterrows():
        capacity_mw = pd.to_numeric(row.get("turbine_nameplate_capacity"), errors="coerce")
        rate = pd.to_numeric(row.get("value_$/MW"), errors="coerce")
        rd = pd.to_numeric(row.get("rotor_diameter"), errors="coerce")
        hh = pd.to_numeric(row.get("tower_height"), errors="coerce")
        if pd.isna(capacity_mw) or pd.isna(rate) or pd.isna(rd) or pd.isna(hh):
            continue
        predicted.append(
            _predicted_turbine_cost(rd, hh, capacity_mw * 1000.0, mass_params, cost_params)
        )
        observed.append(float(rate) * float(capacity_mw))

    emp_rows = empirical_df[
        (empirical_df["Component"] == "turbine")
        & empirical_df["offshore type"].isin([offshore_type, "not specified"])
    ]
    for _, row in emp_rows.iterrows():
        cost = pd.to_numeric(row.get("cost ($)"), errors="coerce")
        rd = pd.to_numeric(row.get("RD (m)"), errors="coerce")
        hh = pd.to_numeric(row.get("hh (m)"), errors="coerce")
        mw = pd.to_numeric(row.get("MW"), errors="coerce")
        if pd.isna(cost) or pd.isna(rd) or pd.isna(hh) or pd.isna(mw):
            continue
        predicted.append(_predicted_turbine_cost(rd, hh, mw * 1000.0, mass_params, cost_params))
        observed.append(float(cost))

    n_points = len(predicted)
    if n_points == 0:
        return FitResult("Turbine", "aggregate_check", offshore_type, {}, None, 0, "no data")
    r2 = _r_squared(np.array(observed), np.array(predicted)) if n_points > 1 else None
    return FitResult(
        "Turbine", "aggregate_check", offshore_type, {}, r2, n_points, "validation only (not fit)"
    )


def render_fit_report(report: list[FitResult], model_name: str) -> str:
    """Renders `report` as the plain-text table printed to the console and saved alongside the
    written models.
    """
    header = f"Fit report — {model_name}"
    lines = [header, "=" * len(header), ""]
    lines.append(
        f"{'Component':<12}{'Kind':<16}{'Type':<14}{'Status':<28}{'R²':>8}{'n':>6}  Params"
    )
    lines.append("-" * 110)
    for r in report:
        r2_str = f"{r.r_squared:.4f}" if r.r_squared is not None else "—"
        params_str = ", ".join(f"{k}={v:.6g}" for k, v in r.params.items())
        offshore_type = r.offshore_type or ""
        lines.append(
            f"{r.label:<12}{r.kind:<16}{offshore_type:<14}{r.status:<28}{r2_str:>8}"
            f"{r.n_points:>6}  {params_str}"
        )
    return "\n".join(lines)


def _render_model_source(class_name: str, docstring: str, overrides: dict[str, float]) -> str:
    """Renders an `OSWBase` subclass with `overrides` applied — a plain `.reuse(default=...)`
    line per coefficient, the same generated-subclass pattern
    :py:mod:`csm.tools.experimental.build_custom_model` uses for the land-based models.
    """
    override_lines = "\n".join(
        f"    {name} = base.{name}.reuse(default={float(value)!r})"
        for name, value in overrides.items()
    )
    header_text = (
        "Auto-generated by build_custom_osw_model.py — coefficients fit from empirical and "
        "benchmark offshore wind data."
    )
    footer_text = (
        "Do not hand-edit this file; rerun the fitting script instead so the model and its fit "
        "report stay in sync."
    )
    class_docstring_text = (
        "Coefficients fit from empirical and benchmark offshore wind data. See the accompanying "
        "fit report for what was fit and from how many data points."
    )
    module_docstring = "\n".join(
        [
            f'"""{textwrap.fill(header_text, width=97)}',
            "",
            *textwrap.wrap(docstring, width=100),
            "",
            *textwrap.wrap(footer_text, width=100),
            '"""',
        ]
    )
    class_docstring_lines = textwrap.wrap(class_docstring_text, width=90)
    class_docstring_body = [
        '    """' + class_docstring_lines[0],
        *(f"    {line}" for line in class_docstring_lines[1:]),
        '    """',
    ]
    class_docstring = "\n".join(class_docstring_body)
    return (
        f"{module_docstring}\n\n"
        f"from attrs import define, fields\n\n"
        f"from csm.models.base_osw_model import OSWBase\n\n\n"
        f"base = fields(OSWBase)\n\n\n"
        f"@define\n"
        f"class {class_name}(OSWBase):\n"
        f"{class_docstring}\n\n"
        f"{override_lines}\n"
    )


def build_custom_osw_model(
    empirical_csv: str | Path,
    benchmark_csv: str | Path,
    output_dir: str | Path = "csm/models",
) -> list[FitResult]:
    """Fits mass (shared) and cost (per offshore type) coefficients and writes
    `nlr2024_osw_fb.py`/`nlr2024_osw_fl.py` to `output_dir`. Returns the full fit report.
    """
    empirical_df = load_empirical_data(empirical_csv)
    benchmark_df = load_benchmark_data(benchmark_csv)

    report: list[FitResult] = []
    mass_params: dict[str, dict[str, float]] = {}
    for label, spec in MASS_SPECS.items():
        result = _fit_mass(label, spec, empirical_df, benchmark_df)
        mass_params[label] = result.params
        report.append(result)
    mass_overrides = {
        name: value
        for label, spec in MASS_SPECS.items()
        if report_status_ok(next(r for r in report if r.label == label and r.kind == "mass"))
        for name, value in mass_params[label].items()
    }

    cost_params: dict[str, dict[str, dict[str, float]]] = {t: {} for t in OFFSHORE_TYPES}
    cost_overrides: dict[str, dict[str, float]] = {t: {} for t in OFFSHORE_TYPES}
    for offshore_type in OFFSHORE_TYPES:
        for label, field_name in COST_SPECS.items():
            result = _fit_cost(
                label,
                field_name,
                MASS_SPECS[label],
                mass_params[label],
                offshore_type,
                benchmark_df,
                empirical_df,
            )
            cost_params[offshore_type][label] = result.params
            report.append(result)
            if result.status not in ("no data",):
                cost_overrides[offshore_type].update(result.params)
        report.append(
            _turbine_aggregate_check(
                mass_params, cost_params[offshore_type], offshore_type, benchmark_df, empirical_df
            )
        )

    output_dir = Path(output_dir)
    class_names = {"fixed-bottom": "OffshoreFB2024NLR", "floating": "OffshoreFL2024NLR"}
    module_names = {"fixed-bottom": "nlr2024_osw_fb", "floating": "nlr2024_osw_fl"}
    for offshore_type in OFFSHORE_TYPES:
        class_name = class_names[offshore_type]
        docstring = (
            f"Fit from {Path(empirical_csv).name} (mass, shared with the other offshore type) "
            f"and {Path(benchmark_csv).name} (cost, {offshore_type} only)."
        )
        source = _render_model_source(
            class_name, docstring, {**mass_overrides, **cost_overrides[offshore_type]}
        )
        module_path = output_dir / f"{module_names[offshore_type]}.py"
        module_path.write_text(source, encoding="utf-8")

    return report


def report_status_ok(result: FitResult) -> bool:
    """Whether `result`'s params are trustworthy enough to override the base model's defaults
    with, rather than leaving `OSWBase`'s own (untuned) placeholder values in place.
    """
    return result.status == "fit"


if __name__ == "__main__":
    fit_report = build_custom_osw_model(
        empirical_csv="csm/tools/experimental/data/osw_csm_2026_data.csv",
        benchmark_csv="csm/tools/experimental/data/osw_benchmark_data.csv",
    )
    print(render_fit_report(fit_report, "osw_2024"))  # noqa: T201
    print("\nWritten to: csm/models/nlr2024_osw_fb.py, csm/models/nlr2024_osw_fl.py")  # noqa: T201
    sys.exit(0)
