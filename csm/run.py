from pathlib import Path
from collections.abc import Generator
from tqdm import tqdm
import pandas as pd
import operator
import itertools
import typing

from csm import csm, util

# default location to look for configuration file
PATH_CONFIG_DEFAULT = "./input/config.yaml"
# return type of model outputs including the name of the model
CSM_RESULT_TYPE = tuple[pd.DataFrame, dict[str, pd.DataFrame]]
# When handling results from multiple different models, it is convenient to place them
# in a tuple along with the name of the model
MODEL_RESULT_TYPE = tuple[str, CSM_RESULT_TYPE]


def load_config(
    config: str | Path | dict = Path(PATH_CONFIG_DEFAULT),
) -> dict:
    """Read an input parameter configuration dict for running model parameter scenarios.
    Input can either be a configuration dict already (in which case nothing is changed),
    or a path to a yaml file specifying the configs

    Args:
        config (str | Path | dict, optional): configuration dict or path to yaml file.
            Defaults to Path(PATH_CONFIG_DEFAULT).

    Returns:
        dict: dict of config options
    """
    if isinstance(config, str):
        config = Path(config).resolve()
    if isinstance(config, Path):
        util.check_file_exists(config)
        config = util.read_config_file(config)
    return config


def run_config(
    config: str | Path | dict = PATH_CONFIG_DEFAULT,
) -> tuple[MODEL_RESULT_TYPE, ...] | tuple[Path, ...]:
    """Run all parameter combinations of all models specified by a parameter
    configuration

    Args:
        config (str | Path | dict, optional): config dict (or path to it). Defaults to
            PATH_CONFIG_DEFAULT.

    Returns:
        tuple[MODEL_RESULT_TYPE, ...] | tuple[Path, ...]: if no output filetype is
            specified, return the model results themselves. Otherwise return the paths
            to the output files
    """

    config_dict = load_config(config)

    model_directory = config_dict.get("model_directory", csm.DIR_MODEL_DEFAULT)
    model_directory = Path(model_directory).resolve()

    model_input = tuple(generate_model_parameter_inputs(config_dict))
    model_result = calculate_model_results(model_input, model_directory=model_directory)
    model_output = create_model_output(model_result, config_dict)

    return model_output


def generate_input_parameter_scenarios(
    config: dict,
) -> Generator[dict[str, typing.Any], None, None]:
    """Read parameters defined in the config into a generator of dicts containing kwargs
    to the model(s). Different scenarios can be defined as dicts within the input, and
    all possible combinations of parameter values will be run for each scenario.
    More nested parameter definitions will override less nested ones

    Yields:
        Generator[dict[str, typing.Any], None, None]: generator of invividual scenario
            parameter values
    """

    if (parameter_inputs := config.get("parameters")) is None:
        raise KeyError("Must specify parameters in the configuration file.")

    parameter_inputs = util.expand_dict_of_dicts(parameter_inputs)
    parameter_inputs = map(util.expand_dict_of_lists, parameter_inputs)
    parameter_inputs = itertools.chain(*parameter_inputs)

    # Check each set of parameters for to ensure it has a model
    for parameter_input in parameter_inputs:
        if parameter_input.get("model") is None:
            raise KeyError(f"Must specify a model: {str(parameter_input):s}")
        yield parameter_input


def generate_model_parameter_inputs(
    config: dict,
) -> Generator[tuple[str, pd.DataFrame], None, None]:
    """Read an input config and turn it into a generator of parameter scenario
    dataframes for each model

    Args:
        config (dict): dict containing parmeter input values

    Raises:
        KeyError: flag when a model has not been specified for each input scenario

    Yields:
        Generator[tuple[str, pd.DataFrame], None, None]: generator of (model_name,
        input_parameters) model inputs
    """

    # The input dicts can theoreticaly appear in any order We need to organise them into
    # groups based on which model they are using, defined by the name of the model which
    # must appear in the dict

    # In order to use itertools.groupby to organize the dicts into groups, we first must
    # sort them based on the model key
    model_getter = operator.itemgetter("model")
    param_input = sorted(
        generate_input_parameter_scenarios(config),
        key=model_getter,
    )

    param_input_grouped = itertools.groupby(param_input, key=model_getter)

    for model_name, param_input_model in param_input_grouped:

        # Create dataframe of model input parameters
        param_input_model = (
            pd.DataFrame(param_input_model)
            .drop(columns="model")
            .rename_axis("scenario_number", axis=0)
            .rename_axis("parameter", axis=1)
        )
        yield model_name, param_input_model


def calculate_model_result(
    model_name: str,
    parameter_input: pd.DataFrame,
    model_directory: Path,
) -> MODEL_RESULT_TYPE:
    """Calculate the results from a single model based on a dataframe of parameter
    inputs

    Args:
        model_name (str): name of CSM model parameter_input (pd.DataFrame): dataframe of
            parameter input scenarios
        model_directory (Path): directory to search for models

    Returns:
        MODEL_RESULT_TYPE: calculated model results
    """

    model = csm.CSM.from_name(model_name, model_directory)

    # Remove the scenario column from the module inputs since it is not a parameter in
    # the model
    model_args = parameter_input.drop(columns="scenario")

    # Handle the unlikely event that there is a parameter dataframe no inputs
    if model_args.empty:
        result_calculate = map(model.calculate_all, [{}] * len(parameter_input.index))
    else:
        _, result_iter = zip(*model_args.apply(pd.Series.to_dict, axis=1).items())
        result_calculate = map(model.calculate_all, result_iter)

    result_unprocessed = tuple(
        tqdm(result_calculate, desc=model_name, total=len(parameter_input.index))
    )

    # Models can produce dataframe (or series) outputs which must be separated into
    # their own dataframes(/series) They will need to be concatenated with the input
    # parameter series as the key so they can be join to the input parameter dataframe

    # Extract the keys of the dataframe/series elements in the first result. Currently
    # all models should return the number and types of output so it is sufficient to
    # check only the first
    keys_dataframe = set(
        k
        for k, v in result_unprocessed[0].items()
        if isinstance(v, (pd.DataFrame, pd.Series))
    )
    result_unprocessed_dataframe = tuple(
        {k: r.pop(k) for k in keys_dataframe} for r in result_unprocessed
    )
    # Assuming all results will have the same keys in the result_df dict
    result_df = {
        k: pd.concat(
            (r[k] for r in result_unprocessed_dataframe), keys=parameter_input.index
        )
        for k in result_unprocessed_dataframe[0].keys()
    }

    result_scalar = pd.DataFrame(result_unprocessed, index=parameter_input.index)

    # Add the scenario column that was previously removed back into the results
    result_scalar.insert(
        loc=0,
        column="scenario",
        value=parameter_input.loc[result_scalar.index, "scenario"],
    )

    return model_name, (result_scalar, result_df)


def calculate_model_results(
    model_inputs: tuple[tuple[str, pd.DataFrame], ...],
    model_directory: Path = Path(csm.DIR_MODEL_DEFAULT),
) -> tuple[MODEL_RESULT_TYPE, ...]:
    """Run each model after the parameter inputs have been organized based on model

    Args:
        model_inputs (tuple[tuple[str, pd.DataFrame], ...]): input model name and
            parameter values to test model_directory (Path): where the csm model files
            are saved

    Returns:
        tuple[MODEL_RESULT_TYPE, ...]: output parameter values for each model
    """
    model_results = tuple(
        calculate_model_result(model_name, parameter_input, model_directory)
        for model_name, parameter_input in model_inputs
    )
    return model_results


def create_model_output(
    model_result: tuple[MODEL_RESULT_TYPE, ...],
    config: dict,
) -> tuple[MODEL_RESULT_TYPE, ...] | tuple[Path, ...]:
    """Create the model output in the specified output format, or return the model
    results directly if not output specified

    Args:
        model_result (tuple[MODEL_RESULT_TYPE, ...]): resutls from models
        config (dict): configuration dict

    Returns:
        tuple[MODEL_RESULT_TYPE, ...] | tuple[Path, ...]: either the model results
        returned directly or the paths to the output files
    """

    # Lookup to get which function should be used to create the output file
    func_create_output_lookup = {
        "excel": util.generate_output_excel,
    }

    if (output_file_type := config.get("output_type", None)) is None:
        # if there is no output file type, simply return the results from the model(s)
        return model_result

    else:
        output_dir = Path(
            config.get("output_directory", csm.DIR_OUTPUT_DEFAULT)
        ).resolve()

        if output_file_type not in func_create_output_lookup.keys():
            raise KeyError(
                (
                    "Invalid output file type: '"
                    f"{output_file_type:s}"
                    "'. Allowable values are "
                    f"{', '.join(func_create_output_lookup.keys())}"
                    " or None"
                ),
            )
        func_create_output = func_create_output_lookup[output_file_type]

        # Call the appropriate function on the model results
        model_output_files = tuple(
            func_create_output(model_name, model_result, output_dir)
            for model_name, model_result in model_result
        )

        # Return the paths to the resulting output files
        return model_output_files
