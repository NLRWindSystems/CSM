import pytest


MODEL_FILENAME = "test_model.py"
MODEL_DIRECTORY = "./test/model"
PATH_CONFIG = "./test/input/config.yaml"


csm_2015_defaults = {
    # defaults
    "blade_mass_coeff": 0.5,
    "blade_mass_cost_coeff": 14.6,
    "hub_mass_coeff": 2.3,
    "hub_mass_intercept": 1320.0,
    "hub_mass_cost_coeff": 3.9,
    "pitch_bearing_mass_coeff": 0.1295,
    "pitch_bearing_mass_intercept": 491.31,
    "bearing_housing_fraction": 0.3280,
    "mass_sys_offset": 555.0,
    "pitch_system_mass_cost_coeff": 22.1,
    "spinner_mass_coeff": 15.5,
    "spinner_mass_intercept": -980.0,
    "spinner_mass_cost_coeff": 11.1,
    "lss_mass_coeff": 13.0,
    "lss_mass_exp": 0.65,
    "lss_mass_intercept": 775,
    "lss_mass_cost_coeff": 11.9,
    "bearing_mass_coeff": 0.0001,
    "bearing_mass_exp": 3.5,
    "bearing_mass_cost_coeff": 4.5,
    "gearbox_torque_density": 200,
    "gearbox_torque_cost": 50,
    "brake_mass_coeff": 0.00122,
    "brake_mass_cost_coeff": 3.6254,
    "hss_mass_coeff": 0.19894,
    "hss_mass_cost_coeff": 6.8,
    "generator_mass_coeff": 2.3,
    "generator_mass_intercept": 3400,
    "generator_mass_cost_coeff": 12.4,
    "bedplate_mass_exp": 2.2,
    "bedplate_mass_cost_coeff": 2.9,
    "yaw_system_non_bearing_mass_coeff": 1.5,
    "yaw_system_mass_coeff": 0.0009,
    "yaw_system_mass_exp": 3.314,
    "yaw_system_mass_cost_coeff": 8.3,
    "hvac_mass_coeff": 0.08,
    "hvac_mass_cost_coeff": 124,
    "nacelle_cover_mass_coeff": 1.2817,
    "nacelle_cover_mass_intercept": 428.19,
    "nacelle_cover_mass_cost_coeff": 5.7,
    "crane_mass": 3000,
    "crane_cost": 12000.0,
    "platform_mainframe_mass_coeff": 0.125,
    "platform_mainframe_mass_cost_coeff": 17.1,
    "transformer_mass_coeff": 1.9150,
    "transformer_mass_intercept": 1910.0,
    "transformer_mass_cost_coeff": 18.8,
    "converter_mass_cost_coeff": 18.8,
    "controls_rated_power_cost_coeff": 21.15,
    "electrical_connection_rated_power_cost_coeff": 41.85,
    "tower_mass_coeff": 19.828,
    "tower_mass_exp": 2.0282,
    "tower_mass_cost_coeff": 2.9,
}
csm_2015_test_inputs = {
    "turbine_class": 1,
    "efficiency_max": 0.9,
    "num_blades": 3,
    "num_bearings": 2,
    "rated_power_kw": 5000,
    "blade_has_carbon": False,
    "has_crane": True,
    "rotor_diameter": 126,
    "max_tip_speed": 80,
    "tower_length": 90,
}
csm_2015_inputs = csm_2015_defaults | csm_2015_test_inputs


def pytest_collection_modifyitems(config, items):
    """Enforce the usage marking tests as either unit, regression, or integration tests.
    This method will need to be imported into all subsequent ``contest.py`` files.
    """
    test_types = {"unit", "regression", "integration"}
    missing_type_mark = [
        f"{item.path}::{item.name}"
        for item in items
        if not test_types.intersection([el.name for el in item.iter_markers()])
    ]
    if missing_type_mark:
        errors = "\n".join(missing_type_mark)
        msg = (
            "The following tests must be marked as either 'unit', 'regression', or 'integration'"
            f" tests using `@pytest.mark.<test-type>`:\n{errors}"
        )
        raise pytest.UsageError(msg)
