# Calculating and Getting Results

## Primary API

Main interface of the model for end users creating and running a model, and getting results.

| Method | Description |
| ---------- | ----------- |
| [`from_dict`](#csm.models.CSMBase.from_dict)(data, partial) | Create a complete or incomplete model from a configuration data dictionary. |
| [`calculate`](#csm.models.CSMBase.calculate)(args) | Calculate individual or a series of outputs. |
| [`run`](#csm.models.CSMBase.run)() | Calculate all outputs. |
| [`parameterize`](#csm.models.CSMBase.parameterize)(base_kwargs, parameterized_kwargs, results) | Parameter sweep. |
| [`parameterize_subset`](#csm.models.CSMBase.parameterize_subset)(base_kwargs, parameterized_kwargs, results) |  Parameter sweep with only partial calculation of results for incomplete model definitions. |
| [`get_results`](#csm.models.CSMBase.get_results)(args) | Retrieve a dictionary of calculated attributes. |
| [`get_all_results`](#csm.models.CSMBase.get_all_results)() | Retrieve a dictionary of all calculated attributes. |
| [`get_mass_results`](#csm.models.CSMBase.get_mass_results)() | Retrieve a dictionary of calculated mass attributes. |
| [`get_cost_results`](#csm.models.CSMBase.get_cost_results)() | Retrieve a dictionary of calculated cost attributes. |
| [`irs_mpc_breakdown`](#csm.models.CSMBase.irs_mpc_breakdown)(turbine_production_cost, tower_flange_material_cost, tower_flange_production_cost) | Calculate the base cost breakdown of the US IRS manufactured product component tables. |
| [`total_domestic_content`](#csm.models.CSMBase.total_domestic_content)(turbine_production_cost, tower_flange_material_cost, tower_flange_production_cost, domestic) | Calculates the total, valid domestic content production percentage |

## Subsystems

The folllowing is a breakdown of all the individual subsystem calculations available.  All subsystem
values use:math:`kg` for mass and :math:`USD` for cost. Any other values will have units listed.

| System | Method | Description |
| ------ | ---------- | ----------- |
| Rotor | [`calculate_blade_mass`](#csm.models.CSMBase.calculate_blade_mass)() | Calculate mass of a single blade. |
| Rotor | [`calculate_blade_cost`](#csm.models.CSMBase.calculate_blade_cost)() | Calculate cost of a single blade. |
| Hub System | [`calculate_hub_mass`](#csm.models.CSMBase.calculate_hub_mass)() | Calculate mass of the hub. |
| Hub System | [`calculate_hub_cost`](#csm.models.CSMBase.calculate_hub_cost)() | Calculate cost of the hub. |
| Hub System | [`calculate_pitch_system_mass`](#csm.models.CSMBase.calculate_pitch_system_mass)() | Calculate mass of the pitch system. |
| Hub System | [`calculate_pitch_system_cost`](#csm.models.CSMBase.calculate_pitch_system_cost)() | Calculate cost of the pitch system. |
| Hub System | [`calculate_spinner_mass`](#csm.models.CSMBase.calculate_spinner_mass)() | Calculate mass of the spinner (nose cone). |
| Hub System | [`calculate_spinner_cost`](#csm.models.CSMBase.calculate_spinner_cost)() | Calculate cost of the spinner (nose cone). |
| Nacelle | [`calculate_low_speed_shaft_mass`](#csm.models.CSMBase.calculate_low_speed_shaft_mass)() | Calculate mass of the low speed shaft. |
| Nacelle | [`calculate_low_speed_shaft_cost`](#csm.models.CSMBase.calculate_low_speed_shaft_cost)() | Calculate cost of the low speed shaft. |
| Nacelle | [`calculate_bearing_mass`](#csm.models.CSMBase.calculate_bearing_mass)() | Calculate mass of a single main bearing. |
| Nacelle | [`calculate_bearing_cost`](#csm.models.CSMBase.calculate_bearing_cost)() | Calculate cost of a single main bearing. |
| Nacelle | [`calculate_rotor_torque`](#csm.models.CSMBase.calculate_rotor_torque)() | Calculate the rotor_torque (:math:`Nm`). |
| Nacelle | [`calculate_gearbox_mass`](#csm.models.CSMBase.calculate_gearbox_mass)() | Calculate mass of the gearbox. |
| Nacelle | [`calculate_gearbox_cost`](#csm.models.CSMBase.calculate_gearbox_cost)() | Calculate cost of the gearbox. |
| Nacelle | [`calculate_brake_mass`](#csm.models.CSMBase.calculate_brake_mass)() | Calculate mass of the brakes. |
| Nacelle | [`calculate_brake_cost`](#csm.models.CSMBase.calculate_brake_cost)() | Calculate cost of the brakes. |
| Nacelle | [`calculate_high_speed_shaft_mass`](#csm.models.CSMBase.calculate_high_speed_shaft_mass)() | Calculate mass of the high speed shaft. |
| Nacelle | [`calculate_high_speed_shaft_cost`](#csm.models.CSMBase.calculate_high_speed_shaft_cost)() | Calculate cost of the high speed shaft. |
| Nacelle | [`calculate_generator_mass`](#csm.models.CSMBase.calculate_generator_mass)() | Calculate mass of the generator. |
| Nacelle | [`calculate_generator_cost`](#csm.models.CSMBase.calculate_generator_cost)() | Calculate cost of the generator. |
| Nacelle | [`calculate_bedplate_mass`](#csm.models.CSMBase.calculate_bedplate_mass)() | Calculate mass of the bedplate. |
| Nacelle | [`calculate_bedplate_cost`](#csm.models.CSMBase.calculate_bedplate_cost)() | Calculate cost of the bedplate. |
| Nacelle | [`calculate_yaw_system_mass`](#csm.models.CSMBase.calculate_yaw_system_mass)() | Calculate mass of the yaw system. |
| Nacelle | [`calculate_yaw_system_cost`](#csm.models.CSMBase.calculate_yaw_system_cost)() | Calculate cost of the yaw system. |
| Nacelle | [`calculate_hydraulic_cooling_mass`](#csm.models.CSMBase.calculate_hydraulic_cooling_mass)() | Calculate mass of the HVAC system. |
| Nacelle | [`calculate_hydraulic_cooling_cost`](#csm.models.CSMBase.calculate_hydraulic_cooling_cost)() | Calculate cost of the HVAC system. |
| Nacelle | [`calculate_nacelle_cover_mass`](#csm.models.CSMBase.calculate_nacelle_cover_mass)() | Calculate mass of the nacelle cover. |
| Nacelle | [`calculate_nacelle_cover_cost`](#csm.models.CSMBase.calculate_nacelle_cover_cost)() | Calculate cost of the nacelle cover. |
| Nacelle | [`calculate_platform_mainframe_mass`](#csm.models.CSMBase.calculate_platform_mainframe_mass)() | Calculate mass of the platform railing. |
| Nacelle | [`calculate_platform_mainframe_cost`](#csm.models.CSMBase.calculate_platform_mainframe_cost)() | Calculate cost of the platform railing. |
| Nacelle | [`calculate_transformer_mass`](#csm.models.CSMBase.calculate_transformer_mass)() | Calculate mass of the transformer. |
| Nacelle | [`calculate_transformer_cost`](#csm.models.CSMBase.calculate_transformer_cost)() | Calculate cost of the transformer. |
| Nacelle | [`calculate_controls_mass`](#csm.models.CSMBase.calculate_controls_mass)() | Calculate mass of the controls system. |
| Nacelle | [`calculate_controls_cost`](#csm.models.CSMBase.calculate_controls_cost)() | Calculate cost of the controls system. |
| Nacelle | [`calculate_electrical_connection_mass`](#csm.models.CSMBase.calculate_electrical_connection_mass)() | Calculate mass of the electrical connections. |
| Nacelle | [`calculate_electrical_connection_cost`](#csm.models.CSMBase.calculate_electrical_connection_cost)() | Calculate cost of the electrical connections. |
| Nacelle | [`calculate_converter_mass`](#csm.models.CSMBase.calculate_converter_mass)() | Calculate mass of the electrical converter system. |
| Nacelle | [`calculate_converter_cost`](#csm.models.CSMBase.calculate_converter_cost)() | Calculate cost of the electrical converter system. |
| Tower | [`calculate_tower_mass`](#csm.models.CSMBase.calculate_tower_mass)() | Calculate mass of the tower. |
| Tower | [`calculate_tower_cost`](#csm.models.CSMBase.calculate_tower_cost)() | Calculate cost of the tower. |

## Subsystem Aggregations (Systems)

| Method | Description |
| ---------- | ----------- |
| [`calculate_subsystem_mass`](#csm.models.CSMBase.calculate_subsystem_mass)() | Calculate mass of all subsystems listed above. |
| [`calculate_subsystem_cost`](#csm.models.CSMBase.calculate_subsystem_cost)() | Calculate cost of all subsystems
listed above. |
| [`calculate_nacelle_mass`](#csm.models.CSMBase.calculate_nacelle_mass)() | Calculate mass of the nacelle. |
| [`calculate_nacelle_cost`](#csm.models.CSMBase.calculate_nacelle_cost)() | Calculate cost of the nacelle. |
| [`calculate_hub_system_mass`](#csm.models.CSMBase.calculate_hub_system_mass)() | Calculate mass of hub system. |
| [`calculate_hub_system_cost`](#csm.models.CSMBase.calculate_hub_system_cost)() | Calculate cost of hub system. |
| [`calculate_rotor_mass`](#csm.models.CSMBase.calculate_rotor_mass)() | Calculate mass of the rotor. |
| [`calculate_rotor_cost`](#csm.models.CSMBase.calculate_rotor_cost)() | Calculate cost of the rotor. |
| [`calculate_turbine_mass`](#csm.models.CSMBase.calculate_turbine_mass)() | Calculate mass of the turbine. |
| [`calculate_turbine_cost`](#csm.models.CSMBase.calculate_turbine_cost)() | Calculate cost of the turbine. |

# Model Helpers

The following properties and methods are made available for either convenience or performing underlying checks on the
data.

| Attributes/Methods | Description |
| ------------------ | ----------- |
| [`rotor_radius`](#csm.models.CSMBase.rotor_radius) | Half of the rotor diameter. |
| [`swept_area`](#csm.models.CSMBase.swept_area) | Rotor swept area. |
| [`output_names`](#csm.models.CSMBase.output_names) | The names of all attributes available as outputs. |
| [`get_dependent_attributes`](#csm.models.CSMBase.get_dependent_attributes)(name) | Names of all attributes dependent on `name`. |
| [`get_descendant_attributes`](#csm.models.CSMBase.get_descendant_attributes)(name) | Names of all attributes `name` depends on. |
| [`_get_attr_map`](#csm.models.CSMBase._get_attr_map)(both_as_separate, include_units) | Mapping of all the inputs and outputs of the model. |
| [`fields`](#csm.models.CSMBase.fields) | Tuple of `attrs.Attribute`s. |
| [`fields_dict`](#csm.models.CSMBase.fields_dict) | Dictionary of `attrs.Attribute`s. |
| [`_has_values`](#csm.models.CSMBase._has_values)(args) | Checks for the existence of a non-None value. |
| [`_validate_inputs`](#csm.models.CSMBase._validate_inputs)(parameters) | Validates the required attributes for a component's calculation and runs any uncalculated dependent calculations. |
| [`_prepare_calculation`](#csm.models.CSMBase._prepare_calculation) | Verifies the attribute isn't already calculated and validates its dependencies. |
