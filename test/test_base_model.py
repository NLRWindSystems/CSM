from copy import deepcopy

from attrs import fields
import pytest

from csm.base_model import CSMBase


csm_2015_inputs = {
    # defaults
    "turbine_class": 1,
    "rotor_efficiency_max": None,
    "blade_has_carbon": False,
    "blade_mass_coeff": 0.5,
    "blade_mass_cost_coeff": 14.6,
    "hub_mass_coeff": 2.3,
    "hub_mass_intercept": 1320.0,
    "hub_mass_cost_coeff": 3.9,
    "rotor_angular_velocity_max": None,

    # example input
    "rated_power_kw": 3500,
    "rotor_diameter": None,
}

csm_2015_outputs = {
    "rotor_angular_velocity_max": None,
    "blade_mass": None,
    "blade_cost": None,
    "rotor_torque": None,
    "nacelle_length": None,
    "hub_mass": None,
    "hub_cost": None,
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
        model.calculate_rotor_torque()
        
    with pytest.raises(ValueError, match=undefined_params_msg):
        model.calculate_blade_cost()
    
    with pytest.raises(ValueError, match=undefined_params_msg):
        model.run()
    
    results = model.get_results()
    _fields = fields(CSMBase)
    for name, val in results.items():
        default = getattr(_fields, name).default
        assert default == val, f"{name} does not match the default value when no input was provided"


def test_CSMBase_with_inputs(subtests):
    """Tests the model functionality works as expected when all inputs are defined."""

    blade_variant1 =  deepcopy(csm_2015_inputs)
    blade_variant1["blade_has_carbon"] = True
    
    blade_variant2 =  deepcopy(csm_2015_inputs)
    blade_variant2["turbine_class"] = 2
    
    blade_variant3 =  deepcopy(blade_variant1)
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