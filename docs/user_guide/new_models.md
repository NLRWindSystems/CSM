# Creating a New Model

This guide will walk through the process and considerations for creating a new model by focusing on
creating a new blade mass formulation with new mass relationships, mirroring the
[`Land2020NLR`](#api:land-2020) model.

## Imports and setup

Aside from the base model, we also need to be able to access the actual attribute data provided by
the `attrs` dataclass. This will be useful for simple reuse of existing variables.

```python
from attrs import define, fields

from csm.models import CSMBase
from csm.models.utils import create_field

base = fields(CSMBase)
```

Note that we could also subclass the `Land2015NLR` if we wished to maintain the defaults and
relationships made available there. However, the 2020 model changes nearly all the values and many
relationships, so it is not desirable in this case. Though the 2021 model does subclass the 2020
model as there are comparatively few changes between the two.

### Class creation

Be sure to wrap the class with the `attrs.define` decorator, and subclass the base model or
another existing implementation closely matching the desired relationships.

```python
@define
class CustomModel(CSMBase):
    ...
```

#### Updating the inputs and attributes

For easy reuse of the base model's attributes, we use the `reuse` method to work with the focal
attribute's existing type data, metadata, and conversn and validation routines.

In this example, we are setting default values for `turbine_class` and `blade_has_carbon`. Though
these attributes will be unused by `CustomModel`, a value is required for certain helper
methods for the class in addition to encoding the expected information for posterity (including 0).
However, for `blade_has_carbon` and `turbine_class`, we also set the `init=False` to prohibit users
from setting this value without raising an error. For this case, it's not necessary as it won't be
used, so is purely for demonstration. We must also create a new attribute `blade_mass_exp`. Note
that `units="unitless"` and `io_type="input"` are the defaults.

Both attributes `units` and `io_type` are essential for WISDEM integration. As such, `units` should
align with
[OpenMDAO-compatible units](https://openmdao.org/newdocs/versions/latest/features/units.htm). The
`io_type` should be "input" for values required to be set by a user or are provided as model
defaults, "output" for values only able to be calculated, and "both" for calculated values that can
be overridden with user inputs. For further details, refer to the `csm.models.utils.create_field`
documentation.

```python
@define
class CustomModel(CSMBase):
    turbine_class = base.turbine_class.reuse(default=1, init=False)
    blade_has_carbon = base.blade_has_carbon.reuse(default=True, init=False)
    blade_mass_exp = create_field(obj=float, units="unitless", io_type="input", default=9.2157)
```

#### Updating the parameter mapping and post initialization hook

The `parameter_map` defines what each attribute's dependent attributes are, enabling the
streamlined data checking, validation, and value resetting. Without this mapping, updating an
attribute's value will incorrectly clear an upstream calculated value. When creating a wholly new
scaling relationship, i.e., adding new attributes or removing an attribute dependency, it's critical
to update the `parameter_map` to reflect the new relationships.

Below we are updating the `blade_mass` to no longer need the `blade_has_carbon` or `turbine_class`
attributes, and add `blade_mass_exp`. Once the `parameter_map` is updated, the base class' method
can be run `super.__attrs_post_init__()`. The `super` class, aka `CSMBase`, also generates a
dependency graph based on these relationships.

```python
    def __attrs_post_init__(self):
        self.parameter_map["blade_mass"] = ("rotor_diameter", "blade_mass_coeff", "blade_mass_exp")
        super().__attrs_post_init__()
```

#### Defining a new scaling relationship

For the new `calculate_blade_mass` method, the first three lines are used to determine if the focal
variable has already been calculated or provided. If it has, then the calculation should return
early, otherwise the calculation should proceed. This piece of control flow should always occur
first, with only the input to `_prepare_calculation` changing. In this case we use `"blade_mass"`
as that is the attribute being set.

The `calculate_xx` methods should not return a value, instead act as setters for the calculated
value. It is important to adhere to the existing attribute naming conventions to avoid errors at
runtime. Please note, the docstring has not been created in this example, but please follow the
examples set forth in `CSMBase` or any custom models for the information that should be provided.

```python
    def calculate_blade_mass(self):
        exists = self._prepare_calculation("blade_mass")
        if exists:
            return

        self.blade_mass = self.blade_mass_coeff * (self.rotor_diameter / 2) ** self.blade_mass_exp
```

#### Updating results calculations

If a new subsystem scaling relationship is being created that did not exist previously, then the the
following methods will also have to be updated to ensure their values are calculated and mapped
accordingly.

* `calculate_subsystem_mass`
* `calculate_system_mass`
* `calculate_subsystem_cost`
* `calculate_system_cost`
* `results`
* `mass_results`
* `cost_results`

For the `calculate_subsystem_mass` and `calculate_subsystem_cost` methods, if the subsystem will be
a dependent of an upstream subsystem such as with `rotor_torque` being required for `gearbox_mass`
and `brake_mass`, then the method will need to be recreated. If it can be calculated either first
or last, then the following can be done. Simply change the ordering of
`super().calculate_subsystem_mass()` depending on if it should be calculated first or last.

```python
    def calculate_subsystem_mass():
        """Runs all the mass calculations for the non-aggregated turbine subsytems."""
        self.calculate_new_subsystem_mass()
        super().calculate_subsystem_mass()
```

### The full implementation

Below is the full implementation of the `CustomModel` that redefines the `blade_mass` scaling
relationship.

```python
from attrs import define, fields

from csm.models import CSMBase, Land2015NLR
from csm.models.utils import create_field


base = fields(Land2015NLR)


@define
class CustomModel(CSMBase):
    turbine_class = base.turbine_class.reuse(default=1, init=False)
    blade_has_carbon = base.blade_has_carbon.reuse(default=True, init=False)
    blade_mass_coeff = base.blade_mass_coeff.reuse(default=9.2157)
    blade_mass_exp = create_field(
        obj=float, units="unitless", io_type="input", default=1.7679
    )

    def __attrs_post_init__(self):
        # NOTE: we are changing the blade mass calculation's requirements, and
        # need to update the parameter relationships
        self.parameter_map["blade_mass"] = (
            "rotor_diameter", "blade_mass_coeff", "blade_mass_exp"
        )
        super().__attrs_post_init__()

    def calculate_blade_mass(self):
        exists = self._prepare_calculation("blade_mass")
        if exists:
            return

        self.blade_mass = (
            self.blade_mass_coeff * (self.rotor_diameter / 2) ** self.blade_mass_exp
        )
```
