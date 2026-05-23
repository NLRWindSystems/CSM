from attrs import fields
import pytest

from csm.base_model import CSMBase


def test_CSMBase_defaults_only(subtests):
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


