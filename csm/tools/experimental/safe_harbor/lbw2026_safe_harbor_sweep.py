"""Sweeps the LBW 2026 model's safe-harbor-style IRS MPC breakdown (see
:py:meth:`csm.models.base_model.CSMBase.irs_mpc_breakdown`) across every (model, hub height)
combination in :py:data:`SAFE_HARBOR_SPECS` — real onshore turbine models and hub heights pulled
from a fleet listing (see below for the exact source rows and what was excluded), plus "GE3.6-154"
added by hand (not in the source listing).

Every model's rated power and rotor diameter come directly from its own name (GE/Vestas/Nordex
turbine model numbers already encode both, e.g. "V150-4.5" = 150 m rotor, 4.5 MW; "N155/4500" =
155 m rotor, 4500 kW). Hub heights come from the source listing's own rows for that model — rows
whose hub height was blank are skipped entirely (there's no way to build a model input from an
unspecified hub height), and rows with no model name and 0 MW (an "unidentified turbines" bucket
in the source data) are dropped outright.

Excluded from the source listing: SG-11.0-200-DD, SG-14-222-DD, and Haliade-X (offshore turbines
have no place in an LBW comparison). "GE3.6-154" was added with no hub height of its own in the
source data, so it borrows GE3.8-154's 98 m hub height — the closest real data point (same 154 m
rotor diameter).

Every configuration shares the same assumptions, per this sweep's own request: 90 m/s max tip
speed, 0.9 rotor efficiency, a single main bearing, and no onboard crane (see
:py:mod:`csm.tools.experimental.lbw2026_safe_harbor_tables` for the ``has_crane`` fix this relies
on — before it, ``has_crane=False`` had no effect).

The per-MPC "Mass (kg)" column isn't something ``irs_mpc_breakdown`` itself returns, so it's
computed here in exact lockstep with that method's own cost mapping (num_blades times blade_mass
for Blade, hub_system_mass for Rotor Hub, nacelle_mass minus converter_mass for Nacelle,
converter_mass for Power Converter — Production and the tower flange rows have no mass concept,
since they're user-supplied costs, not model-computed components).
"""

import pandas as pd

from csm.models.nlr2026 import Land2026NLR
from csm.tools.experimental.safe_harbor.lbw2026_safe_harbor_tables import (
    HAS_CRANE,
    NUM_BEARINGS,
    _derived_irs_costs,
)


# Shared assumptions across every configuration in this sweep.
TIP_SPEED_MAX = 90.0
ROTOR_EFFICIENCY_MAX = 0.9

# Model -> (rated power (MW), rotor diameter (m), hub heights (m) — one sweep point each).
# Source: a fleet listing of onshore turbine models, hub height, turbine count, and total MW per
# hub height. Rows with no recorded hub height, and the source's own "unidentified turbines"
# bucket rows (blank model, 0 MW), are omitted — see the module docstring.
SAFE_HARBOR_SPECS: dict[str, dict] = {
    "GE2.3-116": {"rated_power_MW": 2.3, "rotor_diameter": 116.0, "hub_heights": [90.0]},
    "GE2.5-116": {"rated_power_MW": 2.5, "rotor_diameter": 116.0, "hub_heights": [90.0]},
    "GE2.52-116": {"rated_power_MW": 2.52, "rotor_diameter": 116.0, "hub_heights": [90.0]},
    "GE2.72-116": {"rated_power_MW": 2.72, "rotor_diameter": 116.0, "hub_heights": [90.0]},
    "GE2.8-127": {"rated_power_MW": 2.8, "rotor_diameter": 127.0, "hub_heights": [89.0, 114.0]},
    "GE2.82-127": {
        "rated_power_MW": 2.82,
        "rotor_diameter": 127.0,
        "hub_heights": [88.0, 88.6, 89.0, 114.0],
    },
    "GE3.4-140": {"rated_power_MW": 3.4, "rotor_diameter": 140.0, "hub_heights": [98.0, 117.0]},
    # Added by hand — not in the source listing. Hub height borrowed from GE3.8-154 (same 154 m
    # rotor diameter), per this sweep's own request.
    "GE3.6-154": {"rated_power_MW": 3.6, "rotor_diameter": 154.0, "hub_heights": [98.0]},
    "GE3.8-154": {"rated_power_MW": 3.8, "rotor_diameter": 154.0, "hub_heights": [98.0]},
    "GE6.1-158": {"rated_power_MW": 6.1, "rotor_diameter": 158.0, "hub_heights": [101.0, 117.0]},
    "N155/4500": {"rated_power_MW": 4.5, "rotor_diameter": 155.0, "hub_heights": [108.0]},
    "SG-3.1-129": {"rated_power_MW": 3.1, "rotor_diameter": 129.0, "hub_heights": [83.0, 87.0]},
    "V100-2.0": {"rated_power_MW": 2.0, "rotor_diameter": 100.0, "hub_heights": [95.0]},
    "V117-4.0": {"rated_power_MW": 4.0, "rotor_diameter": 117.0, "hub_heights": [92.0]},
    "V136-3.45": {"rated_power_MW": 3.45, "rotor_diameter": 136.0, "hub_heights": [105.0]},
    "V136-3.6": {"rated_power_MW": 3.6, "rotor_diameter": 136.0, "hub_heights": [105.0]},
    "V150-4.0": {"rated_power_MW": 4.0, "rotor_diameter": 150.0, "hub_heights": [120.0]},
    "V150-4.2": {"rated_power_MW": 4.2, "rotor_diameter": 150.0, "hub_heights": [105.0]},
    "V150-4.3": {"rated_power_MW": 4.3, "rotor_diameter": 150.0, "hub_heights": [105.0]},
    "V150-4.5": {
        "rated_power_MW": 4.5,
        "rotor_diameter": 150.0,
        "hub_heights": [105.0, 120.0, 136.0],
    },
    "V162-6.0": {"rated_power_MW": 6.0, "rotor_diameter": 162.0, "hub_heights": [105.0, 119.0]},
    "V163-4.5": {
        "rated_power_MW": 4.5,
        "rotor_diameter": 163.0,
        "hub_heights": [98.0, 112.0, 113.0],
    },
}

# Each irs_mpc_breakdown (APC, MPC) row's mass, computed the same way irs_mpc_breakdown computes
# that row's own cost — None where there's no mass concept (Production and the tower flange rows
# are user-supplied costs, not model-computed components).
_MASS_BY_APC_MPC = {
    ("Wind Turbine", "Blade"): lambda m: m.num_blades * m.blade_mass,
    ("Wind Turbine", "Rotor Hub"): lambda m: m.hub_system_mass,
    ("Wind Turbine", "Nacelle"): lambda m: m.nacelle_mass - m.converter_mass,
    ("Wind Turbine", "Power Converter"): lambda m: m.converter_mass,
}


def _model_kwargs(rated_power_mw: float, rotor_diameter: float, hub_height: float) -> dict:
    """``Land2026NLR`` constructor kwargs for one (rated power, rotor diameter, hub height) point,
    with every other input fixed to this sweep's shared assumptions.
    """
    return {
        "rated_power_kw": round(rated_power_mw * 1000),
        "rotor_diameter": rotor_diameter,
        "tower_length": hub_height,
        "max_tip_speed": TIP_SPEED_MAX,
        "efficiency_max": ROTOR_EFFICIENCY_MAX,
        "num_bearings": NUM_BEARINGS,
        "num_blades": 3,
        "has_crane": HAS_CRANE,
    }


def _sweep_point_rows(model_name: str, hub_height: float, spec: dict) -> list[dict]:
    """The full (Mass, Cost, Cost %) breakdown for one (model, hub height) point, one row per
    ``irs_mpc_breakdown`` (APC, MPC) pair.
    """
    kwargs = _model_kwargs(spec["rated_power_MW"], spec["rotor_diameter"], hub_height)
    model = Land2026NLR(**kwargs)
    model.run()

    derived_costs = _derived_irs_costs(model)
    breakdown = model.irs_mpc_breakdown(**derived_costs, with_category=True)

    def _row(apc: str, mpc: str, mass, cost: float, pct: float) -> dict:
        return {
            "Model": model_name,
            "Hub Height (m)": hub_height,
            "Rated Power (MW)": spec["rated_power_MW"],
            "Rotor Diameter (m)": spec["rotor_diameter"],
            "APC": apc,
            "MPC": mpc,
            "Mass (kg)": mass,
            "Cost (2026$)": cost,
            "Cost (%)": pct,
        }

    rows = []
    tower_flange_cost_total = 0.0
    tower_flange_pct_total = 0.0
    for (apc, mpc), record in breakdown.iterrows():
        # Excludes "Total" and the two not-a-real-MPC placeholder rows (Tower, Steel or iron
        # products in foundation) — all three share MPC == "-" (see irs_mpc_breakdown's own
        # steel_ix/total construction), unlike every real MPC row.
        if mpc == "-":
            continue
        mass_fn = _MASS_BY_APC_MPC.get((apc, mpc))
        rows.append(
            _row(apc, mpc, mass_fn(model) if mass_fn else None, record["cost"], record["Value"])
        )
        if apc == "Wind Tower Flange":
            tower_flange_cost_total += record["cost"]
            tower_flange_pct_total += record["Value"]

    # A combined Material+Production row — not one of irs_mpc_breakdown's own (APC, MPC) pairs,
    # but the published safe-harbor reference this sweep gets compared against reports "Wind tower
    # flanges" as a single line, so this saves every comparison formula from having to add the two
    # rows back together itself.
    rows.append(
        _row("Wind Tower Flange", "Total", None, tower_flange_cost_total, tower_flange_pct_total)
    )
    return rows


def generate_safe_harbor_sweep(specs: dict[str, dict] = SAFE_HARBOR_SPECS) -> pd.DataFrame:
    """Runs :py:func:`_sweep_point_rows` for every (model, hub height) combination in `specs`.

    Returns:
        pd.DataFrame: One row per (model, hub height, MPC) — see the module docstring for column
            definitions. Saving this to a file is
            :py:mod:`csm.tools.experimental.lbw2026_safe_harbor_workbook`'s job, not this
            function's — it also needs this same table to build its comparison-sheet formulas.
    """
    rows: list[dict] = []
    for model_name, spec in specs.items():
        for hub_height in spec["hub_heights"]:
            rows.extend(_sweep_point_rows(model_name, hub_height, spec))
    return pd.DataFrame(rows)


if __name__ == "__main__":
    pd.set_option("display.width", 160)
    pd.set_option("display.max_rows", 300)
    sweep = generate_safe_harbor_sweep()
    print(sweep)  # noqa: T201 — CLI entry point
    print(f"\n{len(sweep)} rows across {sweep['Model'].nunique()} models")  # noqa: T201
