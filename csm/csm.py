import typing
import inspect
import warnings
import itertools
from pathlib import Path
from collections import OrderedDict
from collections.abc import Generator

import attrs
import pandas as pd

from csm import io, util


@attrs.define
class CSM:
    _functions = attrs.field(type=dict[str, typing.Callable], factory=dict)
    _function_args = attrs.field(type=dict[str, list[str]], factory=OrderedDict)
    _name = attrs.field(type=str, init=False)
    _inputs = attrs.field(type=tuple[str, ...], factory=tuple, init=False)

    def __attrs_post_init__(self):
        self._name = self.__class__.__name__

        self._functions = self._get_functions()
        self._populate_function_args(tuple(self._functions.keys()))

        # Inputs to the model are parameters that appear in a function argument but are not defined by a function
        self._inputs = tuple(
            set(itertools.chain.from_iterable(self._function_args.values())).difference(
                self._function_args.keys()
            )
        )

    def __repr__(self) -> str:
        return f"{__class__.__name__:s}({self._name:s})"  # type: ignore

    @classmethod
    def get_available_models(
        cls,
        dir_models: str | Path = io.DIR_MODEL_DEFAULT,
    ) -> dict[str, type]:
        """Scan the model directory looking for files that contain CSM classes

        Args:
            dir_models (str | Path, optional): directory that contains .py files with CSM models. Defaults to io.DIR_MODEL_DEFAULT.

        Returns:
            dict[str, type[typing.Self]]: dict of all uninstantiated CSM models that were found, keyed by their name
        """
        models = {}
        # Check all non-dunder .py files
        module_paths = Path(dir_models).glob("[!__]*[!__].py")
        for p in module_paths:
            module = util.import_module(p)
            for name, obj in inspect.getmembers(module):
                if inspect.isclass(obj) and obj.__module__ == module.__name__:
                    if issubclass(obj, CSM):
                        models[name] = obj

        return models

    @classmethod
    def from_name(
        cls,
        model_name: str,
        dir_model: str | Path = io.DIR_MODEL_DEFAULT,
    ) -> typing.Self:
        """Generate an instance of a CSM subclass by finding and creating it based on the name of the model

        Args:
            model_name (str): name of CSM model
            dir_model (str | Path, optional): directory to look for models. Defaults to io.DIR_MODEL_DEFAULT.

        Raises:
            FileNotFoundError: if model file cannot be found

        Returns:
            typing.Self: instance of named model
        """
        available_models = cls.get_available_models(dir_models=dir_model)
        if (model := available_models.get(model_name)) is None:
            raise FileNotFoundError(
                f"Cannot find CSM with name: {model_name:s}. Available models are: {', '.join(available_models)}"
            )
        return model()

    def get_inputs(self) -> tuple[str, ...]:
        """Get all the input parameters for a model, i.e. all the parameters that are needed to calculate every output

        Returns:
            tuple[str, ...]: tuple of input parameter names sorted alphabetically
        """
        return tuple(sorted(self._inputs))

    def get_outputs(self) -> tuple[str, ...]:
        """Get all the output parameters from the model. If all the inputs are known, each one of these outputs can be calculated

        Returns:
            tuple[str, ...]: sorted tuple of output parameter names, sorted in the most efficienct calculation order
        """
        return tuple(self._function_args.keys())

    def get_name(self) -> str:
        return self._name

    def is_calculable_with_inputs(
        self,
        param_to_calculate: str,
        params_known: typing.Iterable[str],
    ) -> bool:
        """Determine whether a given parameter is calculable given a sequence of known parameter names
        If the parameter is defined by a function, recursively checks if those functions are calculable

        The reason this function cannot simply rely on the required_inputs_to_calculate function is because
        that function returns only the base inputs required to calculate a function, whereas there is no
        reason a user shouldn't be able to provide intermediate calculation steps as well.

        Args:
            param_to_calculate (str): name of parameter to calculate
            params_known (typing.Sequence[str]): sequence of parameter names which are assumed to be known

        Returns:
            bool: whether or not the parameter is calculable given the inputs
        """
        if param_to_calculate in self._function_args.keys():
            # Get all the arguments that will need to be calculated (that are not already known)
            args = set(self._function_args[param_to_calculate]).difference(params_known)

            # Check the calculatability of all required unknown arguments, if all are calculable then the
            # parameter itself is calculable
            return all(
                self.is_calculable_with_inputs(a, params_known=params_known)
                for a in args
            )
        else:
            # If the parameter is not defined by a function, then it is only 'calculable' if it is already known
            return param_to_calculate in params_known

    def _generate_required_inputs_to_calculate(
        self, param_name: str
    ) -> Generator[str, None, None]:
        """For a given parameter, generate all the input paramers that are required to calculate it.
        Does not return intermediate parameters, only inputs

        Args:
            param_name (str): name of parameter to find inputs for

        Yields:
            Generator[str, None, None]: names of parameters required to calculate the input param
        """
        for a in self._function_args[param_name]:
            if a in self._function_args.keys():
                yield from self._generate_required_inputs_to_calculate(a)
            else:
                yield a

    def required_inputs_to_calculate(self, param_name: str) -> list[str]:
        """Returns a sorted list from the generator _generate_required_inputs_to_calculate

        Args:
            param_name (str): name of parameter to find inputs for

        Raises:
            KeyError: if parameter is not defined by a function in the model

        Returns:
            list[str]: ordered list of dependent parameters
        """
        if param_name in self._inputs:
            return [param_name]
        if param_name not in self._function_args.keys():
            raise KeyError(f"{param_name:s} is not a parameter of {self._name:s}.")
        return sorted(set(self._generate_required_inputs_to_calculate(param_name)))

    def display_function(self, param_name: str) -> None:
        """Display the function that defines a parameter

        Args:
            param_name (str): name of parameter

        Raises:
            KeyError: if no function exists for the parameter name
        """

        param_func = self._functions.get(param_name)
        if param_func is None:
            raise KeyError(f"{param_name:s} is not a function in {self._name:s}.")
        else:
            print(f"{inspect.getsource(param_func):s}")

    def _get_functions(self) -> dict[str, typing.Callable]:
        """Extract all the function objects in the CSM class that are part of the model itself
        (as opposed to CSM class methods or helper functions)

        Raises:
            ValueError: If no functions in the CSM are found

        Returns:
            dict[str, typing.Callable]: dict of function object keyed by function name
        """

        model_functions = dict()
        # difference between the set of instance attrs and base class attrs should be the model functions
        for attr_name in set(dir(self)).difference(dir(CSM)):
            attr_obj = getattr(self.__class__, attr_name)
            if callable(attr_obj):
                model_functions[attr_name] = attr_obj

        if len(model_functions) == 0:
            raise ValueError(f"{self._name:s}: no functions found.")

        model_functions = dict(sorted(model_functions.items()))
        return model_functions

    def _populate_function_args(
        self,
        function_names: tuple[str, ...],
        funcs_checked: set | None = None,
    ) -> None:
        """Iterate through the functions in the model and place the names of the function args in an ordered dict.
        When non-input arguments that are not themselves defined are identified, these are added to the ordered dict
        first recursively so that at the end of the process, the function args will be ordered such that a single iteration
        over the ordered functions will allow all the model output parameters to be calculated without repeating
        intermediate calculation steps.

        Args:
            function_names (tuple[str, ...]): names of functions to get args for
            funcs_checked (set | None, optional): set of functions where definitions have already been attempted. Defaults to None.

        Raises:
            RecursionError: If attempting to define a parameter more than once, it may be because of a recursive relationship
        """

        # initialize an empty set keeping track of which parameters have already been attempted to get args for
        if funcs_checked is None:
            funcs_checked = set()

        for func_name in function_names:
            # Only attempt to get args for functions that do not already have args
            # This check must be inside the loop since self._function_args is modified in the loop
            if func_name not in self._function_args.keys() and hasattr(self, func_name):
                # If we are attempting to get args for a parameter that we have already attempted to get args for,
                # that should occur if there are recursively defined functions
                if func_name in funcs_checked:
                    raise RecursionError(
                        f"Check if the following parameter is defined recursively: {func_name:s}"
                    )

                # If we have not already checked this function name, add it to the set of checked functions
                funcs_checked.add(func_name)

                # Extract the actual arguments themsevles
                func_args = inspect.getfullargspec(getattr(self, func_name)).args

                # Get a tuple of which arguments are not already defined and thus require definition
                func_args_requiring_definition = tuple(
                    a
                    for a in func_args
                    # check if the argument is itself defined by a function
                    if a in self._functions.keys()
                    # check if the argument has already been added to the function args dict
                    and a not in self._function_args.keys()
                )

                # Recursively call this function to define the arguments as required
                if func_args_requiring_definition:
                    self._populate_function_args(
                        func_args_requiring_definition,
                        funcs_checked,
                    )

                # At this point all the arguments to the function themselves have defined arguments (or are inputs)
                # We can add the function and it's arguments to the _function_args ordered dict
                self._function_args[func_name] = func_args

    def calculate(
        self,
        param_to_calculate: str,
        params_input: dict[str, typing.Any] | None = None,
        **params_input_kwargs: dict[str, typing.Any],
    ) -> typing.Any | pd.DataFrame:
        """Calculate a single parameter

        Args:
            param_to_calculate (str): name of parameter to calculate
            params_input (dict[str, typing.Any] | None, optional): inputs used to calculate parameter. Defaults to None.
            **params_input_kwargs (dict[str, typing.Any]): kwargs form of params_input

        Raises:
            KeyError: if the parameter to calculate is not and input and not defined by a function,
            or if any required arguments are missing

        Returns:
            typing.Any | pd.DataFrame: the value of the parameter calculated by the function(s) in the CSM
        """

        if params_input is None:
            params_input = params_input_kwargs

        # If the requested parameter is already provided as an input, simply return the provided value
        if param_to_calculate in params_input.keys():
            return params_input[param_to_calculate]

        # Raise exception if requested parameter does not exist
        if param_to_calculate not in self._function_args.keys():
            raise KeyError(
                f"{param_to_calculate:s} is not defined by a function in model {self._name:s}"
            )

        # Get the values of the required inputs to the requested parameter function by recursively
        # calling this function
        required_kwargs = {
            a: self.calculate(a, params_input)
            for a in self._function_args[param_to_calculate]
        }

        # At this point no more recursion is required and the parameter can be calculated
        func = self._functions[param_to_calculate]

        # Perform the actual calculation
        result = func(**required_kwargs)

        return result

    def calculate_all(
        self,
        params_input: dict[str, typing.Any] | None = None,
        **params_input_kwargs: dict[str, typing.Any],
    ) -> dict[str, typing.Any]:
        """When calculating all the parameters in a model, simply looping over each one and recursively calculating it will
        result in intermediate parameters being calculated multiple times unnecessarily.
        This function will calculate each parameter while retaining those intermediate calculation steps.
        Any parameters that cannot be calculated due to missing inputs will silently be skipped.

        Args:
            params_input (dict[str, typing.Any] | None, optional): input parameter values. Defaults to None.
            **params_input_kwargs: (dict[str, typing.Any]): kwargs form of params_input

        Returns:
            io.CSM_RESULT_TYPE: results from the model, with the scalar results stored in a dict and the dataframe results
            stored in dict, keyed by
        """

        if params_input is None:
            params_input = params_input_kwargs

        params_output = params_input.copy()

        available_inputs = set(params_output.keys())

        # Flag if any unnecessary inputs have been included in the data
        unnecessary_inputs = available_inputs.difference(self._inputs)

        if bool(unnecessary_inputs):
            warnings.warn(
                f"The following inputs have been provided to {self._name:s} but are not required:\n\t{', '.join(unnecessary_inputs):s}"
            )

        # Filter the list of parameters that will be calculated to only include those which are calculable given the inputs
        funcs_to_calculate = (
            func_name
            for func_name in self._function_args.keys()
            if self.is_calculable_with_inputs(func_name, available_inputs)
        )

        # The model parameters were already pre-ordered when initializing the class instance such that
        # we can calculate each output parmeter by looping through the ordered dict only once
        for func_name in funcs_to_calculate:
            params_output[func_name] = self.calculate(func_name, params_output)

        return params_output
