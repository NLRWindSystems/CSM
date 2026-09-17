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
| [`get_transport_results`](#csm.models.CSMBase.get_transport_results)() | Retrieve a dictionary of calculated transport cost attributes. |
| [`get_component_breakdown`](#csm.models.CSMBase.get_component_breakdown)() | Create a component-indexed data frame of mass and cost values. |
| [`irs_mpc_breakdown`](#csm.models.CSMBase.irs_mpc_breakdown)(turbine_production_cost, tower_flange_material_cost, tower_flange_production_cost) | Calculate the base cost breakdown of the US IRS manufactured product component tables. |
| [`total_domestic_content`](#csm.models.CSMBase.total_domestic_content)(turbine_production_cost, tower_flange_material_cost, tower_flange_production_cost, domestic) | Calculates the total, valid domestic content production percentage |
| [`update`](#csm.models.CSMBase.update)(data) | Update model values based on a data dictionary and reset any calculated values dependent on the attributes. |
| [`reset_values`](#csm.models.CSMBase.reset_values)(args) | Reset attribute(s) back to their model default. |

## Model Helpers

The following properties and methods are made available for either convenience or performing underlying checks on the
data.

| Attributes/Methods | Description |
| ------------------ | ----------- |
| [`rated_power_mw`](#csm.models.CSMBase.rated_power) | Turbine nameplate capacity, in :math:`MW`. |
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
