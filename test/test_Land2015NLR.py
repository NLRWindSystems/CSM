import pytest
from attrs import fields
from pytest import approx

from csm.models.nlr2015 import Land2015NLR

from test.conftest import csm_2015_test_inputs


@pytest.mark.unit
def test_Land2015NLR_defaults_only(subtests):
    """Tests that all the individual model calculations fail individually and when run as a group.
    Ensures that all results (output) values are still their defaults. The combination of these
    tests ensures that :py:meth:`CSMBase._has_values` and validate_inputs work for models
    with missing inputs.
    """
    nlr2015 = Land2015NLR()
    assert nlr2015.efficiency_max == 1.0
    assert nlr2015.blade_mass_coeff == 0.5
    assert nlr2015.blade_mass_cost_coeff == 14.6
    assert nlr2015.hub_mass_coeff == 2.3
    assert nlr2015.hub_mass_intercept == 1320.0
    assert nlr2015.hub_mass_cost_coeff == 3.9
    assert nlr2015.pitch_bearing_mass_coeff == 0.1295
    assert nlr2015.pitch_bearing_mass_intercept == 491.31
    assert nlr2015.bearing_housing_fraction == 0.3280
    assert nlr2015.mass_sys_offset == 555.0
    assert nlr2015.pitch_system_mass_cost_coeff == 22.1
    assert nlr2015.spinner_mass_coeff == 15.5
    assert nlr2015.spinner_mass_intercept == -980.0
    assert nlr2015.spinner_mass_cost_coeff == 11.1
    assert nlr2015.lss_mass_coeff == 13.0
    assert nlr2015.lss_mass_exp == 0.65
    assert nlr2015.lss_mass_intercept == 775.0
    assert nlr2015.lss_mass_cost_coeff == 11.9
    assert nlr2015.bearing_mass_coeff == 0.0001
    assert nlr2015.bearing_mass_exp == 3.5
    assert nlr2015.bearing_mass_cost_coeff == 4.5
    assert nlr2015.gearbox_torque_density == 200
    assert nlr2015.gearbox_torque_cost == 50
    assert nlr2015.brake_mass_coeff == 0.00122
    assert nlr2015.brake_mass_cost_coeff == 3.6254
    assert nlr2015.hss_mass_coeff == 0.19894
    assert nlr2015.hss_mass_cost_coeff == 6.8
    assert nlr2015.generator_mass_coeff == 2.3
    assert nlr2015.generator_mass_intercept == 3400
    assert nlr2015.generator_mass_cost_coeff == 12.4
    assert nlr2015.bedplate_mass_exp == 2.2
    assert nlr2015.bedplate_mass_cost_coeff == 2.9
    assert nlr2015.yaw_system_non_bearing_mass_coeff == 1.5
    assert nlr2015.yaw_system_mass_coeff == 0.0009
    assert nlr2015.yaw_system_mass_exp == 3.314
    assert nlr2015.yaw_system_mass_cost_coeff == 8.3
    assert nlr2015.hvac_mass_coeff == 0.08
    assert nlr2015.hvac_mass_cost_coeff == 124
    assert nlr2015.nacelle_cover_mass_coeff == 1.2817
    assert nlr2015.nacelle_cover_mass_intercept == 428.19
    assert nlr2015.nacelle_cover_mass_cost_coeff == 5.7
    assert nlr2015.platform_mainframe_mass_coeff == 0.125
    assert not nlr2015.has_crane
    assert nlr2015.crane_mass == 3000
    assert nlr2015.platform_mainframe_mass_cost_coeff == 17.1
    assert nlr2015.crane_cost == 12000.0
    assert nlr2015.transformer_mass_coeff == 1.9150
    assert nlr2015.transformer_mass_intercept == 1910.0
    assert nlr2015.transformer_mass_cost_coeff == 18.8
    assert nlr2015.tower_mass_coeff == 19.828
    assert nlr2015.tower_mass_exp == 2.0282
    assert nlr2015.tower_mass_cost_coeff == 2.9
    assert nlr2015.controls_cost_coeff == 21.15
    assert nlr2015.converter_mass_cost_coeff == 18.8
    assert nlr2015.electrical_connection_cost_coeff == 41.85

    results = nlr2015.get_all_results()
    mass_results = nlr2015.get_mass_results()
    cost_results = nlr2015.get_cost_results()
    with subtests.test("Ensure mass and cost results add to the joint results"):
        non_mass_cost = 2  # rated_rpm, num_tower_sections
        assert len(mass_results) + len(cost_results) + non_mass_cost == len(results)
        assert not set(mass_results).intersection(cost_results)

    with subtests.test("Check default attribute values for results"):
        _fields = fields(Land2015NLR)
        for name, val in results.items():
            default = getattr(_fields, name).default
            assert default == val, (
                f"{name} does not match the default value when no input was provided"
            )


@pytest.mark.regression
def test_Land2015NLR_with_2015_inputs(subtests):
    """Tests against the WISDEM CSM test restults for the 2015 model."""
    csm = Land2015NLR.from_dict(csm_2015_test_inputs)
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
    with subtests.test("Controls mass"):
        assert csm.controls_mass == approx(0.0)
    with subtests.test("Converter mass"):
        assert csm.converter_mass == approx(0.0)
    with subtests.test("Electrical connection mass"):
        assert csm.electrical_connection_mass == approx(0.0)
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
    with subtests.test("Controls cost"):
        assert csm.controls_cost == approx(105750.0)
    with subtests.test("Converter cost"):
        assert csm.converter_cost == approx(0.0)
    with subtests.test("Electrical connection cost"):
        assert csm.electrical_connection_cost == approx(209250.0)
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
        assert csm.turbine_cost_kw == approx(686.0044808706958)
