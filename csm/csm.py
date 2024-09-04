import typing
import inspect
import numbers
import warnings
import itertools
from pathlib import Path
from collections import OrderedDict
from collections.abc import Generator

import attrs
import numpy as np
import pandas as pd

from csm import io, util


TYPE_PARAM = type[numbers.Number | bool | np.ndarray | pd.Series]


@attrs.define
class CSM:
    _functions = attrs.field(type=dict[str, typing.Callable], factory=dict)
    _function_args = attrs.field(type=dict[str, list[str]], factory=OrderedDict)
    _name = attrs.field(type=str, init=False)
    _parameters = attrs.field(type=set[str], init=False)
    _inputs = attrs.field(type=set[str], init=False)
    _outputs = attrs.field(type=set[str], init=False)

    def __attrs_post_init__(self):
        self._name = self.__class__.__name__

        self._functions = self._get_functions()
        self._populate_function_args(tuple(self._functions.keys()))

        self._parameters = set(
            itertools.chain(*self._function_args.values(), self._function_args.keys())
        )

        self._inputs = self._parameters.difference(self._function_args.keys())
        self._outputs = self._parameters.difference(self._inputs)

    def __repr__(self) -> str:
        return f"{__class__.__name__:s}({self._name:s})"  # type: ignore

    def __new__(cls, *args, **kwargs) -> typing.Self:
        """Prevent instantiation of the base class"""
        if cls is CSM:
            raise TypeError(f"Cannot directly instantiate the {cls.__name__:s} class.")
        return object.__new__(cls, *args, **kwargs)

    @classmethod
    def get_available_models(
        cls,
        dir_models: str | Path = io.DIR_MODEL_DEFAULT,
    ) -> dict[str, type[typing.Self]]:
        models = {}
        module_paths = Path(dir_models).glob("[!__]*[!__].py")
        for p in module_paths:
            module = util.import_module(p)
            for name, obj in inspect.getmembers(module):
                if inspect.isclass(obj) and obj.__module__ == module.__name__:
                    if issubclass(obj, CSM):
                        models[name] = obj

        return models  # type: ignore

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

    def get_inputs(self) -> list[str]:
        """Get all the input parameters for a model, i.e. all the parameters that are needed to calculate every output

        Returns:
            list[str]: sorted list of input parameter names
        """
        return sorted(self._inputs)

    def get_outputs(self) -> list[str]:
        """Get all the output parameters from the model. If all the inputs are known, each one of these outputs can be calculated

        Returns:
            list[str]: sorted list of output parameter names
        """
        return sorted(self._outputs)

    def get_name(self) -> str:
        return self._name

    def is_calculatable_with_inputs(
        self,
        param_to_calculate: str,
        inputs: set[str] | list[str],
    ):
        if param_to_calculate in self._function_args.keys():
            args = set(self._function_args[param_to_calculate]).difference(inputs)
            return all(self.is_calculatable_with_inputs(a, inputs=inputs) for a in args)
        else:
            return param_to_calculate in inputs

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

    def display_parameter_function(self, param_name: str) -> None:
        """Display the function that defines a parameter

        Args:
            param_name (str): name of parameter

        Raises:
            KeyError: if no function exists for the parameter name
        """
        if param_name in self._inputs:
            print(f"{param_name:s} is an input to {self._name:s}.")

        else:
            param_func = self._functions.get(param_name)
            if param_func is None:
                raise KeyError(f"{param_name:s} is not a parameter of {self._name:s}.")
            else:
                print(f"{inspect.getsource(param_func):s}")

    def _get_functions(self) -> dict[str, typing.Callable]:
        """Create dict of all functions in the model

        Returns:
            dict[str, typing.Callable]: function objecs keyed by function name
        """
        model_functions = dict()
        # difference between the set of instance attrs and base class attrs should be the model functions
        for attr_name in set(dir(self)).difference(dir(CSM)):
            attr_obj = getattr(self.__class__, attr_name)
            if callable(attr_obj):
                model_functions[attr_name] = attr_obj

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
        intermediate calculation steps

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

    def calculate_parameter(
        self,
        param_to_calculate: str,
        input_data: dict[str, TYPE_PARAM] | pd.DataFrame | None = None,
        **input_kwargs: dict[str, TYPE_PARAM],
    ) -> TYPE_PARAM | pd.DataFrame | tuple[pd.DataFrame]:
        """Calculate a parameter given certain inputs to the model
        If the function for that parameter depends on intermediate parameter values that are not known,
        the functions for those intermediate parameters are called recursively using their required inputs.
        This function works with both scalar values and numpy arrays. When using numpy arrays, the model
        functions are vectorized before being executed.
        """

        # TODO update docstring. this is the messiest function

        if input_data is None:
            params_known = input_kwargs
        else:
            if bool(input_kwargs):
                raise ValueError(
                    "Must provide the known parameters as a dict/dataframe, or using kwargs, but not both."
                )
            params_known = input_data  # type: ignore

        is_dataframe_input = isinstance(params_known, pd.DataFrame)

        if is_dataframe_input:
            params_known = {c: params_known[c].values for c in params_known.columns}  # type: ignore

        # If the requested parameter is already provided as an input, simply return the provided value
        if param_to_calculate in params_known.keys():
            return params_known[param_to_calculate]

        # Raise exception if requested parameter does not exist
        if param_to_calculate not in self._parameters:
            raise KeyError(
                f"{param_to_calculate:s} is not a parameter in model {self._name:s}"
            )

        # Raise exception if a required input for the requested parameter does not exist
        if (
            param_to_calculate in self._inputs
            and param_to_calculate not in params_known.keys()
        ):
            raise KeyError(
                f"{param_to_calculate:s} is a required input for model {self._name:s}"
            )

        # Get the values of the required inputs to the requested parameter function by recursively
        # calling this function
        required_kwargs = {
            a: self.calculate_parameter(a, params_known)
            for a in self._function_args[param_to_calculate]
        }

        # At this point no more recursion is required and the parameter can be calculated
        func = self._functions[param_to_calculate]

        # Check if any of the function inputs are numpy arrays (or pandas series)
        # If so, the calculation (usually) will be vectorized
        is_vectorized_input = is_dataframe_input or any(
            isinstance(v, np.ndarray) for v in required_kwargs.values()
        )

        # Check if the return type of the function is a dataframe
        is_dataframe_output = (
            getattr(func, "__annotations__", {}).get("return") is pd.DataFrame
        )

        if is_vectorized_input and not is_dataframe_output:
            func = np.vectorize(func)

        if is_vectorized_input and is_dataframe_output:
            if bool(required_kwargs):
                # Handle the scenario where the inputs are vectorized, the output is a dataframe and there is
                # at least one argument to the function
                result_generator = (
                    func(**dict(zip(required_kwargs.keys(), v)))
                    for v in zip(*required_kwargs.values())
                )  # type: ignore
            else:
                # Handle the scenario where the inputs are vectorized, the output is a dataframe but there
                # are not any inputs to the function

                # Get the number of outputs to be produced. We cannot rely on the size of the input args
                # since there aren't any
                if isinstance(params_known, pd.DataFrame):
                    # If the input params are a dataframe the number of expected outputs will be the same
                    # as the number of rows in the input
                    num_outputs = len(params_known.index)
                else:
                    # If the input parameters are a dict of other values (which may or may not be numpy arrays),
                    # check each element to find the longest one
                    num_outputs = max(
                        map(
                            lambda p: len(p) if hasattr(p, "__len__") else 1,
                            params_known.values(),
                        )
                    )
                result_generator = itertools.repeat(func(), num_outputs)  # type: ignore

            # Generate the output result where the input is vectorized and the output is a dataframe
            if is_dataframe_input:
                # If the inputs are provided as a dataframe, return an output dataframe with a multiindex
                # to allow joining back to the inputs
                result = pd.concat(
                    result_generator,
                    keys=input_data.index,  # type: ignore
                )
            else:
                # If the input is not a dataframe, we won't be able to join to the input so simply return
                # a tuple with the appropriate number of output values
                result = tuple(result_generator)
        else:
            result = func(**required_kwargs)

        return result

    def calculate_all_parameters(
        self,
        param_data: pd.DataFrame | dict,
    ) -> io.CSM_RESULT_TYPE:
        """When calculating all the parameters in a model, simply looping over each one and recursively calculating it will
        result in intermediate parameters being calculated multiple times unnecessarily.
        This function will calculate each parameter while retaining those intermediate calculation steps

        Args:
            param_data (pd.DataFrame | dict): input parameters to use, either scalar (dict) or vector (dataframe)

        Raises:
            KeyError: names of any required input parameters that have not been provided

        Returns:
            result_type: tuple containing:
                1. a dict or dataframe with all the input parameters as well as all the calculated output parameters
                2. dict of dataframes that are outputs from the model that generate a result with a bigger size than the input.
                For example, details on the number of tower sections of a turbine. The number of tower sections may depend on
                the hub height and other factors, so will be a variable sized output.
        """

        param_data = param_data.copy()

        # Get the names of the input parameters
        if isinstance(param_data, pd.DataFrame):
            available_inputs = set(param_data.columns)
        else:
            available_inputs = set(param_data.keys())

        # Flag if any unnecessary inputs have been included in the data
        unnecessary_inputs = (
            set(available_inputs).difference(self._inputs).difference({"scenario"})
        )
        if bool(unnecessary_inputs):
            warnings.warn(
                f"The following inputs have been provided to {self._name:s} but are not required:\n\t{', '.join(unnecessary_inputs):s}"
            )

        # Filter the list of parameters that will be calculated to only include those which are calculatable given the inputs
        funcs_to_calculate = (
            func_name
            for func_name in self._function_args.keys()
            if self.is_calculatable_with_inputs(func_name, available_inputs)
        )

        # Dict to hold the dataframe outputs of the model
        param_data_df = dict()

        # The model parameters were already pre-ordered when initializing the class instance such that
        # we can calclate each output parmeter by looping through the ordered dict only once
        # for func_name, func_args in self._function_args.items():
        for func_name in funcs_to_calculate:
            func_result = self.calculate_parameter(func_name, param_data)

            if isinstance(func_result, (pd.DataFrame, tuple)):
                param_data_df[func_name] = func_result
            else:
                param_data[func_name] = func_result

        if isinstance(param_data, pd.DataFrame):
            # Sort columns in alphabetical order to make finding things easier.
            param_data = param_data.sort_index(axis=1)

        return param_data, param_data_df
