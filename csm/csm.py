from . import util

import inspect
import itertools
import numpy as np
import pandas as pd
import warnings
import inspect
import types
from collections import OrderedDict
import itertools
from pathlib import Path

class CostAndScalingModel:

    def __init__(
            self,
            csm_module: types.ModuleType | str,
            dir_module: Path | str | None = None,
        ):

        # If the input is a string, assume it is the name of a model
        if isinstance(csm_module, str):
            csm_module = util.get_csm_module(
                csm_module,
                dir_module,
                )

        # Module containng csm functions
        self.module = csm_module

        # Name of the CSM which corresponds to the name of the .py file containing the model equations
        self.name = csm_module.__name__.split(".")[-1]

        # dict containing the CSM functions keyed by their name
        self.functions = dict(inspect.getmembers(csm_module, inspect.isfunction))

        # dict containing CSM function arguments keyed by the function name
        function_args_unordered = {
            n: tuple(getattr(f, "_args", inspect.getfullargspec(f).args))
            for n, f in self.functions.items()
            }

        # All the parameters relevant to the model, whether inputs or outputs
        self.parameters_all = set(itertools.chain(*function_args_unordered.values()))

        # Any parameters that are not defined by a function must be provided as inputs
        self.parameter_inputs = self.parameters_all.difference(function_args_unordered.keys())

        # Any parameters that are not inputs are outputs
        self.parameter_outputs = self.parameters_all.difference(self.parameter_inputs)

        # Ordered dict containing{function_name: function_arguments} pairs ordered such that each can be calculated from a single loop of the dict
        self.function_args = self.get_parameter_calculation_order(function_args_unordered)

    def get_parameter_inputs(self):
        return self.parameter_inputs

    def generate_required_params(self, param_name: str):

        for a in self.function_args[param_name]:

            if a in self.function_args:
                yield from self.generate_required_params(a)
            else:
                yield a


    def required_inputs_to_calculate(self, param_name: str):

        if param_name not in self.function_args.keys():
            return set()
        else:
            return set(self.generate_required_params(param_name))
        

    def calculate_single_param(
            self,
            param_to_calculate: str,
            **known_args,
    ):
        
        required_args = self.required_inputs_to_calculate(param_to_calculate)
        missing_args = required_args.difference(known_args.keys())
        if bool(missing_args):
            raise KeyError(f"The following parameters are required to calculate {param_to_calculate:s}:\n\t{", ".join(missing_args)}")

        if param_to_calculate in known_args.keys():
            return known_args[param_to_calculate]
        
        else:
            return self.functions[param_to_calculate](**{
                a: self.calculate_single_param(a, **known_args)
                for a in self.function_args[param_to_calculate]
            })


    def calculate_all_params(self, param_data):

        if isinstance(param_data, pd.DataFrame):
            input_param_names = param_data.columns
        elif isinstance(param_data, dict):
            input_param_names = set(param_data.keys())
        else:
            raise SyntaxError("input_data must be a dict (scalar) or DataFrame (vectorized).")
        
        # Check if any of the required inputs are missing
        missing_inputs = self.parameter_inputs.difference(input_param_names)
        if bool(missing_inputs):
            raise KeyError(
                f"{self.name:s}: the following required inputs or functions are missing:\n\t{", ".join(missing_inputs)}"
            )
        
        # Flag if any unnecessary inputs have been included in the data
        unnecessary_inputs = set(input_param_names).difference(self.parameter_inputs).difference({"scenario"})
        if bool(unnecessary_inputs):
            warnings.warn(f"The following inputs have been provided to the {self.name:s} model but are not required:\n\t{", ".join(unnecessary_inputs):s}")

        param_data_multi = dict()

        # The list of parameters to calculate was already pre-ordered so we can calclate each parmeter by looping through the ordered dict only once
        for func_name, func_args in self.function_args.items():

            func = self.functions[func_name]
            
            func_args = list(func_args)
            func_is_multi = func_name.startswith("multi_")

            if isinstance(param_data, pd.DataFrame):
                if func_is_multi:
                # Functions returing a table of values for each parameter scenario place that table in the multi_outputs dict

                    result_multi = param_data[func_args].to_dict(orient="records")
                    result_multi = map(lambda r: func(**r), param_data[func_args].to_dict(orient="records"))
                    result_multi = pd.concat(result_multi, keys=param_data.index)
                    param_data_multi[func_name] = result_multi

                else:
                    # Functions returning a single row per scenario can be vectorized so will be fast
                    if isinstance(param_data, pd.DataFrame):
                        param_data[func_name] = np.vectorize(func)(
                            **dict(
                                zip(
                                    func_args,
                                    param_data[func_args].values.T,
                                )
                            )
                        )
            else:
                result_scalar = func(**{p: param_data[p] for p in func_args})
                if func_is_multi:
                    param_data_multi[func_name] = result_scalar
                else:
                    param_data[func_name] = result_scalar

        # Remove any parameters that have been marked for exclusion
        params_to_exclude = list(name for name, func in self.functions.items() if getattr(func, "_exclude", False))
        if bool(params_to_exclude):
            if isinstance(param_data, pd.DataFrame):
                param_data = param_data.drop(columns=params_to_exclude)
            else:
                for p in params_to_exclude:
                    del param_data[p]

        
        if isinstance(param_data, pd.DataFrame):
            # Sort columns in alphabetical order to make finding things easier.
            param_data = param_data.sort_index(axis=1)

        return param_data, param_data_multi

        

    def display_categorized_params(self):
        
        param_input = self.parameter_inputs
        param_output = set(self.function_args.keys()).difference(itertools.chain.from_iterable(self.function_args.values()))
        param_intermediate = self.parameter_outputs.difference(param_input)

        param_input = sorted(param_input)
        param_intermediate = sorted(param_intermediate)
        param_output = sorted(param_output)

        params = (param_input, param_intermediate, param_output)
        column_width = max(map(lambda p: max(map(len, p)), params))
        params = tuple(map(
            lambda p: tuple(map(lambda pi: pi.ljust(column_width), p)),
            params,
            ))

        csep = "\t"
        rsep = "\n"
        header = csep.join(map(lambda s: s.ljust(column_width), ("Input", "Intermediate", "Output")))
        border = "="*len(header.expandtabs())
        num_rows = max(map(len, params))

        content = itertools.zip_longest(itertools.repeat(csep, num_rows), *params, fillvalue=" "*column_width)
        content = tuple(content)
        content = rsep.join(map(lambda c: "{1:s}{0:s}{2:s}{0:s}{3:s}".format(*c), content))
        table = rsep.join((header, border, content, border))

        print(table)


    def get_parameter_calculation_order(self, function_args_unordered: dict) -> OrderedDict:
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
            function_args_unordered (dict): unordered function arguments

        Returns:
            OrderedDict: function arguments ordered by when they should be calculated
        """
        
        # Populate the ordered list of functions and arguments with functions that are calculated only using input parameters (or those which have no parameters)
        # Simultaneously remove those parameters from the unordered dict
        function_args_ordered = OrderedDict({
            k: function_args_unordered.pop(k)
            for k in tuple(function_args_unordered.keys())
            if len(set(function_args_unordered[k]).difference(self.parameter_inputs)) == 0
        })

        # Repeatedly iterate over the unordered functions (while there are still any in the dict) removing them from the dict as we place then in an appropriate order
        while bool(function_args_unordered):

            update_made = False  # flag to check if anything changes over an iteration of the dict, to avoid infinitely looping due to recursively defined functions

            # params which we can use as inputs. Any function with all args in this set is calculatable
            known_params = self.parameter_inputs.union(function_args_ordered.keys())

            # Create a separate tuple from the function dict keys since we are modifying the dict as we loop over it
            for name in tuple(function_args_unordered.keys()):

                # Check if all the input kwargs to the function are in the known params
                if len(set(function_args_unordered[name]).difference(known_params)) == 0:

                    # Add the unorderd function to the ordered dict and remove it from the unordered dict
                    function_args_ordered[name] = function_args_unordered.pop(name)
                    update_made = True
            
            # If we do a full loop over the remaining unordered functions without any changes being made, it is likely there is a recursive function definition
            if not update_made:
                raise RecursionError(f"Check if the any of the following parameters are recursively defined:\n\t{", ".join(function_args_unordered.keys()):s}")
        
        return function_args_ordered
