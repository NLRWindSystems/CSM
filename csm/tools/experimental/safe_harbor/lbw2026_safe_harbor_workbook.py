"""Builds the safe-harbor sweep workbook: raw sweep data on one tab, and a second tab comparing
it against the 2023 published Manufactured Product Component (MPC) percentages — Treasury's
domestic-content safe harbor reference (see :py:mod:`csm.tools.experimental.
lbw2026_safe_harbor_sweep` for what the sweep itself covers and why).

Sheet "Raw Data" is :py:func:`csm.tools.experimental.lbw2026_safe_harbor_sweep.
generate_safe_harbor_sweep`'s own table, written as-is.

Sheet "Comparison" has two linked pieces:

- A comparison table (APC / MPC / 2023 value with its published +/- range / this sweep's own
  mean, min, max), in the same row layout as the 2023 report's own table — the 2023 values are
  hardcoded reference numbers (they're an external published source, not something this workbook
  computes), but every "CSM 2026" column is a live ``AVERAGEIFS``/``MINIFS``/``MAXIFS`` formula
  reading the Raw Data sheet directly, so re-running the sweep with different specs and
  re-pasting that sheet updates the comparison automatically.
- A two-bar 100%-stacked horizontal chart — one bar per data source ("2026 Model Update" from
  this sweep, "Safe Harbor Table (24/25)" from the 2023 report) — built from a small linked
  "chart data" block below the table, with error bars per segment: this sweep's own min/max range
  for the 2026 Model Update bar, and the 2023 report's own published +/- range for the Safe
  Harbor Table bar, via ``ErrorBars(errValType="cust")`` referencing that block's own formula
  cells. Each segment also gets a centered, one-decimal percentage data label, and the value
  axis's own tick numbers are formatted as percentages too.

Note: the 2023 report has no "Production" MPC of its own (its 5 categories only cover
manufactured components, not the wind turbine's own production cost) — it's included as a sixth
segment for legend/axis parity with the 2026 Update bar, with the Safe Harbor Table bar's own
value fixed at 0 for it.
"""

from pathlib import Path

import pandas as pd
from openpyxl import Workbook
from openpyxl.chart import Series, BarChart, Reference
from openpyxl.utils import get_column_letter
from openpyxl.styles import Font, PatternFill
from openpyxl.chart.label import DataLabelList
from openpyxl.chart.shapes import GraphicalProperties
from openpyxl.chart.error_bar import ErrorBars
from openpyxl.chart.data_source import NumRef, NumDataSource

from csm.tools.experimental.safe_harbor.lbw2026_safe_harbor_sweep import (
    generate_safe_harbor_sweep,
)


# The 2023 published reference table this sweep is compared against (see the module docstring) —
# (APC, MPC, value %, +range, -range). MPC labels match the report's own wording; each maps to
# one of Raw Data's own MPC labels via _REPORT_TO_RAW_MPC below. "Production" has no real 2023
# figure (see module docstring) — its 0/0/0 row exists only so the comparison table and chart
# both carry all six segments.
REPORT_2023: list[tuple[str, str, float, float, float]] = [
    ("Rotor", "Blades", 31.2, 3.5, -4.5),
    ("", "Rotor hub", 9.9, 2.1, -0.5),
    ("Nacelle", "Nacelle (excluding power converter)", 47.5, 4.5, -2.5),
    ("", "Power converter", 8.9, 1.1, -2.1),
    ("Tower", "Wind tower flanges", 1.6, 0.6, -0.5),
    ("Wind Turbine", "Production", 0.0, 0.0, 0.0),
]

# Report MPC label -> the (APC, MPC) pair generate_safe_harbor_sweep's own Raw Data rows use.
_REPORT_TO_RAW_MPC: dict[str, tuple[str, str]] = {
    "Blades": ("Wind Turbine", "Blade"),
    "Rotor hub": ("Wind Turbine", "Rotor Hub"),
    "Nacelle (excluding power converter)": ("Wind Turbine", "Nacelle"),
    "Power converter": ("Wind Turbine", "Power Converter"),
    "Wind tower flanges": ("Wind Tower Flange", "Total"),
    "Production": ("Wind Turbine", "Production"),
}

# Chart segment order, short display label, and fill color, left-to-right — matches the
# comparison chart's own legend order/colors.
_CHART_SEGMENTS: list[tuple[str, str, str]] = [
    ("Nacelle (excluding power converter)", "Nacelle", "1F6B7A"),
    ("Blades", "Blades", "E8834E"),
    ("Rotor hub", "Hub", "2E7D32"),
    ("Power converter", "Power Converter", "4FC3E8"),
    ("Wind tower flanges", "Tower Flanges", "9C4FA6"),
    ("Production", "Production", "8BC34A"),
]

# The chart's two bars, in the order they're written to the data block — first row plots at the
# bottom of a horizontal bar chart by default, so "Safe Harbor Table" first puts "2026 Model
# Update" on top, matching the reference figure. These exact strings become each bar's own
# category-axis label, at its base.
_CHART_ROWS: list[str] = ["Safe Harbor Table (24/25)", "2026 Model Update"]

HEADER_FONT = Font(bold=True)
SECTION_FILL = PatternFill("solid", fgColor="D9E1F2")
PERCENT_FORMAT = "0.0"
# Data-label / axis number format: the underlying values are already on a 0-100 scale (not
# 0-1), so a literal appended "%" — not Excel's built-in percent format, which would multiply by
# 100 again — is what actually reads correctly.
LABEL_PERCENT_FORMAT = '0.0"%"'
AXIS_PERCENT_FORMAT = '0"%"'


def _write_raw_data_sheet(wb: Workbook, sweep: pd.DataFrame) -> None:
    ws = wb.active
    ws.title = "Raw Data"
    ws.append(list(sweep.columns))
    for cell in ws[1]:
        cell.font = HEADER_FONT
    for row in sweep.itertuples(index=False):
        ws.append(list(row))
    for col_idx, column in enumerate(sweep.columns, start=1):
        ws.column_dimensions[get_column_letter(col_idx)].width = max(12, len(column) + 2)


def _mpc_formula(kind: str, mpc_label: str) -> str:
    """An `AVERAGEIFS`/`MINIFS`/`MAXIFS` formula (per `kind`) reading Raw Data's own Cost (%)
    column for `mpc_label`, filtered on both APC and MPC (the "Total" tower-flange row shares its
    MPC label with nothing else, but filtering on both columns keeps every formula the same
    shape).
    """
    apc, mpc = _REPORT_TO_RAW_MPC[mpc_label]
    if kind == "mean":
        return (
            f"=AVERAGEIFS('Raw Data'!$I:$I,'Raw Data'!$E:$E,\"{apc}\",'Raw Data'!$F:$F,\"{mpc}\")"
        )
    if kind == "min":
        return f"=MINIFS('Raw Data'!$I:$I,'Raw Data'!$E:$E,\"{apc}\",'Raw Data'!$F:$F,\"{mpc}\")"
    return f"=MAXIFS('Raw Data'!$I:$I,'Raw Data'!$E:$E,\"{apc}\",'Raw Data'!$F:$F,\"{mpc}\")"


def _write_comparison_table(ws) -> dict[str, int]:
    """Writes the APC/MPC/2023/CSM-2026 comparison table starting at row 1.

    Returns:
        dict[str, int]: MPC label -> the row its data lives on, so the chart-data block below can
            reference each row's 2023/Mean/Min/Max cells directly.
    """
    ws["A1"] = (
        "Relative Value of Manufactured Product Components — CSM 2026 vs. 2023 Published Values"
    )
    ws["A1"].font = Font(bold=True, size=13)
    ws.merge_cells("A1:H1")

    headers = [
        "APC",
        "Manufactured Product Component",
        "2023 Reported (%)",
        "2023 (+%)",
        "2023 (-%)",
        "CSM 2026 Mean (%)",
        "CSM 2026 Min (%)",
        "CSM 2026 Max (%)",
    ]
    ws.append([])
    ws.append(headers)
    header_row = ws.max_row
    for cell in ws[header_row]:
        cell.font = HEADER_FONT
        cell.fill = SECTION_FILL

    ws.append(["Wind Turbine CapEx"])
    section_row = ws.max_row
    ws.cell(section_row, 1).font = HEADER_FONT
    ws.merge_cells(start_row=section_row, start_column=1, end_row=section_row, end_column=8)

    mpc_rows: dict[str, int] = {}
    for apc, mpc_label, value, plus, minus in REPORT_2023:
        ws.append([apc, mpc_label, value, plus, minus])
        row = ws.max_row
        ws.cell(row, 6, _mpc_formula("mean", mpc_label))
        ws.cell(row, 7, _mpc_formula("min", mpc_label))
        ws.cell(row, 8, _mpc_formula("max", mpc_label))
        for col in (3, 4, 5, 6, 7, 8):
            ws.cell(row, col).number_format = PERCENT_FORMAT
        mpc_rows[mpc_label] = row

    ws.append([])
    ws.append(
        [
            'Note: the 2023 report has no "Production" MPC of its own (turbine production cost '
            "isn't one of its 5 manufactured-component categories) — its row above is included "
            "only for chart/axis parity with the 2026 Update bar, fixed at 0."
        ]
    )
    ws.cell(ws.max_row, 1).font = Font(italic=True, size=9)
    ws.merge_cells(start_row=ws.max_row, start_column=1, end_row=ws.max_row, end_column=8)

    ws.column_dimensions["A"].width = 10
    ws.column_dimensions["B"].width = 34
    for col in "CDEFGH":
        ws.column_dimensions[col].width = 16
    return mpc_rows


def _write_chart_data_block(ws, mpc_rows: dict[str, int], start_row: int) -> int:
    """Writes the small linked block the chart's series/error-bars read from: one column per
    segment, one row per bar ("Safe Harbor Table (2024/25)", "2026 Update"), plus a matching pair
    of Error+/Error- row-blocks beneath — every cell a formula referencing that segment's own row
    in the comparison table above.

    Returns:
        int: The header row (segment names) — the chart reads its series titles from here and
            its three 2-row value/error blocks immediately below.
    """
    ws.cell(start_row, 1, "Chart data (linked to the table above)")
    ws.cell(start_row, 1).font = Font(italic=True, size=9)

    header_row = start_row + 1
    for col_offset, (_mpc_label, display_name, _color) in enumerate(_CHART_SEGMENTS, start=2):
        ws.cell(header_row, col_offset, display_name)
        ws.cell(header_row, col_offset).font = HEADER_FONT

    values_row0 = header_row + 1  # "Safe Harbor Table (2024/25)"
    values_row1 = values_row0 + 1  # "2026 Update"
    plus_row0 = values_row1 + 1
    plus_row1 = plus_row0 + 1
    minus_row0 = plus_row1 + 1
    minus_row1 = minus_row0 + 1

    for offset, label in enumerate((values_row0, values_row1)):
        ws.cell(label, 1, _CHART_ROWS[offset])
    ws.cell(plus_row0, 1, f"{_CHART_ROWS[0]} Error +")
    ws.cell(plus_row1, 1, f"{_CHART_ROWS[1]} Error +")
    ws.cell(minus_row0, 1, f"{_CHART_ROWS[0]} Error -")
    ws.cell(minus_row1, 1, f"{_CHART_ROWS[1]} Error -")

    for col_offset, (mpc_label, _display_name, _color) in enumerate(_CHART_SEGMENTS, start=2):
        table_row = mpc_rows[mpc_label]
        # Safe Harbor Table (2024/25): its own reported value and published +/- range.
        ws.cell(values_row0, col_offset, f"=C{table_row}")
        ws.cell(plus_row0, col_offset, f"=D{table_row}")
        ws.cell(minus_row0, col_offset, f"=-E{table_row}")
        # 2026 Update: this sweep's mean, with min/max-derived error amounts.
        ws.cell(values_row1, col_offset, f"=F{table_row}")
        ws.cell(plus_row1, col_offset, f"=H{table_row}-F{table_row}")
        ws.cell(minus_row1, col_offset, f"=F{table_row}-G{table_row}")
        for row in (values_row0, values_row1, plus_row0, plus_row1, minus_row0, minus_row1):
            ws.cell(row, col_offset).number_format = PERCENT_FORMAT

    return header_row


def _add_chart(ws, header_row: int) -> None:
    """Adds the two-bar 100%-stacked horizontal chart, one series per :py:data:`_CHART_SEGMENTS`
    entry, with custom asymmetric error bars sourced from the four rows below the value rows (see
    :py:func:`_write_chart_data_block`).
    """
    values_row0 = header_row + 1
    values_row1 = values_row0 + 1
    plus_row0 = values_row1 + 1
    plus_row1 = plus_row0 + 1
    minus_row0 = plus_row1 + 1
    minus_row1 = minus_row0 + 1

    chart = BarChart()
    chart.type = "bar"
    chart.grouping = "stacked"
    chart.overlap = 100
    chart.title = "Average Contribution to Total Manufactured Products Cost"
    chart.y_axis.title = None
    chart.x_axis.title = "Contribution to Total Manufactured Product Cost (%)"
    chart.height = 8
    chart.width = 24

    # Category axis (the bars' own base labels — "Safe Harbor Table (24/25)" / "2026 Model
    # Update") stays visible next to its bars; value axis ticks read as percentages ("0%" ...
    # "100%") rather than the raw 0-100 numbers.
    chart.y_axis.delete = False
    chart.y_axis.tickLblPos = "nextTo"
    chart.x_axis.number_format = AXIS_PERCENT_FORMAT

    categories = Reference(ws, min_col=1, min_row=values_row0, max_row=values_row1)
    for col_offset, (_mpc_label, display_name, color) in enumerate(_CHART_SEGMENTS, start=2):
        col = get_column_letter(col_offset)
        values = Reference(
            ws, min_col=col_offset, max_col=col_offset, min_row=values_row0, max_row=values_row1
        )
        series = Series(values, title_from_data=False, title=display_name)
        series.graphicalProperties = GraphicalProperties(solidFill=color)
        # One-decimal percentage labels, centered inside each stacked segment.
        series.dLbls = DataLabelList(
            showVal=True,
            showLegendKey=False,
            showCatName=False,
            showSerName=False,
            showPercent=False,
            showBubbleSize=False,
            dLblPos="ctr",
            numFmt=LABEL_PERCENT_FORMAT,
        )
        series.errBars = ErrorBars(
            errDir="x",
            errBarType="both",
            errValType="cust",
            noEndCap=False,
            plus=NumDataSource(NumRef(f"'Comparison'!${col}${plus_row0}:${col}${plus_row1}")),
            minus=NumDataSource(NumRef(f"'Comparison'!${col}${minus_row0}:${col}${minus_row1}")),
        )
        chart.series.append(series)
    chart.set_categories(categories)

    ws.add_chart(chart, f"A{minus_row1 + 3}")


def build_safe_harbor_workbook(
    output_path: str | Path = "output/safe_harbor_tables/safe_harbor_sweep.xlsx",
) -> Path:
    """Runs the sweep and writes the full two-tab workbook (see module docstring).

    Returns:
        Path: The saved .xlsx path.
    """
    sweep = generate_safe_harbor_sweep()

    wb = Workbook()
    _write_raw_data_sheet(wb, sweep)

    ws = wb.create_sheet("Comparison")
    mpc_rows = _write_comparison_table(ws)
    header_row = _write_chart_data_block(ws, mpc_rows, start_row=ws.max_row + 2)
    _add_chart(ws, header_row)

    output_path = Path(output_path).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(str(output_path))
    return output_path


if __name__ == "__main__":
    path = build_safe_harbor_workbook()
    print(f"Written to: {path}")  # noqa: T201
