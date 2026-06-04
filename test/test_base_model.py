from copy import deepcopy

import pytest
from attrs import fields

from csm.base_model import CSMBase


csm_2015_inputs = {
    # defaults
    "efficiency_max": 1.0,
    "blade_mass_coeff": 0.5,
    "blade_mass_cost_coeff": 14.6,
    "hub_mass_coeff": 2.3,
    "hub_mass_intercept": 1320.0,
    "hub_mass_cost_coeff": 3.9,
    "rotor_angular_velocity_max": None,
    "num_blades": 3,
    "pitch_bearing_mass_coeff": 0.1295,
    "pitch_bearing_mass_intercept": 491.31,
    "bearing_housing_fraction": 0.3280,
    "mass_sys_offset": 555.0,
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
    # example input
    "turbine_class": 1,
    "blade_has_carbon": False,
    "rated_power_kw": 3500,
    "rotor_diameter": 136.7,
    "max_tip_speed": 71.53,
}

csm_2015_outputs = {
    "rotor_angular_velocity_max": None,
    "blade_mass": None,
    "blade_cost": None,
    "rotor_torque": None,
    "nacelle_length": None,
    "hub_mass": None,
    "hub_cost": None,
    "spinner_mass": None,
    "spinner_cost": None,
}


def test_CSMBase_defaults_only(subtests):
    """Tests that all the individual model calculations fail individually and when run as a group.
    Ensures that all results (output) values are still their defaults. The combination of these
    tests ensures that :py:method:`CSMBase._has_values` and validate_inputs work for models
    with missing inputs.
    """
    model = CSMBase()
    undefined_params_msg = "Inputs for the following variables required"

    with pytest.raises(ValueError, match=undefined_params_msg):
        model.calculate_blade_mass()

    with pytest.raises(ValueError, match=undefined_params_msg):
        model.calculate_blade_cost()

    with pytest.raises(ValueError, match=undefined_params_msg):
        model.calculate_hub_mass()

    with pytest.raises(ValueError, match=undefined_params_msg):
        model.calculate_hub_cost()

    with pytest.raises(ValueError, match=undefined_params_msg):
        model.calculate_pitch_system_mass()

    with pytest.raises(ValueError, match=undefined_params_msg):
        model.calculate_pitch_system_cost()

    with pytest.raises(ValueError, match=undefined_params_msg):
        model.calculate_spinner_mass()

    with pytest.raises(ValueError, match=undefined_params_msg):
        model.calculate_spinner_cost()

    with pytest.raises(ValueError, match=undefined_params_msg):
        model.calculate_low_speed_shaft_mass()

    with pytest.raises(ValueError, match=undefined_params_msg):
        model.calculate_low_speed_shaft_cost()

    with pytest.raises(ValueError, match=undefined_params_msg):
        model.calculate_bearing_mass()

    with pytest.raises(ValueError, match=undefined_params_msg):
        model.calculate_bearing_cost()

    with pytest.raises(ValueError, match=undefined_params_msg):
        model.calculate_rotor_torque()

    with pytest.raises(ValueError, match=undefined_params_msg):
        model.calculate_gearbox_mass()

    with pytest.raises(ValueError, match=undefined_params_msg):
        model.calculate_gearbox_cost()

    with pytest.raises(ValueError, match=undefined_params_msg):
        model.self.calculate_brake_mass()()

    with pytest.raises(ValueError, match=undefined_params_msg):
        model.calculate_brake_cost()

    with pytest.raises(ValueError, match=undefined_params_msg):
        model.run()

    results = model.get_results()
    mass_results = model.get_mass_results()
    cost_results = model.get_cost_results()
    with subtests.test("Ensure mass and cost results add to the joint results"):
        assert len(mass_results) + len(cost_results) == len(results)
        assert not set(mass_results).intersection(cost_results)

    with subtests.test("Check default attribute values for results"):
        _fields = fields(CSMBase)
        for name, val in results.items():
            default = getattr(_fields, name).default
            assert default == val, (
                f"{name} does not match the default value when no input was provided"
            )


def test_CSMBase_with_inputs(subtests):
    """Tests the model functionality works as expected when all inputs are defined."""
    blade_variant1 = deepcopy(csm_2015_inputs)
    blade_variant1["blade_has_carbon"] = True

    blade_variant2 = deepcopy(csm_2015_inputs)
    blade_variant2["turbine_class"] = 2

    blade_variant3 = deepcopy(blade_variant1)
    blade_variant1["blade_has_carbon"] = True
    blade_variant2["turbine_class"] = 2

    csm1 = CSMBase(**blade_variant1)
    csm2 = CSMBase(**blade_variant2)
    csm3 = CSMBase(**blade_variant3)

    csm1.run()
    csm2.run()
    csm3.run()

    assert csm1.blade_mass != csm2.blade_mass != csm3.blade_mass
    # TODO: check actual values
    # TODO: check the outputs


def test_CSMBase_with_outputs_as_inputs(subtests):

    assert True
