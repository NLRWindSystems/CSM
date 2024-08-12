# Cost and Scaling Model

The purpose of the cost and scaling model is to estimate cost and scaling relationships for wind turbine components. For example, putting in a larger blade should increase the energy generation from the turbine. However, it may also require a larger gearbox, yaw system, nacelle etc. and it may be the case that the increased cost of these larger components outweighs the benefit of the larger blade. The purpose of this module is to attempt to model the relationships between these different turbine components.

## Inputs

There are two areas requiring user input to use this tool; the configuration file and model definitions.

### Configuration File

The configuration file contains basic settings required to run the cost and scaling model(s) as well as the parameter values that should be tested for each model. These are defined in the `parameters` section and can be specified in a number of ways:
- a scalar value indicates a single value to test (e.g. `hub_height: 150`)
- a list indicated a number of options to test (e.g. `hub_height: [120, 150, 160, 180]`)
- an input following the format `[[start, end], count]` will create `count` evenly spaced values between `start` and `end`

When lists are used to specify multiple parameters, every possible combination of these parameters will be tested. Testing multiple values over many different parameters can generate a very large number of input parameter scenarios. In order to reduce this, you can split these scenarios up into arbitrarily named groups. For example:
```
hub_height: [120, 150]
small:
    turbine_rating_MW: [4.2, 5.6]
    rotor_diameter: [136, 150]
large:
    turbine_rating_MW: [6.2, 7.2]
    rotor_diameter: [6.2, 7.2]
```

The parameter options inside the `small` and `large` scenarios are treated separately. All possible combinations of parameters are generated within each scenario but not between scenarios. The `hub_height` values are defined outside these named scenarios so they apply to both. You can create as many scenarios as you want and they can be as nested as you want. The only exception to this is you cannot give a scenario the same name as a model input (e.g. `rotor_diameter`). It is possible (although not recommended) to re-define parameter values inside a scenario that are also defined outside. In these cases, the more nested value is preferentially chosen.

Finally, each different parameter scenario must contain a `model` value with the name of the cost and scaling model the parameters should apply to. These models are detailed below.

By default the configuration file should be saved at `./input/config.yaml`.

### Model Definitions

Cost and scaling models are defined by a number of equations that approximate relationships between turbine components based on real-life or modelled data. For example, perhaps after analyzing industry data there is a power law relationship between the rotor radius of a turbine and the mass of blade. We can capture this relationship by defining a function.
```
def blade_mass(rotor_radius):
    return 9.2157 * rotor_radius**1.7679
```

Once we have a blade mass, we can use another simple relationship to model the blade cost.

```
def blade_cost(blade_mass):
    return 15.9432 * blade_mass
```

From these two equations is is clear that `blade_cost` can be estimated using `rotor_radius` by first calculating `blade_mass` as an intermediate step. This is what the cost and scaling model does, it calculates all the model equations based on the input parameter values defined in the configuration file.

In order to determine how all these functions relate to each other, it is important that the function and argument names are consistent. For example, if you instead defined the `blade_cost` function as:

```
def blade_cost(blade_mass_kg):
    return 15.9432 * blade_mass_kg
```

The model will complain because it isn't smart enough to recognize that `blade_mass` is equivalent to `blade_mass_kg`.

It is important to avoid recursively defined functions, for example:

```
def rotor_radius(rotor_diameter):
    return rotor_diameter / 2
def rotor_diameter(rotor_radius):
    return rotor_radius * 2
```

In this case, the model will never be able to calculate either parameter because both are defined in terms of each other.

A cost and scaling model is defined by a `.py` file (by default located in `./csm/model`) that contains all these functions. If you have two similar models that share some functions, you will need two separate files but you can define the shared functions in one and import them into the other. All the relevant functions for the model will need to be defined or imported in the `.py` file, and the name of this `.py` file must match the `model` setting in the configuration file.

All of the parameter inputs for a particular model are organized into a dataframe and their results are calculated simultaneously in a vectorized manner. The exception to this is if the model contains a function that is decorated with `@multi_output`. These functions generate more than one dataframe output row for each single input row. For example, defining details on individual turbine tower sections. The number of sections may vary depending on the parameter inputs so this function a variable sized output. This output is saved in a separate dataframe which can be joined to the other parameters using the common `scenario_number` index level.

There is also a `@exclude_output` decorator for functions that provide useful intermediate calculation steps but not useful outputs.

## Output

The model(s) can return a few different types of output depending on what options are specified in the configuration file. Currently, the results can be saved as a sqlite file, as input spreadsheets for LandBOSSE, or not saved at all and simply returned as dataframes.