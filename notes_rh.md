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

# Feedback 9/9/2024

## General

- The offshore and onshore models should just be split. I assume the relationships won't ultimately
  be compatible.
- `io.py` should be renamed because the Python standard library includes a package called `io`, so
  importing the CSM version writes over its namespace when imported. I think most of it would fit
  in `csm/csm.py` just fine as well.
- Be careful with how long the comments are in some places. Generally aim to be succinct. I'd also
  avoid breaking up list/dict/etc. comprehensions with comments because it makes the code harder to
  read. Keep the line lengths consistent with the code line lengths as well, it's much easier to
  read that way.
- I'd aim for avoiding abbreviations for things like `param` to keep things explicit.
- When working with `Path` objects, just be sure to do `Path(<input>).resolve()` when initializing
- `dict` objects should be initialized with `x = {}`, not `x = dict()`. This comes more of
  an accepted best practice within Python vs anything substantively wrong. It's just generally best
  to avoid instantiating a dictionary, or even list, with `dict(<input>)` vs `{"key": "value"}
  unless it's something like `x = dict(zip(list1, list2))`, which is then the appropriate way.
- `dict_of_dicts` is more commonly `nested_dict`
- I'm still curious about the use of yield, is there a reason you're creating the dictionaries
  from generators? It's just not that common of a use case, so I'm just curious.
- Is there a reason why only Python 3.12+ is supported? It'd be good to at least include 3.11 as
  well if it's possible. Relatedly, the ruff target version should reflect the minimum supported
  version.

## CSM

- I don't think I'm following the self._name logic, what exactly is this doing? Is it pulling the
  model's name?
- `CSM.from_name()` seems like it should be the main model creation hook where
  `model_name` and `model_dir` are the two expected inputs. If using an included model, then
  `model_dir` could be `None`.
- `self._function_args.keys()` is used a lot, couldn't `self._functions` be used in its place?
- `_get_functions` should probably be `_get_model_functions`.
- In `calculate()`, I might use the arguments `parameter`, `inputs`, and `**kwargs` because they're
  shorter and a more standard naming convention (at least with `**kwargs`).

## util.py

- `expand_dict_of_dicts`
  - Will the underscore connection in bringing nested levels up (`upstream_key + "_" + k`) cause
    issues later if there is an underscore in the parameter name already?

  ### you are right in that it won't be possible to reverse-engineer the nested structure from the result, but for this use case it doesn't really bother me. I don't think it will cause problems

- The `np.linspace` call could just be `dict_of_lists[k] = np.linspace(*v[0], v[1]), but i might also
  be being picky about this. You might also need a check that the start and stop are in the correct
  order.
- Something that would be helpful when creating the docstrings for these functions is to provide
  a somewhat basic example to show what the input and output should look like. In general, without 
  seeing an example these are pretty abstract (totally fine) so they're a bit hard to follow.

## run.py

- `get_parameter_config` should be `read_config` or `load_config` instead of get since this is
  primarily intended to be a file reading method. This method probably fits nicely in csm.py as well.
- `run_parameter_config` could also just be `run` and be csm.py as a means to run without using the
  `CSM` class. This is also seems a bit redundant with `CSM.calculate_all()`.
- In `create_input_parameter_scenarios`, `pi` threw me off, so I'd either stick with the generic
  `el` or use something more specific like `parameter` (not `input` since that's an actual method).
  In the f-string, `f"{str(pi)}"` is redundant and can just be `f"{pi}"`
