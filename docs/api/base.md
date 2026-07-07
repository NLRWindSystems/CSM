(api:base-model)=
# Base Model

```{eval-rst}
.. automodule:: csm.models.base_model
    :members:
    :undoc-members:
    :exclude-members: CSMBase
```

## Base Parameterization

```{eval-rst}
.. autoclass:: csm.models.base_model.CSMBase
    :members: from_dict, update, reset_values
    :undoc-members:
    :exclude-members: turbine_class, rated_power_kw, rotor_diameter, efficiency_max, num_bearings,
        num_blades, blade_has_carbon, blade_mass_coeff, blade_mass_cost_coeff, blade_mass,
        blade_cost, hub_mass_coeff, hub_mass_intercept, hub_mass_cost_coeff, hub_mass, hub_cost,
        max_tip_speed, rated_rpm, rotor_torque, pitch_bearing_mass_coeff,
        pitch_bearing_mass_intercept, bearing_housing_fraction, mass_sys_offset,
        pitch_system_mass_cost_coeff, pitch_system_mass, pitch_system_cost, spinner_mass_coeff,
        spinner_mass_intercept, spinner_mass_cost_coeff, spinner_mass, spinner_cost, lss_mass_coeff,
        lss_mass_intercept, lss_mass_exp, lss_mass_cost_coeff, low_speed_shaft_mass,
        low_speed_shaft_cost, bearing_mass_coeff, bearing_mass_exp, bearing_mass_cost_coeff,
        bearing_mass, bearing_cost, gearbox_torque_density, gearbox_torque_cost, gearbox_mass,
        gearbox_cost, brake_mass_coeff, brake_mass_cost_coeff, brake_mass, brake_cost,
        hss_mass_coeff, hss_mass_cost_coeff, high_speed_shaft_mass, high_speed_shaft_cost,
        generator_mass_coeff, generator_mass_intercept, generator_mass_cost_coeff, generator_mass,
        generator_cost, bedplate_mass_exp, bedplate_mass_cost_coeff, bedplate_mass, bedplate_cost,
        yaw_system_non_bearing_mass_coeff, yaw_system_mass_coeff, yaw_system_mass_exp,
        yaw_system_mass_cost_coeff, yaw_system_mass, yaw_system_cost, hvac_mass_coeff,
        hvac_mass_cost_coeff, hydraulic_cooling_mass, hydraulic_cooling_cost,
        nacelle_cover_mass_coeff, nacelle_cover_mass_intercept, nacelle_cover_mass_cost_coeff,
        nacelle_cover_mass, nacelle_cover_cost, has_crane, crane_mass, crane_cost,
        platform_mainframe_mass_coeff, platform_mainframe_mass_cost_coeff, platform_mainframe_mass,
        platform_mainframe_cost, transformer_mass_coeff, transformer_mass_intercept,
        transformer_mass_cost_coeff, transformer_mass, transformer_cost, controls_mass,
        controls_rated_power_cost_coeff, controls_cost, electrical_connection_mass,
        electrical_connection_rated_power_cost_coeff, electrical_connection_cost, converter_mass,
        converter_mass_cost_coeff, converter_cost, tower_mass_coeff, tower_length, tower_mass_exp,
        tower_mass_cost_coeff, tower_mass, tower_cost, nacelle_mass, nacelle_cost, hub_system_mass,
        hub_system_cost, rotor_mass, rotor_cost, turbine_mass, turbine_cost, turbine_cost_kw,
        parameter_map, parameter_graph, turbine_production_cost, tower_flange_material_cost,
        tower_flange_production_cost,
        fields, fields_dict, _has_values, _validate_inputs, _prepare_calculation,
        reset_values, update, parameterize, run, get_dependent_attributes,
        _get_attr_map,
        get_results, get_mass_results, get_cost_results, irs_mpc_breakdown, total_domestic_content,
        calculate_subsystem_mass, calculate_subsystem_cost, calculate_system_mass,
        calculate_system_cost,
        calculate_blade_mass, calculate_blade_cost, calculate_hub_mass, calculate_hub_cost,
        calculate_pitch_system_mass, calculate_pitch_system_cost, calculate_spinner_mass,
        calculate_spinner_cost, calculate_low_speed_shaft_mass, calculate_low_speed_shaft_cost,
        calculate_bearing_mass, calculate_bearing_cost, calculate_rotor_torque,
        calculate_gearbox_mass, calculate_gearbox_cost, calculate_brake_mass, calculate_brake_cost,
        calculate_high_speed_shaft_mass, calculate_high_speed_shaft_cost, calculate_generator_mass,
        calculate_generator_cost, calculate_bedplate_mass, calculate_bedplate_cost,
        calculate_yaw_system_mass, calculate_yaw_system_cost, calculate_hydraulic_cooling_mass,
        calculate_hydraulic_cooling_cost, calculate_nacelle_cover_mass,
        calculate_nacelle_cover_cost, calculate_platform_mainframe_mass,
        calculate_platform_mainframe_cost, calculate_transformer_mass, calculate_transformer_cost,
        calculate_controls_mass, calculate_controls_cost, calculate_electrical_connection_mass,
        calculate_electrical_connection_cost, calculate_converter_mass,
        calculate_converter_mass_cost_coeff, calculate_converter_cost, calculate_tower_mass,
        calculate_tower_cost, calculate_nacelle_mass, calculate_nacelle_cost,
        calculate_hub_system_mass, calculate_hub_system_cost, calculate_rotor_mass,
        calculate_rotor_cost, calculate_turbine_mass, calculate_turbine_cost,
        calculate_turbine_cost
```

## Running the model

```{eval-rst}
.. automethod:: csm.models.base_model.CSMBase.run
```

```{eval-rst}
.. automethod:: csm.models.base_model.CSMBase.parameterize
```

## Getting Results

```{eval-rst}
.. automethod:: csm.models.base_model.CSMBase.get_results
```

```{eval-rst}
.. automethod:: csm.models.base_model.CSMBase.get_mass_results
```

```{eval-rst}
.. automethod:: csm.models.base_model.CSMBase.get_cost_results
```

```{eval-rst}
.. automethod:: csm.models.base_model.CSMBase.irs_mpc_breakdown
```

```{eval-rst}
.. automethod:: csm.models.base_model.CSMBase.total_domestic_content
```

## Model Helpers

### Dependent Variable Tracking

```{eval-rst}
.. automethod:: csm.models.base_model.CSMBase._get_attr_map
```

```{eval-rst}
.. automethod:: csm.models.base_model.CSMBase.get_dependent_attributes
```

### Data Checking

```{eval-rst}
.. automethod:: csm.models.base_model.CSMBase._has_values
```

```{eval-rst}
.. automethod:: csm.models.base_model.CSMBase._validate_inputs
```

```{eval-rst}
.. automethod:: csm.models.base_model.CSMBase._prepare_calculation
```

### Subclassing

```{eval-rst}
.. autoproperty:: csm.models.base_model.CSMBase.fields
```

```{eval-rst}
.. autoproperty:: csm.models.base_model.CSMBase.fields_dict
```

## Subsystem Calculations

### Rotor

```{eval-rst}
.. automethod:: csm.models.base_model.CSMBase.calculate_blade_mass
```

```{eval-rst}
.. automethod:: csm.models.base_model.CSMBase.calculate_blade_cost
```

#### Hub System

```{eval-rst}
.. automethod:: csm.models.base_model.CSMBase.calculate_hub_mass
```

```{eval-rst}
.. automethod:: csm.models.base_model.CSMBase.calculate_hub_cost
```

```{eval-rst}
.. automethod:: csm.models.base_model.CSMBase.calculate_pitch_system_mass
```

```{eval-rst}
.. automethod:: csm.models.base_model.CSMBase.calculate_pitch_system_cost
```

```{eval-rst}
.. automethod:: csm.models.base_model.CSMBase.calculate_spinner_mass
```

```{eval-rst}
.. automethod:: csm.models.base_model.CSMBase.calculate_spinner_cost
```

### Nacelle

```{eval-rst}
.. automethod:: csm.models.base_model.CSMBase.calculate_low_speed_shaft_mass
```

```{eval-rst}
.. automethod:: csm.models.base_model.CSMBase.calculate_low_speed_shaft_cost
```

```{eval-rst}
.. automethod:: csm.models.base_model.CSMBase.calculate_bearing_mass
```

```{eval-rst}
.. automethod:: csm.models.base_model.CSMBase.calculate_bearing_cost
```

```{eval-rst}
.. automethod:: csm.models.base_model.CSMBase.calculate_rotor_torque
```

```{eval-rst}
.. automethod:: csm.models.base_model.CSMBase.calculate_gearbox_mass
```

```{eval-rst}
.. automethod:: csm.models.base_model.CSMBase.calculate_gearbox_cost
```

```{eval-rst}
.. automethod:: csm.models.base_model.CSMBase.calculate_brake_mass
```

```{eval-rst}
.. automethod:: csm.models.base_model.CSMBase.calculate_brake_cost
```

```{eval-rst}
.. automethod:: csm.models.base_model.CSMBase.calculate_high_speed_shaft_mass
```

```{eval-rst}
.. automethod:: csm.models.base_model.CSMBase.calculate_high_speed_shaft_cost
```

```{eval-rst}
.. automethod:: csm.models.base_model.CSMBase.calculate_generator_mass
```

```{eval-rst}
.. automethod:: csm.models.base_model.CSMBase.calculate_generator_cost
```

```{eval-rst}
.. automethod:: csm.models.base_model.CSMBase.calculate_bedplate_mass
```

```{eval-rst}
.. automethod:: csm.models.base_model.CSMBase.calculate_bedplate_cost
```

```{eval-rst}
.. automethod:: csm.models.base_model.CSMBase.calculate_yaw_system_mass
```

```{eval-rst}
.. automethod:: csm.models.base_model.CSMBase.calculate_yaw_system_cost
```

```{eval-rst}
.. automethod:: csm.models.base_model.CSMBase.calculate_hydraulic_cooling_mass
```

```{eval-rst}
.. automethod:: csm.models.base_model.CSMBase.calculate_hydraulic_cooling_cost
```

```{eval-rst}
.. automethod:: csm.models.base_model.CSMBase.calculate_nacelle_cover_mass
```

```{eval-rst}
.. automethod:: csm.models.base_model.CSMBase.calculate_nacelle_cover_cost
```

```{eval-rst}
.. automethod:: csm.models.base_model.CSMBase.calculate_platform_mainframe_mass
```

```{eval-rst}
.. automethod:: csm.models.base_model.CSMBase.calculate_platform_mainframe_cost
```

```{eval-rst}
.. automethod:: csm.models.base_model.CSMBase.calculate_transformer_mass
```

```{eval-rst}
.. automethod:: csm.models.base_model.CSMBase.calculate_transformer_cost
```

```{eval-rst}
.. automethod:: csm.models.base_model.CSMBase.calculate_controls_mass
```

```{eval-rst}
.. automethod:: csm.models.base_model.CSMBase.calculate_controls_cost
```

```{eval-rst}
.. automethod:: csm.models.base_model.CSMBase.calculate_electrical_connection_mass
```

```{eval-rst}
.. automethod:: csm.models.base_model.CSMBase.calculate_electrical_connection_cost
```

```{eval-rst}
.. automethod:: csm.models.base_model.CSMBase.calculate_converter_mass
```

```{eval-rst}
.. automethod:: csm.models.base_model.CSMBase.calculate_converter_cost
```

### Tower

```{eval-rst}
.. automethod:: csm.models.base_model.CSMBase.calculate_tower_mass
```

```{eval-rst}
.. automethod:: csm.models.base_model.CSMBase.calculate_tower_cost
```

## Subsystem Aggregations

```{eval-rst}
.. automethod:: csm.models.base_model.CSMBase.calculate_subsystem_mass
```

```{eval-rst}
.. automethod:: csm.models.base_model.CSMBase.calculate_subsystem_cost
```

```{eval-rst}
.. automethod:: csm.models.base_model.CSMBase.calculate_system_mass
```

```{eval-rst}
.. automethod:: csm.models.base_model.CSMBase.calculate_system_cost
```

```{eval-rst}
.. automethod:: csm.models.base_model.CSMBase.calculate_nacelle_mass
```

```{eval-rst}
.. automethod:: csm.models.base_model.CSMBase.calculate_nacelle_cost
```

```{eval-rst}
.. automethod:: csm.models.base_model.CSMBase.calculate_hub_system_mass
```

```{eval-rst}
.. automethod:: csm.models.base_model.CSMBase.calculate_hub_system_cost
```

```{eval-rst}
.. automethod:: csm.models.base_model.CSMBase.calculate_rotor_mass
```

```{eval-rst}
.. automethod:: csm.models.base_model.CSMBase.calculate_rotor_cost
```

```{eval-rst}
.. automethod:: csm.models.base_model.CSMBase.calculate_turbine_mass
```

```{eval-rst}
.. automethod:: csm.models.base_model.CSMBase.calculate_turbine_cost
```
