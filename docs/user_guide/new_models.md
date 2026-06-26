# Creating a New Model

This guide will walk through the process and considerations for creating a new model by focusing on
creating a new blade mass formulation with new mass relationships, mirroring the
[`Land2020NLR`](#api:land-2020) model.

## Imports and setup

Aside from the base model , we also need to be able to access the actual attribute data
provided by the `attrs` dataclass. This will be useful for simple reuse of existing
variables

```python
from attrs import define, fields

from csm.models.base_model import CSMBase
from csm.models.utils import create_field

base = fields(CSMBase)
```

### Class creation

Be sure to wrap the class with the `attrs.define` decorator, and subclass the base model or
another existing implementation closely matching the desired relationships.

```python
@define
class CustomModel(CSMBase):
```

#### Updating the inputs and attributes

For easy reuse of the base model's attributes, we `reuse` the focal attribute's existing
type data, metadata, and conversion and validation routines. However, we also want
to ensure users don't change the `blade_has_carbon` attribute, so we set `init=False` to
cause the model to error out on initialization if the user provides a value for it.

In this example, we must also create a new attribute `blade_mass_exp`. It's important to note that
`units="unitless"` and `io_type="input"` are the defaults and the metadata used for making the model
available to WISDEM with `io_type` also helping with data validation. If your custom model is not
intended to be integrated into the codebase, or be used in a WISDEM workflow, `units` may be ignored.
However, when using, be sure to check the documentation for `csm.models.utils.create_field` on their
proper usage. In general, units should align with
[OpenMDAO units](https://openmdao.org/newdocs/versions/latest/features/units.htm) and
`io_type` should be one of "input" (strictly an input), "output" (strictly a calculated value), or
"both" (a calculated value that could be hard-coded as an input, i.e., custom blade mass calculated
outside of CSM).

```python
    turbine_class = base.turbine_class.reuse(default=1)
    blade_has_carbon = base.blade_has_carbon.reuse(default=True, init=False)
    blade_mass_exp = create_field(obj=float, units="unitless", io_type="input", default=9.2157)
```

#### Updating the parameter mapping and post initialization hook

This step is critical as it defines what each attribute's dependent attributes are, enabling the
streamlined data checking and validation. Without this mapping, updating an attribute's value will
incorrectly clear an upstream calculated value. Below we are updating the `blade_mass` to
no longer need the `blade_has_carbon` or `turbine_class` attributes, and add `blade_mass_exp`.
Once the `parameter_map` is updated, the base class' method can be run `super.__attrs_post_init__()`.

```python
    def __attrs_post_init__(self):
        # NOTE: we are changing the blade mass calculation's requirements, and need to
        # update the parameter relationships
        self.parameter_map["blade_mass"] = (
            "rotor_diameter", "blade_mass_coeff", "blade_mass_exp"
        )
        super().__attrs_post_init__()
```

#### Defining the new scaling relationship

Please note, the docstring has not been created in this example, but please follow the examples
set forth in `CSMBase` or any custom models for the information that should be provided.

The first three lines are used to determine if the focal variable has already been calculated or
provided. If it has, then the calculation should return early, otherwise the calculation should
proceed. These method should not return a value, instead act as setters for the calculated
value. It is important to adhere to the existing attribute naming conventions to avoid errors at
runtime.

```python
    def calculate_blade_mass(self):
        exists = self._prepare_calculation("blade_mass")
        if exists:
            return

        self.blade_mass = self.blade_mass_coeff * (self.rotor_diameter / 2) ** self.blade_mass_exp
```

### The full implementation
