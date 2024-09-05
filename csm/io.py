import typing
import operator
import itertools
from pathlib import Path
from collections.abc import Generator

import yaml
import pandas as pd

from csm import util


DIR_MODEL_DEFAULT = "./csm/model"
DIR_OUTPUT_DEFAULT = "./output"
PATH_CONFIG_DEFAULT = "./input/config.yaml"
CSM_RESULT_TYPE = tuple[pd.DataFrame, dict[str, pd.DataFrame]]


def read_config_file(
    path_config: Path,
) -> dict:
    return yaml.safe_load(open(path_config))


def create_input_parameter_scenarios(
    config: dict,
) -> Generator[dict[str, typing.Any], None, None]:
    """Read parameters defined in the config into a generator of dicts containing kwargs to the model(s)
    Different scenarios can be defined as dicts within the input, and all possible combinations of parameter values
    will be run for each scenario. More nested parameter definitions will override less nested ones

    Yields:
        Generator[dict[str, typing.Any], None, None]: generator of invividual scenario parameter kwargs
    """

    if (parameter_inputs := config.get("parameters")) is None:
        raise KeyError("Must specify parameters in the configuration file.")

    parameter_inputs = util.expand_dict_of_dicts(parameter_inputs)
    parameter_inputs = map(util.expand_dict_of_lists, parameter_inputs)
    parameter_inputs = itertools.chain(*parameter_inputs)

    # Check each set of parameters for to ensure it has a model
    for pi in parameter_inputs:
        if pi.get("model") is None:
            raise KeyError(f"Must specify a model: {str(pi)}")
        yield pi


def read_model_input(
    config: dict,
) -> Generator[tuple[str, pd.DataFrame], None, None]:
    """Read an input config and turn it into a generator of parameter scenario dataframes for each model

    Args:
        config (dict): dict containing parmeter input values

    Raises:
        KeyError: flag when a model has not been specified for each input scenario

    Yields:
        Generator[tuple[str, pd.DataFrame], None, None]: generator of (model_name, input_parameters) model inputs
    """

    # The input dicts can theoreticaly appear in any order
    # We need to organise them into groups based on which model they are using, defined by the name of the model
    # which must appear in the dict

    # In order to use itertools.groupby to organize the dicts into groups, we first must sort them based on the model key
    model_getter = operator.itemgetter("model")
    param_input = sorted(
        create_input_parameter_scenarios(config),
        key=model_getter,
    )

    param_input_grouped = itertools.groupby(param_input, key=model_getter)

    for model_name, param_input_model in param_input_grouped:
        # Handle inputs with no specified model
        if model_name is None:
            raise KeyError("All inputs must indicate which model should be used.")

        # Create dataframe of model input parameters
        param_input_model = (
            pd.DataFrame(param_input_model)
            .drop(columns="model")
            .rename_axis("scenario_number", axis=0)
            .rename_axis("parameter", axis=1)
        )
        yield model_name, param_input_model


def generate_output_excel(
    model_name: str,
    model_output: CSM_RESULT_TYPE,
    output_dir: Path,
) -> Generator[Path, None, None]:
    """Saves CSM output to excel, in case it is needed.

    Args:
        model_name (str): name of model. used for filename
        model_output (CSM_RESULT_TYPE): results from model
        output_dir (Path): directory to save the output files

    Yields:
        Generator[Path, None, None]: path to saved excel file
    """

    parameter_output, parameter_dataframe_output = model_output

    path_excel_output = output_dir / (model_name + ".xlsx")
    with pd.ExcelWriter(path_excel_output) as ew:
        parameter_output.to_excel(ew, sheet_name=model_name)
        for k, v in parameter_dataframe_output.items():
            v.to_excel(ew, sheet_name=k, merge_cells=False)

    yield path_excel_output
