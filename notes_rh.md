# CSM Feedback

## General

- Just be sure to adhere to expected Python standards for naming conventions like the following:
  - classes: `MyClassName`, excepting one-offs where capitalization is preferred like `CSMBase`
  - constants: `MY_CONSTANT`
  - basically everything else Python: `my_attribute`, except one-offs where you might prefer
    capitalization like `turbine_AEP`
- You could turn off mypy until you settle on your form or when you do commits
  `SKIP=mypy git commit -m "message"` until you're ready to add type hinting
- Or, Type hinting is nice, but not required, so if you're not up to it just yet, feel free to get
  rid of it altogether.
- In code type checking should be done with `isinstance(val, type)` like `isinstance(cls, CSM)`
- The typical way to parameterize an unknown set of keyword arguments is through `**kwargs` and
  then document how `**kwargs` is used in the docstring.

## CSMBase

- Should there be a standard set of inputs to this?
- If no to the above this is a niche class type called a mixin class that has no inputs, but exists
  purely to provide a common set of methods to other classes that will inherit it. The only thing to
  do is signal that it's a mixin by changing the name to `CSMMixin` or anything that ends in `Mixin`.
- Regardless, I think this should live in a new module under `csm/model/` called `base.py` or
  something else that signals common methods/classes/etc. might live there.

## CSM

- I think I have a more fundamental question around the use case. Is this designed to be such that
  given whatever inputs are provided, the allowable methods will then all be run? Or, is this
  designed around running all the methods, and the user has to then provide the required inputs?
- I'm not following what the `__new__` method is for
- Good use of class methods.
- It seems like you have `get_inputs`, which returns all inputs, but your description in `main.py`
  describes this as the required inputs, I just wanted to be sure it's not the latter because I'd
  change the name to indicate that if it is.
- `calculate_parameter`
  - It's not too important, but `np.vectorize` is just a list comprehension under the hood, so I
    might recommend that all model methods are actually built such that they can be vectorized by
    default, which they seem to be anyway. This is where some unit tests could come in handy to
    ensure methods can arbitrarily take scalar or numpy arrays and return the expected results for
    either.
- Much of this class feels like it's a base model class that provides the boilerplate helper
  methods. Or, this even feels like it could be separated into a base model and user interface code
  (the interface should just keep the same name)
- `calculate_all_parameters`
  - I might think about adopting a `run` method in place of this that can take parameter data as a
    dictionary or dataframe, and have a `which` (or similarly named) flag where a parameter name can
    be passed, then a `**kwargs` to pass in the known data. If not (totally fine if you disagree
    here) have a `run` and `run_single`. My thoughts on the naming convention stem mostly from the
    fact that it's more conventional, but it's also fine to disagree here since the existing
    convention is clearly stating what's happening.
  - I'm curious why there are different formats to the potential calculation because the models all
    look like they return a single value numpy array if vectorized.
  - This method seems like it gets a bit complex because it has to properly sort the model's methods
    and inputs to ensure everything that's needed is available. For me, this solidifies the fact
    there should be a base model class with a standard set of inputs and have all the appropriate
    results stored in `model._parameter` that can be retrieved if it's already been calculated and a
    value hasn't been passed. Something like the following:

    ```python
    class Emprical2024(CSMMixin, CSMBase)
        _hub_mass = attrs.field(init=False, default=None)
        def hub_mass(blade_mass: Number | np.ndarray | None):
            if blade_mass is None:
                if self.hub_mass is not None:
                    return self._hub_mass
                return ValueError("`blade_mass` is a required input if hub_mass has not already been calculated.")
            return 3.46 * blade_mass - 25451.58
    ```

    I think this might be a bit more to create a new model, but it's ultimately easier to manage
    inputs and results. On top of that, it's providing the error messages about missing inputs at
    the model source, which is a bit more straightforward.

## `utils.py`

- file handling and checking should be in `io.py`

## `run.py`

- This feels like good interface type code that could be part of `CSM`
  - `get_parameter_config` could then be a load function
  - `run_parameter_config` could be a class method for just running a configuration without
    instantiating the class, but the use of `yield` is unclear to me.
  - `generate_model_result` could be something like `run_models`, though I'm still not sold on the
    usage of `yield`. One consideration would to just concatenate all the resulting data frames
    into a single resulting dataframe.