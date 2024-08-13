import inspect
import itertools
import numpy as np
import pandas as pd
import warnings
import inspect
import types
from collections import OrderedDict

class CostAndScalingModel:

    def __init__(self, csm_module: types.ModuleType):

        # Module containng cms functions
        self.module = csm_module

        # Name of the CSM which corresponds to the name of the .py file containing the model equations
        self.name = csm_module.__name__.split(".")[-1]

        # Some CSM functions return a table with multiple rows for each input row.
        # These need to be returned as separate dataframes and are stored in this dict, keyed by the function name
        self.multi_ouputs = dict()

        # dict containing the CSM functions
        self.functions = dict(inspect.getmembers(csm_module, inspect.isfunction))

        # CSM function arguments
        function_args_unordered = {
            n: set(getattr(f, "_args", inspect.getfullargspec(f).args))
            for n, f in self.functions.items()
            }

        # All the parameters relevant to the model, whether inputs or outputs
        self.parameters_all = set(itertools.chain(*function_args_unordered.values()))

        # Any parameters that are not defined by a function must be provided as inputs for the model
        self.parameter_inputs = self.parameters_all.difference(function_args_unordered.keys())

        # Any parameters that are not inputs are outputs
        self.parameter_outputs = self.parameters_all.difference(self.parameter_inputs)

        # Ordered dict containing {function_name: function_arguments} pairs ordered such that each can be calculated from a single loop of the dict
        self.function_args = self.get_parameter_calculation_order(function_args_unordered)


    def get_parameter_calculation_order(self, function_args_unordered: dict) -> OrderedDict:
        """Many of the functions in a cost and scaling model will most likely refer to other functions. For example consider the following equations:

            rotor_radius = rotor_diameter / 2
            swept_area = pi * rotor_radius**2

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
            function_args_unordered (dict): unordered function arguments

        Returns:
            OrderedDict: function arguments ordered by when they should be calculated
        """
        
        # Populate the ordered list of functions and arguments with functions that are calculated only using input parameters (or those which have no parameters)
        # Simultaneously remove those parameters from the unordered dict
        function_args_ordered = OrderedDict({
            k: function_args_unordered.pop(k)
            for k in tuple(function_args_unordered.keys())
            if len(function_args_unordered[k].difference(self.parameter_inputs)) == 0
        })

        # Repeatedly iterate over the unordered functions (while there are still any in the dict) removing them from the dict as we place then in an appropriate order
        while bool(function_args_unordered):

            update_made = False  # flag to check if anything changes over an iteration of the dict, to avoid infinitely looping due to recursively defined functions

            # params which we can use as inputs. Any function with all args in this set is calculatable
            known_params = self.parameter_inputs.union(function_args_ordered.keys())

            # Create a separate tuple from the function dict keys since we are modifying the dict as we loop over it
            for name in tuple(function_args_unordered.keys()):

                # Check if all the input kwargs to the function are in the known params
                if len(function_args_unordered[name].difference(known_params)) == 0:

                    # Add the unorderd function to the ordered dict and remove it from the unordered dict
                    function_args_ordered[name] = function_args_unordered.pop(name)
                    update_made = True
            
            # If we do a full loop over the remaining unordered functions without any changes being made, it is likely there is a recursive function definition
            if not update_made:
                raise RecursionError(f"Check if the any of the following parameters are recursively defined:\n\t{", ".join(function_args_unordered.keys()):s}")
        
        return function_args_ordered



    def calculate_output_parameters(self, param_data: pd.DataFrame) -> tuple:
        """Using a dataframe of parameter inputs and the equations of the model, return all parameter outputs in a dataframe
        This runs all input parameter scenarios for a given model simultaneously

        Args:
            param_data (pd.DataFrame): input parameters

        Returns:
            tuple: tuple with two elements:
                1. dataframe of scalar model outputs (along with model inputs)
                2. dict of more complex table outputs from model
        """

        # Check if any of the required inputs are missing
        missing_inputs = self.parameter_inputs.difference(param_data.columns)
        if bool(missing_inputs):
            raise KeyError(
                f"{self.name:s}: the following required inputs or functions are missing:\n\t{", ".join(missing_inputs)}"
            )
        
        # Flag if any unnecessary inputs have been included in the data
        unnecessary_inputs = set(param_data.columns).difference(self.parameter_inputs).difference({"scenario"})
        if bool(unnecessary_inputs):
            warnings.warn(f"The following inputs have been provided to the {self.name:s} model but are not required:\n\t{", ".join(unnecessary_inputs):s}")


        # The list of parameters to calculate was already pre-ordered so we can calclate each parmeter by looping through the ordered dict only once
        for func_name, func_args in self.function_args.items():

            func = self.functions[func_name]
            
            func_args = list(func_args)

            if hasattr(func, "_args"):
                # Functions returing a table of values for each parameter scenario place that table in the multi_outputs dict
                self.multi_ouputs[func_name] = func(param_data[func_args])

            else:
                # Functions returning a single row per scenario can be vectorized so will be fast
                param_data[func_name] = np.vectorize(func)(
                    **dict(
                        zip(
                            func_args,
                            param_data[func_args].values.T,
                        )
                    )
                )

        # Remove any parameters that have been marked for exclusion
        columns_to_drop = list(name for name, func in self.functions.items() if getattr(func, "_exclude", False))
        if bool(columns_to_drop):
            param_data = param_data.drop(columns=columns_to_drop)

            
        # Sort columns in alphabetical order to make finding things easier.
        param_data = param_data.sort_index(axis=1)

        return param_data, self.multi_ouputs


