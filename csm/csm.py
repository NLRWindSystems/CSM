import types
import typing
import inspect
import warnings
import itertools
from numbers import Number
from pathlib import Path
from collections import OrderedDict
from collections.abc import Generator

import attrs
import numpy as np
import pandas as pd

from csm import io, util


def get_parameter_calculation_order(
    function_args_unordered: dict[str, list[str]],
    params_input: set,
) -> OrderedDict:
    """Many of the functions in a cost and scaling model will most likely refer to other functions. For example consider the following equations:

        swept_area = pi * rotor_radius**2
        rotor_radius = rotor_diameter / 2

    In this example, rotor_diameter is the only variable that is not defined by an expression, so it must be an input.
    Given a rotor_diameter we can calculate the rotor_radius directly, but we cannot calculate swept_area until the rotor_radius has been calculated.

    The functions in a cost and scaling model can be defined in any order, this function will re-order them so they can be calculated in one iteration of a loop.

    In the event that recursive function definitions are found, this should raise an error. For example:

        rotor_radius = rotor_diameter / 2
        rotor_diameter = rotor_radius * 2

    Each of the above functions depend on the other and so neither can ever be calculated.

    This could be achieved more optimally by using a dependency tree, however this approach is 'good enough'.
    It could also be achieved with a recursive approach, but that may require safeguards against infinite recursion.

    Args:
        function_args_unordered (dict[str, list[str]]): dict of function argument names keyed by function names
        params_input (set): input parameters to the model, which are not defined by a function

    Raises:
        RecursionError: if recursively defined functions are found

    Returns:
        OrderedDict: input function args, but ordered by when they should be calculated to reduce repeated calculations
    """

    # Populate the ordered list of functions and arguments with functions that are calculated only using input parameters (or those which have no parameters)
    # Simultaneously remove those parameters from the unordered dict
    function_args_ordered = OrderedDict(
        {
            k: function_args_unordered.pop(k)
            for k in tuple(function_args_unordered.keys())
            if not bool(set(function_args_unordered[k]).difference(params_input))
        }
    )

    # Repeatedly iterate over the unordered functions (while there are still any in the dict) removing them from the dict as we place then in an appropriate order
    while bool(function_args_unordered):
        update_made = False  # flag to check if anything changes over an iteration of the dict, to avoid infinitely looping due to recursively defined functions

        # params which we can use as inputs. Any function with all args in this set is calculatable
        known_params = params_input.union(function_args_ordered.keys())

        # Create a separate tuple from the function dict keys since we are modifying the dict as we loop over it
        for name in tuple(function_args_unordered.keys()):
            # Check if all the input kwargs to the function are in the known params
            if not bool(set(function_args_unordered[name]).difference(known_params)):
                # Add the unorderd function to the ordered dict and remove it from the unordered dict
                function_args_ordered[name] = function_args_unordered.pop(name)
                update_made = True

        # If we do a full loop over the remaining unordered functions without any changes being made, it is likely there is a recursive function definition
        if not update_made:
            raise RecursionError(
                f"Check if the any of the following parameters are recursively defined:\n\t{', '.join(function_args_unordered.keys()):s}"
            )

    return function_args_ordered


@attrs.define
class CSM:
    name = attrs.field(type=str)  # name of the model
    dir_model = attrs.field(
        default=Path(io.DIR_MODEL_DEFAULT), converter=Path
    )  # directory where the file containing the model functions is saved

    module = attrs.field(
        type=types.ModuleType, init=False
    )  # module object containing model functions
    functions = attrs.field(
        type=dict[str, typing.Callable], init=False
    )  # model function callable objects
    parameters = attrs.field(
        type=set[str], init=False
    )  # all parameters to the model, whether inputs or outputs
    inputs = attrs.field(type=set[str], init=False)  # input parameters to the model
    outputs = attrs.field(type=set[str], init=False)  # output parameters to the model
    function_args = attrs.field(
        type=dict[str, set], init=False
    )  # named arguments to each function, keyed by the function name

    def __attrs_post_init__(self):
        self.module = util.import_model(self.name, self.dir_model)
        self.functions = dict(inspect.getmembers(self.module, inspect.isfunction))

        function_args_unordered = {
            name: inspect.getfullargspec(func).args
            for name, func in self.functions.items()
        }
        self.parameters = set(
            itertools.chain(
                *function_args_unordered.values(), function_args_unordered.keys()
            )
        )
        self.inputs = self.parameters.difference(function_args_unordered.keys())
        self.outputs = self.parameters.difference(self.inputs)

        # Ordered dict containing{function_name: function_arguments} pairs ordered such that each can be calculated from a single loop of the dict
        self.function_args = get_parameter_calculation_order(
            function_args_unordered=function_args_unordered,
            params_input=self.inputs,
        )

    def __repr__(self) -> str:
        return f"{self.__class__.__name__:s}({self.name:s})"

    def get_inputs(self):
        return sorted(self.inputs)

    def get_outputs(self):
        return sorted(self.outputs)

    @classmethod
    def get_available_models(
        cls,
        dir_models=Path(io.DIR_MODEL_DEFAULT),
    ) -> list[str]:
        return sorted(p.stem for p in dir_models.glob("[!__]*[!__].py"))

    def generate_required_inputs_to_calculate(
        self, param_name: str
    ) -> Generator[str, None, None]:
        """For a given parameter, generate all the input paramers that are required to calculate it.
        Does not return intermediate parameters, only inputs

        Args:
            param_name (str): name of parameter to find inputs for

        Yields:
            Generator[str, None, None]: names of parameters required to calculate the input param
        """
        for a in self.function_args[param_name]:
            if a in self.function_args.keys():
                yield from self.generate_required_inputs_to_calculate(a)
            else:
                yield a

    def required_inputs_to_calculate(self, param_name: str) -> list[str]:
        """Returns a sorted list from the generator generate_required_inputs_to_calculate

        Args:
            param_name (str): name of parameter to find inputs for

        Raises:
            KeyError: if parameter is not defined by a function in the model

        Returns:
            list[str]: ordered list of dependent parameters
        """
        if param_name in self.inputs:
            return [param_name]
        if param_name not in self.function_args.keys():
            raise KeyError(f"{param_name:s} is not a parameter of {self.name:s}.")
        return sorted(self.generate_required_inputs_to_calculate(param_name))

    def display_parameter_function(self, param_name: str) -> None:
        """Display the function that defines a parameter

        Args:
            param_name (str): name of parameter

        Raises:
            KeyError: if no function exists for the parameter
        """
        if param_name in self.inputs:
            print(f"{param_name:s} is an input to {self.name:s}.")

        param_func = self.functions.get(param_name)
        if param_func is None:
            raise KeyError(f"{param_name:s} is not a parameter of {self.name:s}.")
        else:
            print(f"{inspect.getsource(param_func):s}")

    def calculate_parameter(
        self,
        param_to_calculate: str,
        **known_kwargs: dict[str, Number | np.ndarray],
    ) -> Number | np.ndarray | pd.DataFrame:
        """Calcualte a parameter given certain inputs to the model
        If the function for that parameter depends on intermediate parameter values that are not known,
        the functions for those intermediate parameters are called recursively using their required inputs.
        This function works with both scalar values and numpy arrays. When using numpy arrays, the model
        functions are vectorized before being executed.

        Args:
            param_to_calculate (str): parameter to be calculated

        Raises:
            KeyError: if the requested parameter does not exist, or if a required input parameter has not been provided

        Returns:
            Number | np.ndarray | pd.DataFrame: result returned from the appropriate CSM function
        """

        # If the requested parameter is already provided as an input, simpy return the provided value
        if param_to_calculate in known_kwargs.keys():
            return known_kwargs[param_to_calculate]

        # Raise exception if requested parameter does not exist
        if param_to_calculate not in self.parameters:
            raise KeyError(
                f"{param_to_calculate:s} is not a parameter in model {self.name:s}"
            )

        # Raise exception if a required input for the requested parameter does not exist
        if (
            param_to_calculate in self.inputs
            and param_to_calculate not in known_kwargs.keys()
        ):
            raise KeyError(
                f"{param_to_calculate:s} is a required input for model {self.name:s}"
            )

        # Get the values of the required inputs to the requested parameter function by recursively
        # calling this function
        required_kwargs = {
            a: self.calculate_parameter(a, **known_kwargs)
            for a in self.function_args[param_to_calculate]
        }

        # At this point no more recursion is required and the parameter can be calculated
        func = self.functions[param_to_calculate]

        # Check to see if any of the inputs are numpy arrays, in which case the parameter fuction
        # can be vectorized
        is_vectorized = any(isinstance(v, np.ndarray) for v in required_kwargs.values())
        if is_vectorized:
            func = np.vectorize(func)

        # Call the function to calculate the parameter
        result = func(**required_kwargs)

        return result

    def calculate_all_parameters(
        self,
        param_data: pd.DataFrame | dict,
    ) -> io.csm_result_type:
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
            input_param_names = set(param_data.columns)
        elif isinstance(param_data, dict):
            input_param_names = set(param_data.keys())

        # Check if any of the required inputs are missing
        missing_inputs = self.inputs.difference(input_param_names)
        if bool(missing_inputs):
            raise KeyError(
                f"{self.name:s}: the following required inputs or functions are missing:\n\t{', '.join(missing_inputs)}"
            )

        # Flag if any unnecessary inputs have been included in the data
        unnecessary_inputs = (
            set(input_param_names).difference(self.inputs).difference({"scenario"})
        )
        if bool(unnecessary_inputs):
            warnings.warn(
                f"The following inputs have been provided to the {self.name:s} model but are not required:\n\t{', '.join(unnecessary_inputs):s}"
            )

        # Dict to hold the dataframe outputs of the model
        param_data_df = dict()

        # The model parameters were already pre-ordered when initializing the class instance such that
        # we can calclate each output parmeter by looping through the ordered dict only once
        for func_name, func_args in self.function_args.items():
            # Callable function object for the parameter
            func = self.functions[func_name]

            # Check the type annotations from the CSM function to determine if the return type is a dataframe
            # If the function does return a dataframe but does not have this type hint it will generate an error
            func_return_dataframe = (
                getattr(func, "__annotations__", {}).get("return") is pd.DataFrame
            )

            # Get the kwarg inputs to the function depending on whether the inputs are vectors or scalars
            if isinstance(param_data, pd.DataFrame):
                func_kwargs = {p: param_data[p].values for p in func_args}
            else:
                func_kwargs = {p: param_data[p] for p in func_args}

            if func_return_dataframe and isinstance(param_data, pd.DataFrame):
                # Handle the case where the input parameters are vectors and the return type is a dataframe
                # The outputs will need to be combined into a dataframe that is larger than the input
                result_multi: map | itertools.repeat
                if bool(func_args):
                    result_multi = map(
                        lambda r: func(**r),
                        param_data[func_args].to_dict(orient="records"),
                    )  # relatively slow calculation
                else:
                    # Handle special case where the inputs are vectorized but a function returning a dataframe takes no arguments
                    result_multi = itertools.repeat(func(), len(param_data.index))

                func_result = pd.concat(
                    result_multi,
                    keys=param_data.index,
                )
            else:
                # Perform the calculation to get the parameter value
                func_result = self.calculate_parameter(func_name, **func_kwargs)

            # Append the result to the input dict or dataframe if the output type is not a dataframe, otherwise store it in the dataframe output dict
            if func_return_dataframe:
                param_data_df[func_name] = func_result
            else:
                param_data[func_name] = func_result

        if isinstance(param_data, pd.DataFrame):
            # Sort columns in alphabetical order to make finding things easier.
            param_data = param_data.sort_index(axis=1)

        return param_data, param_data_df
