from copy import deepcopy

import pytest
from attrs import fields
from pytest import approx

from csm.models.base_model import CSMBase

from test.conftest import csm_2015_inputs


csm_2015_outputs = {
    "rotor_angular_velocity_max": None,
    "blade_mass": None,
    "blade_cost": None,
    "rotor_torque": None,
    "hub_mass": None,
    "hub_cost": None,
    "spinner_mass": None,
    "spinner_cost": None,
}


@pytest.mark.unit
def test_defaults_only(subtests):
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
        model.calculate_brake_mass()

    with pytest.raises(ValueError, match=undefined_params_msg):
        model.calculate_brake_cost()

    with pytest.raises(ValueError, match=undefined_params_msg):
        model.calculate_high_speed_shaft_mass()

    with pytest.raises(ValueError, match=undefined_params_msg):
        model.calculate_high_speed_shaft_cost()

    with pytest.raises(ValueError, match=undefined_params_msg):
        model.calculate_generator_mass()

    with pytest.raises(ValueError, match=undefined_params_msg):
        model.calculate_generator_cost()

    with pytest.raises(ValueError, match=undefined_params_msg):
        model.calculate_bedplate_mass()

    with pytest.raises(ValueError, match=undefined_params_msg):
        model.calculate_bedplate_cost()

    with pytest.raises(ValueError, match=undefined_params_msg):
        model.calculate_yaw_system_mass()

    with pytest.raises(ValueError, match=undefined_params_msg):
        model.calculate_yaw_system_cost()

    with pytest.raises(ValueError, match=undefined_params_msg):
        model.calculate_hydraulic_cooling_mass()

    with pytest.raises(ValueError, match=undefined_params_msg):
        model.calculate_hydraulic_cooling_cost()

    with pytest.raises(ValueError, match=undefined_params_msg):
        model.calculate_nacelle_cover_mass()

    with pytest.raises(ValueError, match=undefined_params_msg):
        model.calculate_nacelle_cover_cost()

    with pytest.raises(ValueError, match=undefined_params_msg):
        model.calculate_platform_mainframe_mass()

    with pytest.raises(ValueError, match=undefined_params_msg):
        model.calculate_platform_mainframe_cost()

    with pytest.raises(ValueError, match=undefined_params_msg):
        model.calculate_transformer_mass()

    with pytest.raises(ValueError, match=undefined_params_msg):
        model.calculate_transformer_cost()

    with pytest.raises(ValueError, match=undefined_params_msg):
        model.calculate_nacelle_mass()

    with pytest.raises(ValueError, match=undefined_params_msg):
        model.calculate_nacelle_cost()

    with pytest.raises(ValueError, match=undefined_params_msg):
        model.calculate_tower_mass()

    with pytest.raises(ValueError, match=undefined_params_msg):
        model.calculate_tower_cost()

    with pytest.raises(ValueError, match=undefined_params_msg):
        model.calculate_rotor_mass()

    with pytest.raises(ValueError, match=undefined_params_msg):
        model.calculate_rotor_cost()

    with pytest.raises(ValueError, match=undefined_params_msg):
        model.calculate_hub_system_mass()

    with pytest.raises(ValueError, match=undefined_params_msg):
        model.calculate_hub_system_cost()

    with pytest.raises(ValueError, match=undefined_params_msg):
        model.calculate_turbine_mass()

    with pytest.raises(ValueError, match=undefined_params_msg):
        model.calculate_turbine_cost()

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


@pytest.mark.unit
def test_with_inputs(subtests):
    """Tests the model functionality works as expected when all inputs are defined."""
    blade_variant1 = deepcopy(csm_2015_inputs)
    blade_variant1["blade_has_carbon"] = True

    blade_variant2 = deepcopy(csm_2015_inputs)
    blade_variant2["turbine_class"] = 2
    blade_variant2["has_crane"] = False

    blade_variant3 = deepcopy(blade_variant1)
    blade_variant1["blade_has_carbon"] = True
    blade_variant2["turbine_class"] = 2

    csm1 = CSMBase(**blade_variant1)
    csm2 = CSMBase(**blade_variant2)
    csm3 = CSMBase(**blade_variant3)

    csm1.run()
    csm2.run()
    csm3.run()

    with subtests.test("Check blade differentiation"):
        assert csm1.blade_mass != csm2.blade_mass != csm3.blade_mass

    with subtests.test("Check crane differentiation"):
        assert csm1.platform_mainframe_mass != csm2.platform_mainframe_mass
        assert csm1.platform_mainframe_cost != csm2.platform_mainframe_cost


@pytest.mark.regression
def test_with_2015_inputs(subtests):
    """Tests against the WISDEM CSM test restults for the 2015 model."""
    csm = CSMBase(**csm_2015_inputs)
    csm.run()

    with subtests.test("Blade mass"):
        assert csm.blade_mass == approx(18590.66820649)
    with subtests.test("Hub mass"):
        assert csm.hub_mass == approx(44078.53687493)
    with subtests.test("Pitch system mass"):
        assert csm.pitch_system_mass == approx(10798.90594644)
    with subtests.test("Spinner mass"):
        assert csm.spinner_mass == approx(973.0)
    with subtests.test("Low speed shaft mass"):
        assert csm.low_speed_shaft_mass == approx(22820.27928238)
    with subtests.test("Main bearing mass"):
        assert csm.bearing_mass == approx(2245.41649102)
    with subtests.test("Rated RPM"):
        assert csm.rated_rpm == approx(12.1260909)
    with subtests.test("Rotor torque"):
        assert csm.rotor_torque == approx(4375.0)
    with subtests.test("Gearbox mass"):
        assert csm.gearbox_mass == approx(21875.0)
    with subtests.test("Brake mass"):
        assert csm.brake_mass == approx(5337.5)
    with subtests.test("High speed shaft mass"):
        assert csm.high_speed_shaft_mass == approx(994.7)
    with subtests.test("Generator mass"):
        assert csm.generator_mass == approx(14900.0)
    with subtests.test("Bedplate mass"):
        assert csm.bedplate_mass == approx(41765.26095285)
    with subtests.test("Yaw system mass"):
        assert csm.yaw_system_mass == approx(12329.96247921)
    with subtests.test("Hydraulic cooling mass"):
        assert csm.hydraulic_cooling_mass == approx(400.0)
    with subtests.test("Nacelle cover mass"):
        assert csm.nacelle_cover_mass == approx(6836.69)
    with subtests.test("Platform mainframe mass"):
        assert csm.platform_mainframe_mass == approx(8220.65761911)
    with subtests.test("Transformer mass"):
        assert csm.transformer_mass == approx(11485.0)
    with subtests.test("Tower mass"):
        assert csm.tower_mass == approx(182336.48057717)
    with subtests.test("Hub system mass"):
        assert csm.hub_system_mass == approx(55850.44282136)
    with subtests.test("Rotor mass"):
        assert csm.rotor_mass == approx(111622.44744083)
    with subtests.test("Nacelle mass"):
        assert csm.nacelle_mass == approx(151455.88331558352)
    with subtests.test("Turbine mass"):
        assert csm.turbine_mass == approx(445414.81133358914)

    with subtests.test("Blade cost"):
        assert csm.blade_cost == approx(271423.75581475)
    with subtests.test("Hub cost"):
        assert csm.hub_cost == approx(171906.29381221)
    with subtests.test("Pitch system cost"):
        assert csm.pitch_system_cost == approx(238655.82141628)
    with subtests.test("Spinner cost"):
        assert csm.spinner_cost == approx(10800.3)
    with subtests.test("Rotor cost"):
        # assert csm.rotor_mass_tcc == approx(111622.44744083)
        assert csm.rotor_cost == approx(1235633.68267274)
    with subtests.test("Low speed shaft cost"):
        assert csm.low_speed_shaft_cost == approx(271561.32346034)
    with subtests.test("Main bearing cost"):
        assert csm.bearing_cost == approx(10104.37420958)
    with subtests.test("Gearbox cost"):
        assert csm.gearbox_cost == approx(218750.0)
    with subtests.test("Brake cost"):
        assert csm.brake_cost == approx(19350.5725)
    with subtests.test("High speed shaft cost"):
        assert csm.high_speed_shaft_cost == approx(6763.96)
    with subtests.test("Generator cost"):
        assert csm.generator_cost == approx(184760.0)
    with subtests.test("Bedplate cost"):
        assert csm.bedplate_cost == approx(121119.25676326)
    with subtests.test("Yaw system cost"):
        assert csm.yaw_system_cost == approx(102338.68857747)
    with subtests.test("Hydraulic cooling cost"):
        assert csm.hydraulic_cooling_cost == approx(49600.0)
    # with subtests.test("Hub cost"):
    # assert csm.controls_cost == approx(105750.0)
    # assert csm.converter_cost == approx(0.0)
    # assert csm.elec_cost == approx(209250.0)
    with subtests.test("Nacelle Cover cost"):
        assert csm.nacelle_cover_cost == approx(38969.133)
    with subtests.test("Platform mainframe cost"):
        assert csm.platform_mainframe_cost == approx(101273.24528671)
    with subtests.test("Transformer cost"):
        assert csm.transformer_cost == approx(215918.0)
    with subtests.test("Nacelle cost"):
        assert csm.nacelle_cost == approx(1665612.9280069391)
        # with subtests.test("Hub cost"):
        # assert csm.nacelle_mass_tcc == approx(151455.88331558352 )
        # with subtests.test("Tower parts cost"):
        # assert csm.tower_parts_cost == approx(528775.7936738)
        assert csm.tower_cost == approx(528775.7936738)
    with subtests.test("Hub system cost"):
        # assert csm.hub_system_mass_tcc == approx(55850.44282136)
        assert csm.hub_system_cost == approx(421362.41522849)
    with subtests.test("Rotor cost"):
        assert csm.rotor_cost == approx(1235633.68267274)
    with subtests.test("Turbine cost"):
        # assert csm.turbine_mass_tcc == approx(445414.81133358914)
        assert csm.turbine_cost == approx(3430022.404353479)
        assert csm.turbine_cost_kW == approx(686.0044808706958)


@pytest.mark.unit
def test_from_dict(subtests):
    """Test :py:method:`CSMBase.from_dict`."""
    with subtests.test("2015 inputs from_dict"):
        model = CSMBase.from_dict(csm_2015_inputs)
        for name, val in csm_2015_inputs.items():
            assert val == getattr(model, name)

    with subtests.test("Non-existent inputs"):
        msg = "The initialization for CSMBase was given extraneous inputs: blade_exponent"
        with pytest.raises(AttributeError, match=msg):
            _extra = deepcopy(csm_2015_inputs)
            _extra["blade_exponent"] = 1.22
            CSMBase.from_dict(_extra)

    with subtests.test("Exclusive output as input"):
        msg = "The initialization for CSMBase was given extraneous inputs: turbine_mass"
        with pytest.raises(AttributeError, match=msg):
            _extra = deepcopy(csm_2015_inputs)
            _extra["turbine_mass"] = 1.22
            CSMBase.from_dict(_extra)

    with subtests.test("Missing input"):
        msg = "The class definition for CSMBase is missing the following inputs: rotor_diameter"
        with pytest.raises(AttributeError, match=msg):
            _extra = deepcopy(csm_2015_inputs)
            del _extra["rotor_diameter"]
            CSMBase.from_dict(_extra)
