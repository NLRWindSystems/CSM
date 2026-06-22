"""
Turbine component cost/mass post-processor
=============================================

Reads the wide-format "turbine_config_csm_sweep_*.csv" export (one column
per turbine model x cost-model-variant) and produces a clean component-level
table (mass, cost, IRS rollup component, IRS cost %) for a single turbine /
model-variant chosen by the user. Automatically saves the output to a CSV.
"""

import csv
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Row-label -> CSV row index map (0-indexed, matching the raw file's rows)
# ---------------------------------------------------------------------------
ROW = {
    "turbine_cost": 12,
    "rotor_cost": 13,
    "blade_cost": 14,
    "hub_cost": 15,
    "pitch_system_cost": 16,
    "nose_cone_cost": 17,
    "nacelle_cost": 18,
    "low_speed_shaft_cost": 19,
    "main_bearing_cost": 20,
    "gearbox_cost": 21,
    "braking_system_cost": 22,
    "generator_cost": 23,
    "transformer_power_electronics_cost": 24,
    "yaw_system_cost": 25,
    "bedplate_cost": 26,
    "railing_platform_cost": 27,
    "crane_cost": 28,
    "hvac_cost": 29,
    "nacelle_cover_cost": 30,
    "controls_cost": 31,
    "electrical_connection_cost": 32,
    "tower_cost": 33,
    "rotor_mass": 35,
    "blade_mass": 36,
    "hub_mass": 37,
    "pitch_system_mass": 38,
    "nose_cone_mass": 39,
    "nacelle_mass": 40,
    "low_speed_shaft_mass": 41,
    "main_bearing_mass": 42,
    "gearbox_mass": 43,
    "braking_system_mass": 44,
    "generator_mass": 45,
    "transformer_power_electronics_mass": 46,
    "yaw_system_mass": 47,
    "bedplate_mass": 48,
    "railing_platform_mass": 49,
    "crane_mass": 50,
    "hvac_mass": 51,
    "nacelle_cover_mass": 52,
    "tower_mass": 53,
    "turbine_rating_MW": 55,
}

MODEL_VARIANTS = ["Empirical2020", "Empirical2024Onshore", "Prioritized_Hybrid"]

# US CPI-U for January of respective years
CPI_JAN_2020 = 257.971
CPI_JAN_2024 = 308.417
CPI_JAN_2026 = 325.252

# Inflation factors targeting Jan 2026 dollars
INFLATION_FACTORS = {
    "Empirical2020": CPI_JAN_2026 / CPI_JAN_2020,        # ~1.2608
    "Empirical2024Onshore": CPI_JAN_2026 / CPI_JAN_2024, # ~1.0546
    "Prioritized_Hybrid": CPI_JAN_2026 / CPI_JAN_2024,                            # Assumes base 2026 dollars
}

# Assumptions per the project costing methodology
POWER_CONVERTER_USD_PER_KW = 50.0
TOWER_FLANGE_FRACTION = 0.06


def load_csv(path):
    """Read the raw CSV and return (turbine_names_row, model_variant_row, data_rows)."""
    with open(path, newline="", encoding="utf-8-sig") as f:
        rows = list(csv.reader(f))
    return rows[0], rows[1], rows


def discover_turbines(turbine_row):
    """Map each turbine name to its list of (column_index, model_variant) pairs."""
    turbines = {}
    for col_idx in range(1, len(turbine_row)):
        name = turbine_row[col_idx].strip()
        if name:
            turbines.setdefault(name, []).append(col_idx)
    return turbines


def get_value(rows, row_key, col_idx, default=None):
    """Fetch a numeric value from the CSV; returns `default` if blank/missing."""
    raw = rows[ROW[row_key]][col_idx]
    if raw is None or str(raw).strip() == "":
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def find_column(rows, turbine_row, model_row, turbine_name, model_variant):
    """Locate the column index for a given turbine name + model variant."""
    for col_idx in range(1, len(turbine_row)):
        if turbine_row[col_idx].strip() == turbine_name and model_row[col_idx].strip() == model_variant:
            return col_idx
    return None


def get_value_with_fallback(rows, row_key, turbine_cols, preferred_idx, model_row):
    """Fall back to other columns for the SAME turbine if the preferred variant cell is blank.
       Returns a tuple of (value, source_variant).
    """
    value = get_value(rows, row_key, preferred_idx)
    if value is not None:
        return value, model_row[preferred_idx].strip()
        
    for col_idx in turbine_cols:
        value = get_value(rows, row_key, col_idx)
        if value is not None:
            return value, model_row[col_idx].strip()
            
    return None, None


def apply_inflation(value, source_variant, is_cost):
    """Applies the appropriate inflation multiplier if the metric is a cost."""
    if value is None or not is_cost or source_variant not in INFLATION_FACTORS:
        return value
    return value * INFLATION_FACTORS[source_variant]


def build_component_table(rows, turbine_row, model_row, turbine_name, model_variant):
    """Build the list of component dicts for the requested turbine + model variant."""
    turbines = discover_turbines(turbine_row)
    if turbine_name not in turbines:
        raise ValueError(f"Turbine '{turbine_name}' not found.")
    
    turbine_cols = turbines[turbine_name]
    col_idx = find_column(rows, turbine_row, model_row, turbine_name, model_variant)
    
    if col_idx is None:
        raise ValueError(f"Model variant '{model_variant}' not found for turbine '{turbine_name}'.")

    def val(row_key):
        # Fetch the value and track which model variant column it came from
        raw_val, source_variant = get_value_with_fallback(rows, row_key, turbine_cols, col_idx, model_row)
        
        # Only inflate if the row name denotes a cost
        is_cost = "cost" in row_key.lower()
        return apply_inflation(raw_val, source_variant, is_cost)

    # --- core pulled values -------------------------------------------------
    turbine_cost = val("turbine_cost")
    rotor_cost = val("rotor_cost")
    nacelle_cost = val("nacelle_cost")
    tower_cost = val("tower_cost")
    tower_mass = val("tower_mass")
    rating_mw = val("turbine_rating_MW")

    # --- derived values not present in the raw CSV -------------------------
    rating_kw = rating_mw * 1000.0 if rating_mw is not None else None
    power_converter_cost = POWER_CONVERTER_USD_PER_KW * rating_kw if rating_kw is not None else None
    tower_flange_cost = tower_cost * TOWER_FLANGE_FRACTION if tower_cost is not None else None
    tower_flange_mass = tower_mass * TOWER_FLANGE_FRACTION if tower_mass is not None else None

    def pct(component_cost):
        if component_cost is None or not turbine_cost:
            return None
        return component_cost / turbine_cost * 100.0

    # --- assemble the output table ------------------------------------------
    table = []

    # Get single blade cost to calculate the 3x percentage properly
    single_blade_cost = val("blade_cost")
    three_blade_cost_pct = pct(single_blade_cost * 3) if single_blade_cost is not None else None

    table.append({
        "Component": "Blade (1x)",
        "Mass (kg)": val("blade_mass"),
        "Cost ($)": single_blade_cost,
        "IRS Component": "Blades (3x)",
        "IRS Cost %": "31.2%",
    })
    table.append({
        "Component": "Hub (Incl. Pitch System)",
        "Mass (kg)": val("hub_mass"),
        "Cost ($)": val("hub_cost"),
        #"Mass (kg)": val("hub_mass") + val("pitch_system_mass"),
        #"Cost ($)": val("hub_cost") + val("pitch_system_cost"),
        "IRS Component": "Rotor hub",
        "IRS Cost %": "9.9%",
    })
    table.append({
        "Component": "Nose cone",
        "Mass (kg)": val("nose_cone_mass"),
        "Cost ($)": val("nose_cone_cost"),
        "IRS Component": None,
        "IRS Cost %": None,
    })
    table.append({
        "Component": "Main shaft",
        "Mass (kg)": val("low_speed_shaft_mass"),
        "Cost ($)": val("low_speed_shaft_cost"),
        "IRS Component": "Nacelle",
        "IRS Cost %": "47.5%",
    })
    table.append({
        "Component": "Main bearings (2)",
        "Mass (kg)": val("main_bearing_mass"),
        "Cost ($)": val("main_bearing_cost"),
        "IRS Component": None,
        "IRS Cost %": None,
    })
    table.append({
        "Component": "Gearbox",
        "Mass (kg)": val("gearbox_mass"),
        "Cost ($)": val("gearbox_cost"),
        "IRS Component": None,
        "IRS Cost %": None,
    })
    table.append({
        "Component": "Braking system",
        "Mass (kg)": val("braking_system_mass"),
        "Cost ($)": val("braking_system_cost"),
        "IRS Component": None,
        "IRS Cost %": None,
    })
    table.append({
        "Component": "Generator",
        "Mass (kg)": val("generator_mass"),
        "Cost ($)": val("generator_cost"),
        "IRS Component": None,
        "IRS Cost %": None,
    })
    table.append({
        "Component": "Bedplate",
        "Mass (kg)": val("bedplate_mass"),
        "Cost ($)": val("bedplate_cost"),
        "IRS Component": None,
        "IRS Cost %": None,
    })
    table.append({
        "Component": "Yaw system",
        "Mass (kg)": val("yaw_system_mass"),
        "Cost ($)": val("yaw_system_cost"),
        "IRS Component": None,
        "IRS Cost %": None,
    })
    table.append({
        "Component": "Transformer",
        "Mass (kg)": val("transformer_power_electronics_mass"),
        "Cost ($)": val("transformer_power_electronics_cost"),
        "IRS Component": None,
        "IRS Cost %": None,
    })
    table.append({
        "Component": "Electrical cabling",
        "Mass (kg)": None,
        "Cost ($)": val("electrical_connection_cost"),
        "IRS Component": None,
        "IRS Cost %": None,
    })
    table.append({
        "Component": "Controls",
        "Mass (kg)": None,
        "Cost ($)": val("controls_cost"),
        "IRS Component": None,
        "IRS Cost %": None,
    })
    table.append({
        "Component": "Cooling system",
        "Mass (kg)": val("hvac_mass"),
        "Cost ($)": val("hvac_cost"),
        "IRS Component": None,
        "IRS Cost %": None,
    })
    table.append({
        "Component": "Nacelle cover",
        "Mass (kg)": val("nacelle_cover_mass"),
        "Cost ($)": val("nacelle_cover_cost"),
        "IRS Component": None,
        "IRS Cost %": None,
    })
    table.append({
        "Component": "Railing platform",
        "Mass (kg)": val("railing_platform_mass"),
        "Cost ($)": val("railing_platform_cost"),
        "IRS Component": None,
        "IRS Cost %": None,
    })
    table.append({
        "Component": "Crane",
        "Mass (kg)": val("crane_mass"),
        "Cost ($)": val("crane_cost"),
        "IRS Component": None,
        "IRS Cost %": None,
    })
    table.append({
        "Component": "Power converter",
        "Mass (kg)": None,
        "Cost ($)": power_converter_cost,
        "IRS Component": "Power converter",
        "IRS Cost %": "8.9%",
    })
    table.append({
        "Component": "Tower",
        "Mass (kg)": tower_mass,
        "Cost ($)": tower_cost,
        "IRS Component": "Iron/steel",
        "IRS Cost %": "N/A",
    })
    table.append({
        "Component": "Of which flanges",
        "Mass (kg)": tower_flange_mass,
        "Cost ($)": tower_flange_cost,
        "IRS Component": "Tower flanges",
        "IRS Cost %": "1.6%",
    })

    meta = {
        "turbine_name": turbine_name,
        "model_variant": model_variant,
        "turbine_rating_MW": rating_mw,
        "turbine_cost": turbine_cost,
        "rotor_cost": rotor_cost,
        "nacelle_cost": nacelle_cost,
        "tower_cost": tower_cost,
    }
    return table, meta


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------
def fmt_mass(value):
    if value is None: return ""
    return f"{value:,.0f}"

def fmt_cost(value):
    if value is None: return ""
    return f"${value:,.0f}"

def fmt_pct(value, irs_component):
    if value is None: 
        return ""
    return str(value)

def write_csv(table, out_path):
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Component", "Mass (kg)", "Cost ($)", "IRS Component", "IRS Cost %"])
        for row in table:
            writer.writerow([
                row["Component"],
                fmt_mass(row["Mass (kg)"]),
                fmt_cost(row["Cost ($)"]),
                row["IRS Component"] or "",
                fmt_pct(row["IRS Cost %"], row["IRS Component"]),
            ])

# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------
def main():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("csv_path", type=str, help="Path to the input CSV file.")
    parser.add_argument("--turbine", type=str, default=None)
    parser.add_argument("--variant", type=str, default="Prioritized_Hybrid", choices=MODEL_VARIANTS)
    parser.add_argument("--out", type=str, default=None, help="Optional specific output path.")
    args = parser.parse_args()

    if not args.turbine:
        parser.error("--turbine is required.")

    turbine_row, model_row, rows = load_csv(args.csv_path)
    
    try:
        table, meta = build_component_table(rows, turbine_row, model_row, args.turbine, args.variant)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    out_path = args.out
    if not out_path:
        safe_name = args.turbine.replace(" ", "_").replace("(", "").replace(")", "").replace(".", "_")
        out_path = f"{safe_name}_{args.variant}.csv"

    write_csv(table, out_path)
    print(f"Success! Saved data to: {out_path}")

if __name__ == "__main__":
    main()