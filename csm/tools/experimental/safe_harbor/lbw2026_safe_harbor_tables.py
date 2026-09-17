"""Computes IRS safe-harbor-style domestic content tables (see
:py:meth:`csm.models.base_model.CSMBase.irs_mpc_breakdown`) for two reference turbine
configurations — "ATB T3 (3.3MW)" and "V150-4.5" (both already defined in
:py:mod:`csm.tools.experimental.nlr_cower_table_generator`'s ``DEFAULT_TURBINE_SPECS``, reused
here rather than redefined) — using the LBW 2026 model (:py:class:`csm.models.nlr2026.
Land2026NLR`).

``irs_mpc_breakdown`` needs three costs the model doesn't compute on its own — tower flange
material cost, tower flange production cost, and turbine production cost — so this script derives
them from the model's own real outputs using the rules given for this table specifically:

- Tower flange cost = 6% of the model's own :py:attr:`tower_cost`
- Tower flange material cost = 50% of the tower flange cost
- Tower flange production cost = the other 50% of the tower flange cost
- Turbine production cost = 0.909% of (3 blades + rotor hub + nacelle excl. power converter +
  power converter) — i.e. ``0.00909 * (3 * blade_cost + hub_system_cost + nacelle_cost)``, since
  nacelle excl. power converter plus power converter is exactly :py:attr:`nacelle_cost` (which
  already includes :py:attr:`converter_cost` as one of its own summed components — see
  ``calculate_nacelle_cost``), and "rotor hub" is :py:attr:`hub_system_cost` (hub, pitch system,
  and spinner — see ``calculate_hub_system_cost``), matching the same "Rotor Hub" definition
  ``irs_mpc_breakdown`` itself uses. Kept as an explicit exclude-then-add-back in the code below
  so it reads the same way the rule was specified, rather than the algebraically-simplified form.
"""

from pathlib import Path

import pandas as pd

from csm.models.nlr2026 import Land2026NLR
from csm.tools.experimental.nlr_cower_table_generator import DEFAULT_TURBINE_SPECS, to_model_kwargs


CONFIG_NAMES = ("ATB T3 (3.3MW)", "V150-4.5")

# Both configs should use a single main bearing for this table, overriding whatever
# DEFAULT_TURBINE_SPECS itself says (ATB T3 (3.3MW)'s own entry there is 2) — scoped to this
# script rather than changed at the source, since nlr_cower_table_generator.py's own COWER tables
# still want each config's real bearing count.
NUM_BEARINGS = 1

# No onboard crane assumed for either config's Nacelle cost. Land2026NLR (via Land2020NLR)
# defaults has_crane=True and, since a 2026 fix, actually honors it — zeroing crane_mass/
# crane_cost when False (see calculate_crane_mass/calculate_crane_cost in nlr2020.py).
HAS_CRANE = False

TOWER_FLANGE_OF_TOWER = 0.06
TOWER_FLANGE_MATERIAL_SHARE = 0.50
TOWER_FLANGE_PRODUCTION_SHARE = 0.50
TURBINE_PRODUCTION_RATE = 0.00909


def _derived_irs_costs(model: Land2026NLR) -> dict[str, float]:
    """The three costs :py:meth:`Land2026NLR.irs_mpc_breakdown` needs but doesn't compute on its
    own, derived from `model`'s own real cost outputs per the rules in the module docstring.
    """
    tower_flange_cost = TOWER_FLANGE_OF_TOWER * model.tower_cost
    nacelle_excl_converter = model.nacelle_cost - model.converter_cost
    turbine_production_cost = TURBINE_PRODUCTION_RATE * (
        3 * model.blade_cost + model.hub_system_cost + nacelle_excl_converter + model.converter_cost
    )
    return {
        "turbine_production_cost": turbine_production_cost,
        "tower_flange_material_cost": TOWER_FLANGE_MATERIAL_SHARE * tower_flange_cost,
        "tower_flange_production_cost": TOWER_FLANGE_PRODUCTION_SHARE * tower_flange_cost,
    }


def generate_safe_harbor_tables(
    output_dir: str | Path = "output/safe_harbor_tables",
    config_names: tuple[str, ...] = CONFIG_NAMES,
) -> dict[str, pd.DataFrame]:
    """Runs the LBW 2026 model for each of `config_names` and computes its IRS MPC breakdown
    table, saving each as its own CSV alongside returning it.

    Returns:
        dict[str, pd.DataFrame]: Configuration name -> its IRS MPC breakdown table (see
            :py:meth:`csm.models.base_model.CSMBase.irs_mpc_breakdown`).
    """
    output_dir = Path(output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    tables: dict[str, pd.DataFrame] = {}
    for config_name in config_names:
        spec = DEFAULT_TURBINE_SPECS[config_name]
        model_kwargs = to_model_kwargs(spec) | {
            "num_bearings": NUM_BEARINGS,
            "has_crane": HAS_CRANE,
        }
        model = Land2026NLR(**model_kwargs)
        model.run()

        derived_costs = _derived_irs_costs(model)
        breakdown = model.irs_mpc_breakdown(**derived_costs)
        tables[config_name] = breakdown

        slug = "".join(c if c.isalnum() else "_" for c in config_name).strip("_")
        while "__" in slug:
            slug = slug.replace("__", "_")
        breakdown.to_csv(output_dir / f"safe_harbor_{slug}.csv")

    return tables


if __name__ == "__main__":
    pd.set_option("display.width", 120)
    for name, table in generate_safe_harbor_tables().items():
        print(f"\n=== {name} ===")  # noqa: T201 — CLI entry point, not a debug leftover
        print(table)  # noqa: T201
