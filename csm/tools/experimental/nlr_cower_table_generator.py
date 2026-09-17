"""Generates NLR Cost of Wind Energy Review (COWER)-style CapEx breakdown tables.

Produces one Excel workbook per turbine configuration (see :py:data:`DEFAULT_TURBINE_SPECS`
below — deliberately its own copy, not imported from csm/plotting.py, so this script runs as an
independent entry point), formatted like NLR's COWE Review capex tables: an indented, hierarchical
"Parameter" column ("Turbine" > "Rotor/Nacelle/Tower module" > their own sub-assemblies) using
sentence case throughout (only each row's own first letter capitalized, matching the reference
table's own style), with every value in $/kW (cost divided by that configuration's
``rated_power_kw``). Unlike the single-value reference table, each row here carries one column
per CSM model (:py:data:`DEFAULT_MODELS`), so every workbook doubles as a
2015-vs-2020-vs-... comparison for that one configuration.

The line-item -> CSM cost field mapping (:py:data:`COWER_LINE_ITEMS`) is fixed by spec, not by
reusing any of CSM's own internal WoodMac-benchmark groupings in csm/plotting.py (e.g.
``WM_CATEGORY_MAPPING``'s "Structure" bucket, which lumps Yaw System in with Bedplate/Platform &
Mainframe — CSM's own component names, capitalized as csm/plotting.py itself defines them) —
those group components differently than this table's "Nacelle structural/drivetrain/electrical/
yaw assembly" split calls for, so every row here sums CSM's per-component cost attributes
directly instead.

Note: NLR's own COWE Review table has one more row than this one, "Total CapEx" (Turbine +
balance-of-system/soft costs), sitting *above* "Turbine". CSM doesn't model BOS, so there is
nothing to put in that gap — this table starts at "Turbine" (rotor + nacelle + tower module) and
stops there, rather than showing a "Total CapEx" row that would just silently equal Turbine.
"""

from typing import NamedTuple
from pathlib import Path

from openpyxl import Workbook
from openpyxl.utils import get_column_letter
from openpyxl.styles import Font, Side, Border, Alignment, PatternFill

from csm.models.nlr2015 import Land2015NLR
from csm.models.nlr2020 import Land2020NLR
from csm.models.nlr2021 import Land2021NLR
from csm.models.nlr2026 import Land2026NLR


# Deliberately duplicated from csm/plotting.py rather than imported from it — this script is
# meant to run as its own independent entry point, not to depend on (or be broken by unrelated
# changes to) plotting.py's own module state. Keep these in sync by hand if either changes.
DEFAULT_MODELS: dict[str, type] = {
    "2015": Land2015NLR,
    "2020": Land2020NLR,
    "2021": Land2021NLR,
    "2026": Land2026NLR,
}

# Example turbine configurations (same ones csm/plotting.py compares). `turbine_class` and
# `blade_has_carbon` are not part of the ATB specs and are assumed (Class I, no carbon) via
# `to_model_kwargs`.
DEFAULT_TURBINE_SPECS: dict[str, dict] = {
    "ATB T3 (3.3MW)": {
        "turbine_rating_MW": 3.3,
        "rotor_diameter": 148.0,
        "hub_height": 100.0,
        "tip_speed_max": 90.0,
        "num_bearings": 2,
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
    "2011 COWER (1.5MW)": {
        "turbine_rating_MW": 1.5,
        "rotor_diameter": 82.5,
        "hub_height": 80.0,
        "tip_speed_max": 80.0,
        "num_bearings": 1,
        "num_blades": 3,
        "rotor_efficiency_max": 0.9,
        "BOS_cost": 0.0,
    },
    "2015 COWER (2.0MW)": {
        "turbine_rating_MW": 2.0,
        "rotor_diameter": 102.0,
        "hub_height": 82.1,
        "tip_speed_max": 80.0,
        "num_bearings": 1,
        "num_blades": 3,
        "rotor_efficiency_max": 0.9,
        "BOS_cost": 0.0,
    },
    "2020 COWER (2.8MW)": {
        "turbine_rating_MW": 2.8,
        "rotor_diameter": 125.0,
        "hub_height": 90.0,
        "tip_speed_max": 80.0,
        "num_bearings": 1,
        "num_blades": 3,
        "rotor_efficiency_max": 0.9,
        "BOS_cost": 0.0,
    },
}


def to_model_kwargs(spec: dict) -> dict:
    """Converts a raw turbine specification into ``CSMBase`` subclass constructor kwargs.

    Args:
        spec (dict): Turbine specification with keys ``turbine_rating_MW``, ``rotor_diameter``,
            ``hub_height``, ``tip_speed_max``, ``num_bearings``, ``num_blades``, and
            ``rotor_efficiency_max``. Any ``BOS_cost`` key is ignored since it is not a model
            input.

    Returns:
        dict: Keyword arguments accepted by every model in :py:data:`DEFAULT_MODELS`.
    """
    return {
        "rated_power_kw": round(spec["turbine_rating_MW"] * 1000),
        "rotor_diameter": float(spec["rotor_diameter"]),
        "tower_length": float(spec["hub_height"]),
        "max_tip_speed": float(spec["tip_speed_max"]),
        "num_bearings": int(spec["num_bearings"]),
        "num_blades": int(spec["num_blades"]),
        "efficiency_max": float(spec["rotor_efficiency_max"]),
        "turbine_class": int(spec.get("turbine_class", 1)),
        "blade_has_carbon": bool(spec.get("blade_has_carbon", False)),
    }


class LineItem(NamedTuple):
    """One row of the COWER-style table.

    Either `cost_attrs` (a leaf row, summing real CSM cost attributes) or `subtotal_of` (a
    rollup row, summing other line items' *already-computed* $/kW values by label) is set, never
    both — a rollup is always exactly consistent with its own children instead of being
    independently recomputed from cost attributes of its own.

    Each `cost_attrs` entry is `(attr_name, multiplier_key)`, where `multiplier_key` is a
    `to_model_kwargs(...)` entry that attribute alone gets multiplied by before summing, or None
    for no multiplier. A per-attribute (not per-row) multiplier is necessary: CSM's own
    `calculate_nacelle_cost`/`calculate_rotor_cost` multiply exactly two leaf costs this way —
    `blade_cost` by `num_blades` and `bearing_cost` by `num_bearings` (see base_model.py) — since
    each field prices a *single* blade/bearing, not the turbine's full count of them. Blades'
    row has only `blade_cost`, but Main Bearing's `bearing_cost` is bundled with five unmultiplied
    attributes inside the "Drivetrain assembly" row, which is exactly why the multiplier has to
    live on the attribute itself rather than the row — a row-level multiplier would have wrongly
    scaled its neighbors too.
    """

    label: str
    indent: int
    cost_attrs: tuple[tuple[str, str | None], ...] = ()
    subtotal_of: tuple[str, ...] = ()
    bold: bool = False


# The mapping given for this table: which CSM per-component cost fields (see
# csm.plotting.ALL_COMPONENTS) roll up into each NLR COWE Review line item.
COWER_LINE_ITEMS: list[LineItem] = [
    LineItem(
        "Turbine", 0, subtotal_of=("Rotor module", "Nacelle module", "Tower module"), bold=True
    ),
    LineItem(
        "Rotor module", 1, subtotal_of=("Blades", "Pitch assembly", "Hub assembly"), bold=True
    ),
    LineItem("Blades", 2, cost_attrs=(("blade_cost", "num_blades"),)),
    LineItem("Pitch assembly", 2, cost_attrs=(("pitch_system_cost", None),)),
    LineItem("Hub assembly", 2, cost_attrs=(("hub_cost", None), ("spinner_cost", None))),
    LineItem(
        "Nacelle module",
        1,
        subtotal_of=(
            "Nacelle structural assembly",
            "Drivetrain assembly",
            "Nacelle electrical assembly",
            "Yaw assembly",
        ),
        bold=True,
    ),
    LineItem(
        "Nacelle structural assembly",
        2,
        cost_attrs=(
            ("bedplate_cost", None),
            ("nacelle_cover_cost", None),
            ("platform_mainframe_cost", None),
        ),
    ),
    LineItem(
        "Drivetrain assembly",
        2,
        cost_attrs=(
            ("low_speed_shaft_cost", None),
            ("bearing_cost", "num_bearings"),
            ("gearbox_cost", None),
            ("brake_cost", None),
            ("high_speed_shaft_cost", None),
            ("hydraulic_cooling_cost", None),
        ),
    ),
    LineItem(
        "Nacelle electrical assembly",
        2,
        cost_attrs=(
            ("generator_cost", None),
            ("transformer_cost", None),
            ("converter_cost", None),
            ("controls_cost", None),
            ("electrical_connection_cost", None),
        ),
    ),
    LineItem("Yaw assembly", 2, cost_attrs=(("yaw_system_cost", None),)),
    LineItem("Tower module", 1, cost_attrs=(("tower_cost", None),), bold=True),
]

_ITEMS_BY_LABEL: dict[str, LineItem] = {item.label: item for item in COWER_LINE_ITEMS}

HEADER_FILL = PatternFill("solid", fgColor="000000")
HEADER_FONT = Font(color="FFFFFF", bold=True)
ACCENT_FILL = PatternFill("solid", fgColor="2E74B5")
THIN_SIDE = Side(style="thin", color="BFBFBF")
THIN_BORDER = Border(left=THIN_SIDE, right=THIN_SIDE, top=THIN_SIDE, bottom=THIN_SIDE)
VALUE_NUMBER_FORMAT = "#,##0"


def _row_value_per_kw(
    label: str, model, rated_power_kw: float, model_kwargs: dict, cache: dict[str, float]
) -> float:
    """The $/kW value of line item `label` for one already-run `model` instance, memoized in
    `cache` so a rollup row (e.g. "Total CapEx") only walks its children's values once each,
    regardless of how many ancestor rollups also depend on them.
    """
    if label in cache:
        return cache[label]
    item = _ITEMS_BY_LABEL[label]
    if item.subtotal_of:
        value = sum(
            _row_value_per_kw(child, model, rated_power_kw, model_kwargs, cache)
            for child in item.subtotal_of
        )
    else:
        raw_cost = sum(
            (getattr(model, attr, 0.0) or 0.0)
            * (model_kwargs[multiplier_key] if multiplier_key is not None else 1)
            for attr, multiplier_key in item.cost_attrs
        )
        value = raw_cost / rated_power_kw
    cache[label] = value
    return value


def _compute_config_values(
    spec: dict, models: dict[str, type]
) -> dict[str, dict[str, float | None]]:
    """Runs every model against one turbine configuration and computes every line item's $/kW
    value for each.

    Returns:
        dict[str, dict[str, float | None]]: label -> model name -> $/kW value, or None for a
            model/configuration combination that raised while running (a model rejecting an
            infeasible combination of inputs, say) rather than letting the whole workbook fail.
    """
    model_kwargs = to_model_kwargs(spec)
    rated_power_kw = model_kwargs["rated_power_kw"]
    values: dict[str, dict[str, float | None]] = {item.label: {} for item in COWER_LINE_ITEMS}
    for model_name, model_cls in models.items():
        try:
            model = model_cls(**model_kwargs)
            model.run()
        except (ValueError, AttributeError, TypeError):
            for item in COWER_LINE_ITEMS:
                values[item.label][model_name] = None
            continue
        cache: dict[str, float] = {}
        for item in COWER_LINE_ITEMS:
            values[item.label][model_name] = _row_value_per_kw(
                item.label, model, rated_power_kw, model_kwargs, cache
            )
    return values


def _slugify_filename(name: str) -> str:
    keep = "".join(c if c.isalnum() or c in "()._-" else "_" for c in name)
    while "__" in keep:
        keep = keep.replace("__", "_")
    return keep.strip("_")


def _write_workbook(
    config_name: str,
    model_names: list[str],
    values: dict[str, dict[str, float | None]],
    output_path: Path,
) -> None:
    """Writes one config's table (see module docstring for the layout) to `output_path`."""
    wb = Workbook()
    ws = wb.active
    ws.title = "CapEx Breakdown"

    n_cols = 1 + len(model_names)
    ws.cell(row=1, column=1, value="Parameter")
    for col, model_name in enumerate(model_names, start=2):
        ws.cell(row=1, column=col, value=f"{model_name} ($/kW)")
    for col in range(1, n_cols + 1):
        cell = ws.cell(row=1, column=col)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = THIN_BORDER

    for col in range(1, n_cols + 1):
        ws.cell(row=2, column=col).fill = ACCENT_FILL
    ws.row_dimensions[2].height = 6

    for row_offset, item in enumerate(COWER_LINE_ITEMS):
        row = row_offset + 3
        label_cell = ws.cell(row=row, column=1, value=item.label)
        label_cell.alignment = Alignment(indent=item.indent, horizontal="left", vertical="center")
        label_cell.font = Font(bold=item.bold)
        label_cell.border = THIN_BORDER
        for col, model_name in enumerate(model_names, start=2):
            value = values[item.label][model_name]
            value_cell = ws.cell(row=row, column=col, value=value if value is not None else "n/a")
            if value is not None:
                value_cell.number_format = VALUE_NUMBER_FORMAT
            value_cell.font = Font(bold=item.bold)
            value_cell.alignment = Alignment(horizontal="right", vertical="center")
            value_cell.border = THIN_BORDER

    ws.column_dimensions["A"].width = 34
    for col in range(2, n_cols + 1):
        ws.column_dimensions[get_column_letter(col)].width = 16
    ws.freeze_panes = "B3"
    ws.print_title_rows = "1:1"

    wb.properties.title = f"NLR COWE Review-style CapEx breakdown — {config_name}"

    output_path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(str(output_path))


def generate_cower_tables(
    output_dir: str | Path = "output/cower_tables",
    models: dict[str, type] | None = None,
    configs: dict[str, dict] | None = None,
) -> dict[str, Path]:
    """Generates one NLR COWER-style CapEx breakdown workbook per turbine configuration.

    Args:
        output_dir (str | Path, optional): Directory the workbooks are saved into (created if
            missing). Defaults to "output/cower_tables".
        models (dict[str, type] | None, optional): Mapping of model name to a ``CSMBase``
            subclass — becomes one $/kW column per row. Defaults to :py:data:`DEFAULT_MODELS`.
        configs (dict[str, dict] | None, optional): Mapping of configuration name to a raw
            turbine spec (see :py:func:`to_model_kwargs`) — becomes one workbook per entry.
            Defaults to :py:data:`DEFAULT_TURBINE_SPECS`.

    Returns:
        dict[str, Path]: Mapping of configuration name to its saved workbook path.
    """
    models = models or DEFAULT_MODELS
    configs = configs or DEFAULT_TURBINE_SPECS
    output_dir = Path(output_dir).resolve()

    model_names = list(models)
    paths: dict[str, Path] = {}
    for config_name, spec in configs.items():
        values = _compute_config_values(spec, models)
        path = output_dir / f"cower_{_slugify_filename(config_name)}.xlsx"
        _write_workbook(config_name, model_names, values, path)
        paths[config_name] = path
    return paths


if __name__ == "__main__":
    for config_name, path in generate_cower_tables().items():
        print(f"{config_name}: {path}")  # noqa: T201 — CLI entry point, not a debug leftover
