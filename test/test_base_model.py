from copy import deepcopy
from itertools import product

import pytest
import networkx as nx
from attrs import fields, fields_dict
from pytest import approx

from csm.models.base_model import CSMBase, parameter_map

from test.conftest import csm_2015_inputs, csm_2015_defaults


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

    # NOTE: no default relationship
    # with pytest.raises(ValueError, match=undefined_params_msg):
    #     model.calculate_converter_mass()

    with pytest.raises(ValueError, match=undefined_params_msg):
        model.calculate_converter_cost()

    # NOTE: no default relationship
    # with pytest.raises(ValueError, match=undefined_params_msg):
    #     model.calculate_controls_mass()

    with pytest.raises(ValueError, match=undefined_params_msg):
        model.calculate_controls_cost()

    # NOTE: no default relationship
    # with pytest.raises(ValueError, match=undefined_params_msg):
    #     model.calculate_electrical_connection_mass()

    with pytest.raises(ValueError, match=undefined_params_msg):
        model.calculate_electrical_connection_cost()

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
        len_results = len(mass_results) + len(cost_results) + 2  # account for torque + rated rpm
        assert len_results == len(results)
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
    with subtests.test("Controls cost"):
        assert csm.controls_cost == approx(105750.0)
    with subtests.test("Converter cost"):
        assert csm.converter_cost == approx(0.0)
    with subtests.test("Electrical connection cost"):
        assert csm.electrical_connection_cost == approx(209250.0)
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
        assert csm.turbine_cost_kw == approx(686.0044808706958)


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

    with subtests.test("Missing input with partial allowed"):
        _extra = deepcopy(csm_2015_inputs)
        del _extra["rotor_diameter"]
        model = CSMBase.from_dict(_extra, partial=True)
        assert model.rotor_diameter is None


@pytest.mark.unit
def test_attrs_pre_post_initialization():
    """Test :py:method:`CSMBase.__attrs_pre_init__` and :py:method:`CSMBase.__attrs_post_init__`."""
    model = CSMBase()
    assert model.parameter_map == parameter_map

    parameter_graph = model.parameter_graph
    assert isinstance(parameter_graph, nx.DiGraph)

    expected_nodes = set(parameter_map).union(list(sum(parameter_map.values(), ())))
    assert sorted(parameter_graph.nodes) == sorted(expected_nodes)


@pytest.mark.unit
def test_get_dependent_attributes():
    """Test :py:method:`CSMBase.test_get_dependent_attributes`."""
    model = CSMBase()
    blade_has_carbon_upstream = {
        "blade_mass",
        "blade_cost",
        "hub_mass",
        "hub_cost",
        "pitch_system_mass",
        "pitch_system_cost",
        "low_speed_shaft_mass",
        "low_speed_shaft_cost",
        "rotor_mass",
        "rotor_cost",
        "hub_system_mass",
        "hub_system_cost",
        "nacelle_mass",
        "nacelle_cost",
        "turbine_mass",
        "turbine_cost",
    }
    assert blade_has_carbon_upstream == model.get_dependent_attributes("blade_has_carbon")


@pytest.mark.unit
def test_fields():
    """Test :py:method:`CSMBase.fields`."""
    correct_fields = fields(CSMBase)
    model = CSMBase()
    model_fields = model.fields
    assert correct_fields == model_fields


@pytest.mark.unit
def test_fields_dict():
    """Test :py:method:`CSMBase.fields_dict`."""
    correct_fields_dict = fields_dict(CSMBase)
    model = CSMBase()
    model_fields_dict = model.fields_dict
    assert correct_fields_dict == model_fields_dict


@pytest.mark.unit
def test_has_values(subtests):
    """Test :py:method:`CSMBase._has_values`."""
    model = CSMBase.from_dict(csm_2015_inputs)
    with subtests.test("Ensure 2015 values registered"):
        assert all(model._has_values(*csm_2015_inputs))

    calculated = [
        k for k, v in model.fields_dict.items() if v.metadata.get("io") in ("both", "output")
    ]
    with subtests.test("Check calculated values unregistered"):
        assert not all(model._has_values(*calculated))

    with subtests.test("Check calculated registered after run"):
        model.run()
        assert all(model._has_values(*calculated))

    non_none_defaults = ("num_blades",)
    model = CSMBase()
    with subtests.test("Empty model has no registered values, except base defaults"):
        no_none_defaults = set(csm_2015_inputs).union(calculated).difference(non_none_defaults)
        assert not all(model._has_values(*no_none_defaults))
        assert model._has_values(*non_none_defaults)

    model = CSMBase(num_blades=None)
    with subtests.test("Non-None default given None has no registered value"):
        all_attributes = set(csm_2015_inputs).union(calculated)
        assert not all(model._has_values(*all_attributes))


@pytest.mark.unit
def test_validate_inputs(subtests):
    """Test :py:method:`CSMBase._validate_inputs`."""
    # don't use from_dict since this is an incomplete model definition
    model = CSMBase(**csm_2015_defaults)
    blade_mass_inputs = model.parameter_map["blade_mass"]
    with subtests.test("2015 defaults only can't validate"):
        # order taken from parameter_map for consistency
        missing = ("rotor_diameter", "turbine_class", "blade_has_carbon")

        msg = f"Inputs for the following variables required: {', '.join(missing)}"
        with pytest.raises(ValueError, match=msg):
            model._validate_inputs(blade_mass_inputs)

    with subtests.test("Complete definition doesn't raise an error"):
        model.rotor_diameter = 126
        model.turbine_class = 1
        model.blade_has_carbon = True
        assert model._validate_inputs(blade_mass_inputs) is None


@pytest.mark.unit
def test_prepare_calculation(subtests):
    """Test :py:method:`CSMBase._prepare_calculation`."""
    # don't use from_dict since this is an incomplete model definition
    model = CSMBase(**csm_2015_defaults)
    with subtests.test("2015 defaults only can't validate"):
        # order taken from parameter_map for consistency
        missing = ("rotor_diameter", "turbine_class", "blade_has_carbon")

        msg = f"Inputs for the following variables required: {', '.join(missing)}"
        with pytest.raises(ValueError, match=msg):
            model._prepare_calculation("blade_mass")

    with subtests.test("Existing value and dependents undefined is True"):
        model.blade_mass = 100000
        assert model._prepare_calculation("blade_mass")

    with subtests.test("Complete definition doesn't raise an error but needs calculating"):
        model.blade_mass = None
        model.rotor_diameter = 126
        model.turbine_class = 1
        model.blade_has_carbon = True
        assert not model._prepare_calculation("blade_mass")

    with subtests.test("Existing value with all dependents returns True"):
        model.blade_mass = 100000
        assert model._prepare_calculation("blade_mass")


@pytest.mark.unit
def test_reset_values(subtests):
    """Test :py:method:`CSMBase.reset_values`."""
    model = CSMBase.from_dict(csm_2015_inputs)
    blade_mass_inputs = model.parameter_map["blade_mass"]
    assert all(model._has_values(*blade_mass_inputs))

    model.reset_values(*blade_mass_inputs)
    assert not all(model._has_values(*blade_mass_inputs))

    with pytest.raises(KeyError):
        model.reset_values(*["blade_mass_typo"])


@pytest.mark.unit
def test_update(subtests):
    """Test :py:method:`CSMBase.update`."""
    model = CSMBase.from_dict(csm_2015_inputs)
    model.run()

    blade_has_carbon_upstream = {
        "blade_mass",
        "blade_cost",
        "hub_mass",
        "hub_cost",
        "pitch_system_mass",
        "pitch_system_cost",
        "low_speed_shaft_mass",
        "low_speed_shaft_cost",
        "rotor_mass",
        "rotor_cost",
        "hub_system_mass",
        "hub_system_cost",
        "nacelle_mass",
        "nacelle_cost",
        "turbine_mass",
        "turbine_cost",
    }

    with subtests.test("Check expected values at initialization"):
        assert all(model._has_values(*blade_has_carbon_upstream.union(["blade_has_carbon"])))
        assert not model.blade_has_carbon

    with subtests.test("Check update process changes value and resets dependents"):
        model.update({"blade_has_carbon": True})
        assert model.blade_has_carbon
        assert not all(model._has_values(*blade_has_carbon_upstream))

    with subtests.test("Invalid parameter fails"), pytest.raises(AttributeError):
        model.update({"blade_has_more_carbon": 2})

    with subtests.test("Invalid input fails"), pytest.raises(ValueError):
        model.update(("blade_has_more_carbon", 2))


@pytest.mark.unit
def test_parameterize(subtests):
    """Test :py:method:`CSMBase.parameterize`."""
    base = deepcopy(csm_2015_inputs)
    parameters = {
        "efficiency_max": ("range", 0.85, 0.95, 3),
        "rotor_diameter": ("range", 120, 130, 3),
        "blade_has_carbon": ("inputs", True, False),
    }
    del base["efficiency_max"]
    del base["rotor_diameter"]
    del base["blade_has_carbon"]

    with subtests.test("Working example for all input types"):
        inputs = list(product((0.85, 0.9, 0.95), (120.0, 125.0, 130.0), (True, False)))
        outputs = [
            k
            for k, val in fields_dict(CSMBase).items()
            if val.metadata.get("io") in ("both", "output")
        ]
        results = CSMBase.parameterize(base_kwargs=base, parameterized_kwargs=parameters)

        assert results.shape == (len(outputs), len(inputs))
        assert results.index.tolist() == sorted(outputs)
        for _output, _input in zip(results.columns, inputs, strict=True):
            assert all(
                _in == pytest.approx(_out) for _in, _out in zip(_input, _output, strict=True)
            )

    with subtests.test("Working example for subset of outputs"):
        inputs = list(product((0.85, 0.9, 0.95), (120.0, 125.0, 130.0), (True, False)))
        outputs = ["rotor_torque", "turbine_cost_kw"]
        results = CSMBase.parameterize(
            base_kwargs=base, parameterized_kwargs=parameters, results=outputs
        )

        assert results.shape == (len(outputs), len(inputs))
        assert results.index.tolist() == sorted(outputs)

    with subtests.test("Working example for single output"):
        inputs = list(product((0.85, 0.9, 0.95), (120.0, 125.0, 130.0), (True, False)))
        outputs = "turbine_cost_kw"
        results = CSMBase.parameterize(
            base_kwargs=base, parameterized_kwargs=parameters, results=outputs
        )
        outputs = [outputs]

        assert results.shape == (len(outputs), len(inputs))
        assert results.index.tolist() == sorted(outputs)

    with subtests.test("Bad parameterization input type"):
        parameters = {
            "efficiency_max": ("linspace", 0.85, 0.95, 3),
            "rotor_diameter": ("range", 120, 130, 3),
            "blade_has_carbon": ("inputs", True, False),
        }
        msg = "First value for 'efficiency_max' must be 'inputs' or 'range', not 'linspace'."
        with pytest.raises(ValueError, match=msg):
            results = CSMBase.parameterize(base_kwargs=base, parameterized_kwargs=parameters)

    with subtests.test("Bad range input specification"):
        parameters = {
            "efficiency_max": ("range", 0.85, 0.9, 3),
            "rotor_diameter": ("range", 120, 130),
            "blade_has_carbon": ("inputs", True, False),
        }
        msg = (
            "'range' input for 'rotor_diameter' must have 3 values: start, stop, and number of"
            " total values."
        )
        with pytest.raises(ValueError, match=msg):
            results = CSMBase.parameterize(base_kwargs=base, parameterized_kwargs=parameters)

    with subtests.test("Too few inputs for range-type"):
        parameters = {
            "efficiency_max": ("range", 0.85, 0.95, 1),
            "rotor_diameter": ("range", 120, 130, 3),
            "blade_has_carbon": ("inputs", True, False),
        }
        msg = "Parameterized inputs for 'efficiency_max' must have at least 2 values."
        with pytest.raises(ValueError, match=msg):
            results = CSMBase.parameterize(base_kwargs=base, parameterized_kwargs=parameters)

    with subtests.test("Too few inputs for input-type"):
        parameters = {
            "efficiency_max": ("range", 0.85, 0.95, 3),
            "rotor_diameter": ("range", 120, 130, 3),
            "blade_has_carbon": ("inputs", False),
        }
        msg = "Parameterized inputs for 'blade_has_carbon' must have at least 2 values."
        with pytest.raises(ValueError, match=msg):
            results = CSMBase.parameterize(base_kwargs=base, parameterized_kwargs=parameters)
