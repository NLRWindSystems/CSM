import pytest
from attrs import fields
from pytest import approx

from csm.models.nlr2020 import Land2020NLR


@pytest.mark.unit
def test_Land2020NLR_defaults_only(subtests):
    """Tests that all the individual model calculations fail individually and when run as a group.
    Ensures that all results (output) values are still their defaults. The combination of these
    tests ensures that :py:meth:`CSMBase._has_values` and validate_inputs work for models
    with missing inputs.
    """
    nlr2020 = Land2020NLR()
    assert nlr2020.turbine_class == 1
    assert nlr2020.blade_mass_coeff == 9.2157
    assert nlr2020.blade_mass_exp == 1.7679
    assert nlr2020.blade_mass_cost_coeff == 15.9432
    assert nlr2020.hub_mass_coeff == 3.5793
    assert nlr2020.hub_mass_intercept == -25451.58
    assert nlr2020.hub_mass_cost_coeff == 4.2588
    assert nlr2020.pitch_bearing_mass_coeff == 0.1295
    assert nlr2020.pitch_bearing_mass_intercept == 491.31
    assert nlr2020.bearing_housing_fraction == 0.3280
    assert nlr2020.mass_sys_offset == 555.0
    assert nlr2020.pitch_system_mass_cost_coeff == 24.1332
    assert nlr2020.spinner_mass_coeff == 2.3255
    assert nlr2020.spinner_mass_intercept == 204.65
    assert nlr2020.spinner_mass_cost_coeff == 12.1212
    assert nlr2020.lss_mass_coeff1 == 2.1906
    assert nlr2020.lss_mass_coeff2 == -311.15
    assert nlr2020.lss_mass_intercept == 13108.0
    assert nlr2020.lss_mass_cost_coeff == 12.9948
    assert nlr2020.bearing_mass_coeff == 0.0001
    assert nlr2020.bearing_mass_exp == 3.5
    assert nlr2020.bearing_mass_cost_coeff == 4.914
    assert nlr2020.gearbox_torque_density == 156.46
    assert nlr2020.gearbox_torque_exp == 0.6566
    assert nlr2020.gearbox_torque_cost == 14.0868
    assert nlr2020.brake_mass_coeff == 198.51
    assert nlr2020.brake_mass_intercept == 1.893
    assert nlr2020.brake_mass_cost_coeff == 7.4256
    assert nlr2020.hss_mass_coeff == 0
    assert nlr2020.hss_mass_cost_coeff == 0
    assert nlr2020.high_speed_shaft_mass == 0
    assert nlr2020.high_speed_shaft_cost == 0
    assert nlr2020.generator_mass_coeff == 1754
    assert nlr2020.generator_mass_intercept == 3503.6
    assert nlr2020.generator_mass_cost_coeff == 13.5408
    assert nlr2020.bedplate_mass_exp == 0
    assert nlr2020.bedplate_mass_coeff == 737.88
    assert nlr2020.bedplate_mass_intercept == -68066
    assert nlr2020.bedplate_mass_cost_coeff == 3.1668
    assert nlr2020.yaw_system_non_bearing_mass_coeff == 1.6
    assert nlr2020.yaw_system_mass_coeff == 0.0007
    assert nlr2020.yaw_system_mass_exp == 3.1571
    assert nlr2020.yaw_system_mass_cost_coeff == 9.0636
    assert nlr2020.hvac_mass_coeff == 0
    assert nlr2020.hvac_mass_cost_coeff == 135.408
    assert nlr2020.hydraulic_cooling_mass == 221
    assert nlr2020.nacelle_cover_mass_coeff == 1281.7
    assert nlr2020.nacelle_cover_mass_intercept == 428.19
    assert nlr2020.nacelle_cover_mass_cost_coeff == 6.2244
    assert nlr2020.has_crane
    assert nlr2020.platform_mainframe_mass_coeff == 0.005
    assert nlr2020.platform_mainframe_mass_cost_coeff == 18.6732
    assert nlr2020.crane_mass == 3000
    assert nlr2020.crane_mass_cost_coeff == 4.368
    assert nlr2020.transformer_mass_coeff == 1915.0
    assert nlr2020.transformer_mass_intercept == 1910.0
    assert nlr2020.transformer_mass_cost_coeff == 20.5296
    assert nlr2020.converter_mass_cost_coeff == 18.8
    assert nlr2020.controls_cost_coeff == 23.0958
    assert nlr2020.electrical_connection_cost_coeff == 45.7002
    assert nlr2020.tower_mass_coeff == 0.152
    assert nlr2020.tower_mass_intercept == -14281.0
    assert nlr2020.tower_mass_cost_coeff == 3.1668
    assert nlr2020.transport_power_electronics_cost_coeff == 9
    assert nlr2020.transport_drivetrain_cost_coeff1 == 9000
    assert nlr2020.transport_drivetrain_cost_coeff2 == 45000
    assert nlr2020.transport_blade_cost_coeff1 == 0.543
    assert nlr2020.transport_blade_cost_coeff2 == -7.4903
    assert nlr2020.transport_blade_cost_coeff3 == -2847.5
    assert nlr2020.transport_blade_cost_intercept == 103627
    assert nlr2020.transport_hub_cost_intercept == 5000
    assert nlr2020.transport_tower_cost_coeff == 34083
    assert nlr2020.tower_section_mass_max == 80000
    assert nlr2020.transport_misc_parts_cost_coeff == 0.025

    results = nlr2020.get_results()
    mass_results = nlr2020.get_mass_results()
    cost_results = nlr2020.get_cost_results()
    with subtests.test("Ensure mass and cost results add to the joint results"):
        assert len(mass_results) + len(cost_results) + 2 == len(results)  # torque + rated rpm
        assert not set(mass_results).intersection(cost_results)

    with subtests.test("Check default attribute values for results"):
        _fields = fields(Land2020NLR)
        for name, val in results.items():
            default = getattr(_fields, name).default
            assert default == val, (
                f"{name} does not match the default value when no input was provided"
            )


@pytest.mark.regression
def test_Land2020NLR_with_inputs(subtests):
    """Tests against the WISDEM CSM test restults for the 2015 model."""
    num_bearings = 2
    inputs = {
        "num_bearings": num_bearings,
        "rotor_diameter": 162,
        "efficiency_max": 0.9,
        "max_tip_speed": 100,
        "rated_power_kw": 6200,
        "tower_length": 150,
    }
    model = Land2020NLR.from_dict(inputs)
    model.run()

    with subtests.test("Blade mass"):
        assert model.blade_mass == approx(21804.141589129507)
    with subtests.test("Hub mass"):
        assert model.hub_mass == approx(52591.98398997124)
    with subtests.test("Pitch system mass"):
        assert model.pitch_system_mass == approx(12456.8268417964)
    with subtests.test("Spinner mass"):
        assert model.spinner_mass == approx(581.381)
    with subtests.test("Low speed shaft mass"):
        assert model.low_speed_shaft_mass == approx(20191.8064)
    with subtests.test("Main bearing mass"):
        assert model.bearing_mass == approx(10822.623405136128 / num_bearings)
    with subtests.test("Rated RPM"):
        assert model.rated_rpm == approx(11.789255043844097)
    with subtests.test("Rotor torque"):
        assert model.rotor_torque == approx(5580.0)
    with subtests.test("Gearbox mass"):
        assert model.gearbox_mass == approx(45127.71468348047)
    with subtests.test("Brake mass"):
        assert model.brake_mass == approx(1232.655)
    with subtests.test("High speed shaft mass"):
        assert model.high_speed_shaft_mass == approx(0)
    with subtests.test("Generator mass"):
        assert model.generator_mass == approx(14378.400000000001)
    with subtests.test("Bedplate mass"):
        assert model.bedplate_mass == approx(41765.26095285)
    with subtests.test("Yaw system mass"):
        assert model.yaw_system_mass == approx(10589.55901713559)
    with subtests.test("Hydraulic cooling mass"):
        assert model.hydraulic_cooling_mass == approx(221.0)
    with subtests.test("Nacelle cover mass"):
        assert model.nacelle_cover_mass == approx(8374.73)
    with subtests.test("Crane mass"):
        assert model.crane_mass == approx(257.3528)
    with subtests.test("Transformer mass"):
        assert model.transformer_mass == approx(13783.0)
    with subtests.test("Controls mass"):
        assert model.controls_mass == approx(0.0)
    with subtests.test("Converter mass"):
        assert model.converter_mass == approx(0.0)
    with subtests.test("Electrical connection mass"):
        assert model.electrical_connection_mass == approx(0.0)
    with subtests.test("Tower mass"):
        assert model.tower_mass == approx(455672.35832462006)
    with subtests.test("Hub system mass"):
        assert model.hub_system_mass == approx(52591.98398997124)
    with subtests.test("Rotor mass"):
        assert model.rotor_mass == approx(111622.44744083)
    with subtests.test("Nacelle mass"):
        assert model.nacelle_mass == approx(176706.7541057522)
    with subtests.test("Turbine mass"):
        assert model.turbine_mass == approx(445414.81133358914)

    with subtests.test("Blade cost"):
        assert model.blade_cost == approx(347627.7901838095)
    with subtests.test("Hub cost"):
        assert model.hub_cost == approx(223978.7414164895)
    with subtests.test("Pitch system cost"):
        assert model.pitch_system_cost == approx(300623.0935384411)
    with subtests.test("Spinner cost"):
        assert model.spinner_cost == approx(7047.0353772)
    with subtests.test("Rotor cost"):
        # assert model.rotor_mass_tcc == approx(111622.44744083)
        assert model.rotor_cost == approx(1235633.68267274)
    with subtests.test("Low speed shaft cost"):
        assert model.low_speed_shaft_cost == approx(262388.48580672)
    with subtests.test("Main bearing cost"):
        assert model.bearing_cost == approx(53182.37141283893 / num_bearings)
    with subtests.test("Gearbox cost"):
        assert model.gearbox_cost == approx(635705.0912032528)
    with subtests.test("Brake cost"):
        assert model.brake_cost == approx(9153.202968)
    with subtests.test("High speed shaft cost"):
        assert model.high_speed_shaft_cost == approx(0)
    with subtests.test("Generator cost"):
        assert model.generator_cost == approx(194695.03872000004)
    with subtests.test("Bedplate cost"):
        assert model.bedplate_cost == approx(121119.25676326)
    with subtests.test("Yaw system cost"):
        assert model.yaw_system_cost == approx(95979.52710771014)
    with subtests.test("Hydraulic cooling cost"):
        assert model.hydraulic_cooling_cost == approx(29925.167999999998)
    # with subtests.test("Hub cost"):
    # assert model.controls_cost == approx(105750.0)
    # assert model.converter_cost == approx(0.0)
    # assert model.elec_cost == approx(209250.0)
    with subtests.test("Nacelle Cover cost"):
        assert model.nacelle_cover_cost == approx(52127.669412)
    with subtests.test("Platform mainframe cost"):
        assert model.platform_mainframe_cost == approx(4805.60030496)
    with subtests.test("Crane cost"):
        assert model.crane_cost == approx(1124.1170304000002)
    with subtests.test("Transformer cost"):
        assert model.transformer_cost == approx(282959.4768)
    with subtests.test("Controls cost"):
        assert model.controls_cost == approx(143193.96)
    with subtests.test("Converter cost"):
        assert model.converter_cost == approx(0.0)
    with subtests.test("Electrical connection cost"):
        assert model.electrical_connection_cost == approx(283341.24)
    with subtests.test("Nacelle cost"):
        assert model.nacelle_cost == approx(2211577.918173882)
        # with subtests.test("Hub cost"):
        # assert model.nacelle_mass_tcc == approx(151455.88331558352 )
        # with subtests.test("Tower parts cost"):
        # assert model.tower_parts_cost == approx(528775.7936738)
        assert model.tower_cost == approx(528775.7936738)
    with subtests.test("Hub system cost"):
        # assert model.hub_system_mass_tcc == approx(55850.44282136)
        assert model.hub_system_cost == approx(223978.7414164895)
    with subtests.test("Rotor cost"):
        assert model.rotor_cost == approx(1235633.68267274)
    with subtests.test("Turbine cost"):
        # assert model.turbine_mass_tcc == approx(445414.81133358914)
        assert model.turbine_cost == approx(3430022.404353479)
        assert model.turbine_cost_kw == approx(686.0044808706958)
