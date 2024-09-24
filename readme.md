# Cost and Scaling Model (CSM)

The purpose of the cost and scaling model is to approximate the relationships between
the size and cost of various major wind turbine components. These relationships can be
used to approximate the impact that changes in design or technology might have on the
turbine as a whole.

For example, putting in a larger blade should increase the energy generation from the
turbine. However, doing so may also require a larger gearbox, rotor, etc. and it may be
the case that the increased cost of these larger components outweighs the benefit of the
larger blade.

Each individual cost and scaling model is represented by a class, where the functions
that make up the model are defined inside the class. For example, consider the following
model:

```python
import math
class CSMExample:
    def rotor_radius(rotor_diameter):
        return rotor_diameter / 2.0
    def rotor_swept_area(rotor_radius):
        return math.pi * rotor_radius**2
```

Here we have a function called `rotor_radius` and another function `rotor_swept_area`
that takes an argument (also called `rotor_radius`). These names must align for the
model to recognize that in order to calculate `rotor_swept_area` from a known
`rotor_diameter` input, it must first calculate `rotor_radius` as an intermediate step.

This example represents a model that has 3 parameters, `rotor_diameter`, `rotor_radius`
and `rotor_swept_area`. Of these parameters, `rotor_diameter` is an input to the model
(because it is not defined by a function with the same name) and the others are outputs
(because they are defined by functions). If the `rotor_diameter` is known, we can
calculate all the other parameters of the model. Alternatively, if we know the
`rotor_radius`, we can calculate the `rotor_swept_area` directly without knowing the
`rotor_diameter`.

These classes are not called directly, instead the `CSM` class will find and use these
models based a model name provided by the user. This repository includes some sample
models based on curve fits of a variety of different industry datasets, and can be found
in `csm/model` (this is the default location to look for models). These models should be
viewed as 'rule of thumb' estimates only and care should be taken when extrapolating
beyond the range of the original curve fits. These models are also not a substitute for
a detailed design, but rather should be used to explore general trends between different
turbine components.

It is possible for the user to define their own models, and these models can contain any
functions that are required (they don't have to involve wind turbines at all). As long
as the function names and argument names align, the `CSM` module should be able to
figure out the relationships between all the parmeters.

## Using the Provided Models

If you are only interested in using the default models included in this repository,
check out the [example](example/csm_example.ipynb) for basic usage.

Continue reading if you want to either:
- run many inputs simultaneously to sweep over a range of parameter values
- define your own model


## Inputs

In more advanced use cases, there are two areas requiring user input; the configuration
file and model definitions. Neither is required to start using the included models, but
they will allow more control over the results.

### Configuration File

The configuration file contains basic settings required to run the cost and scaling
model(s) as well as the parameter values that should be tested for each model. It is
convenient when you want to run lots of different parameter input scenarios and handle
their outputs.

The parameter values to test are defined in the `parameters` section of the
configuration file and can be specified in a number of ways:
- a scalar value indicates a single value to test (e.g. `hub_height: 150`)
- a list indicated a number of options to test (e.g. `hub_height: [120, 150, 160, 180]`)
- an input following the format `[[start, end], count]` will create `count` evenly
  spaced values between `start` and `end`

When lists are used to specify multiple parameters, every possible combination of these
parameters will be tested. Testing multiple values over many different parameters can
generate a very large number of input parameter scenarios. In order to reduce this, you
can split these scenarios up into arbitrarily named groups. For example:
```yaml
hub_height: [120, 150]
small:
    turbine_rating_MW: [4.2, 5.6]
    rotor_diameter: [136, 150]
large:
    turbine_rating_MW: [6.2, 7.2]
    rotor_diameter: [6.2, 7.2]
```

The parameter options inside the `small` and `large` scenarios are treated separately.
All possible combinations of parameters are generated within each scenario but not
between scenarios. The `hub_height` values are defined outside these named scenarios so
they apply to both. You can create as many scenarios as you want and they can be as
nested as you want. The only exception to this is you cannot give a scenario the same
name as a model input (e.g. `rotor_diameter`). It is possible to re-define parameter
values inside a scenario that are also defined outside. In these cases, the more nested
value is preferentially chosen.

Finally, each different parameter scenario must contain a `model` value with the name of
the cost and scaling model the parameters should apply to. These models are detailed
below.

The `run_config` method is used to run all the parameter combinations in a config file.
It also handles model outputs that are dataframes by appropriately adding an index level
to indicate which parameter combination each row corresponds to.

By default, the configuration file is found at `/input/config.yaml`. When using the
default config file, this is as simple as:

```python
from csm import run_config
result = run_config()
```

If an output file format and directory is specified, files will be saved at that location and `run_config` will return the paths to those files. Otherwise the resulting dataframes themselves are returned.

### Model Definition

As briefly outlined above, cost and scaling models are defined by a number of equations
that approximate relationships between turbine components based on real-life or modelled
data. For example, perhaps after analyzing industry data there is a power law
relationship between the rotor radius of a turbine and the mass of blade. We can capture
this relationship by defining a function.

```python
def blade_mass(rotor_radius):
    return 9.2157 * rotor_radius**1.7679
```

Once we have a blade mass, we can use another simple relationship to model the blade
cost.

```python
def blade_cost(blade_mass):
    return 15.9432 * blade_mass
```

From these two equations is is clear that `blade_cost` can be estimated using
`rotor_radius` by first calculating `blade_mass` as an intermediate step. This is what
the cost and scaling model does, it calculates all the model equations based on the
input parameter values defined in the configuration file.

In order to determine how all these functions relate to each other, it is important that
the function and argument names are consistent. For example, if you instead define the
`blade_cost` function as:

```python
def blade_cost(blade_mass_kg):
    return 15.9432 * blade_mass_kg
```

The model will complain because it isn't smart enough to recognize that `blade_mass` is
equivalent to `blade_mass_kg`.

This also means that all the input arguments must be explicity named. For example, a
function such as:

```python
def turbine_mass(nacelle_mass, tower_mass, rotor_mass):
    return nacelle_mass + tower_mass + rotor_mass
```

Cannot be shortened to:

```python
def turbine_mass(*args)
    return sum(args)
```

Also, it is important to avoid recursively defined functions, for example:

```python
def rotor_radius(rotor_diameter):
    return rotor_diameter / 2
def rotor_diameter(rotor_radius):
    return rotor_radius * 2
```

In this case, the model will never be able to calculate either parameter because both
are defined in terms of each other.

There is no reason the outputs from model functions have to be scalars. They can be more
complex objects depending on the application. For example, you may want information on
the size and mass of the different sections of a wind turbine tower. The number of
sections might depend on the height of the tower, meaning the tower section sizes and
masses will vary in size depending on the input parameters and it may be most suitable
to return this as a dataframe.

## Output

The model(s) can return different types of output depending on what options are
specified in the configuration file. Currently, the results can be saved as an excel
file or not saved at all and simply returned as dataframes.
