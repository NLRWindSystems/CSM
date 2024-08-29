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
        return f"{__class__.__name__:s}({self.__class__.__name__:s})"  # type: ignore

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
    ) -> None:
        """Iterate through the functions in the model and place the names of the function args in an ordered dict
        When non-input arguments that are not themselves defined are identified, these are added to the ordered dict
        first recursively so that at the end of the process, the function args will be ordered such that a single iteration
        over the ordered functions will allow all the model output parameters to be calculated without repeating
        intermediate calculation steps

        Args:
            function_names (tuple[str, ...] | KeysView): names of functions to get args for
        """
        for func_name in function_names:
            if func_name not in self._function_args.keys():
                if hasattr(self, func_name):
                    func_args = inspect.getfullargspec(getattr(self, func_name)).args

                    func_args_requiring_definition = tuple(
                        a
                        for a in func_args
                        # check if function exists for the argument
                        if a in self._functions.keys()
                        # check if the argument has already been added to the function args
                        and a not in self._function_args.keys()
                    )
                    if func_args_requiring_definition:
                        self._populate_function_args(func_args_requiring_definition)

                    self._function_args[func_name] = func_args

    def __new__(cls, *args, **kwargs) -> typing.Self:
        """Prevent instantiation of the base class"""
        if type(cls) is CSM:
            raise TypeError(f"Cannot directly instantiate the {cls.__name__:s} class.")
        return object.__new__(cls, *args, **kwargs)

    @classmethod
    def get_available_models(
        cls,
        dir_models: str | Path = io.DIR_MODEL_DEFAULT,
    ) -> list[str]:
        """Generate a sorted list of available models to use

        Args:
            dir_models (str | Path, optional): directory to search for models. Defaults to io.DIR_MODEL_DEFAULT.

        Returns:
            list[str]: sorted list of model names
        """
        return sorted(p.stem for p in Path(dir_models).glob("[!__]*[!__].py"))

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
        if model_name not in available_models:
            raise FileNotFoundError(
                f"Cannot find {model_name:s}. Available models are: {', '.join(available_models)}"
            )
        model = util.import_model(model_name, dir_model)
        return model()

    def get_inputs(self) -> list[str]:
        return sorted(self._inputs)

    def get_outputs(self) -> list[str]:
        return sorted(self._outputs)

    def get_name(self) -> str:
        return self._name

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
        for a in self._function_args[param_name]:
            if a in self._function_args.keys():
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
        if param_name in self._inputs:
            return [param_name]
        if param_name not in self._function_args.keys():
            raise KeyError(f"{param_name:s} is not a parameter of {self._name:s}.")
        return sorted(self.generate_required_inputs_to_calculate(param_name))

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
        if param_to_calculate not in self._parameters:
            raise KeyError(
                f"{param_to_calculate:s} is not a parameter in model {self._name:s}"
            )

        # Raise exception if a required input for the requested parameter does not exist
        if (
            param_to_calculate in self._inputs
            and param_to_calculate not in known_kwargs.keys()
        ):
            raise KeyError(
                f"{param_to_calculate:s} is a required input for model {self._name:s}"
            )

        # Get the values of the required inputs to the requested parameter function by recursively
        # calling this function
        required_kwargs = {
            a: self.calculate_parameter(a, **known_kwargs)
            for a in self._function_args[param_to_calculate]
        }

        # At this point no more recursion is required and the parameter can be calculated
        func = self._functions[param_to_calculate]

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
        missing_inputs = self._inputs.difference(input_param_names)
        if bool(missing_inputs):
            raise KeyError(
                f"{self._name:s}: the following required inputs or functions are missing:\n\t{', '.join(missing_inputs)}"
            )

        # Flag if any unnecessary inputs have been included in the data
        unnecessary_inputs = (
            set(input_param_names).difference(self._inputs).difference({"scenario"})
        )
        if bool(unnecessary_inputs):
            warnings.warn(
                f"The following inputs have been provided to the {self._name:s} model but are not required:\n\t{', '.join(unnecessary_inputs):s}"
            )

        # Dict to hold the dataframe outputs of the model
        param_data_df = dict()

        # The model parameters were already pre-ordered when initializing the class instance such that
        # we can calclate each output parmeter by looping through the ordered dict only once
        for func_name, func_args in self._function_args.items():
            # Callable function object for the parameter
            func = self._functions[func_name]

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


class CSMBase(CSM):
    """Base CSM class containing functions that will apply to every cost and scaling model"""

    def rotor_angular_velocity_max(tip_speed_max, rotor_radius):  # type: ignore
        return tip_speed_max / rotor_radius  # type: ignore

    def rotor_angular_velocity_max_rpm(rotor_angular_velocity_max):  # type: ignore
        return rotor_angular_velocity_max / (2.0 * np.pi) * 60.0  # type: ignore

    def rotor_torque_max(
        turbine_rating, rotor_efficiency_max, rotor_angular_velocity_max
    ):  # type: ignore
        return (turbine_rating / rotor_efficiency_max) / (rotor_angular_velocity_max)  # type: ignore

    def rotor_radius(rotor_diameter):  # type: ignore
        return rotor_diameter / 2.0  # type: ignore

    def swept_area(rotor_radius):  # type: ignore
        return np.pi * rotor_radius**2  # type: ignore
