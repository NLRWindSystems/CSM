from pathlib import Path
from collections.abc import Generator
from tqdm import tqdm
import pandas as pd

from csm import CSM, io, util


# return type of model outputs including the name of the model
model_result_type = tuple[str, io.CSM_RESULT_TYPE]


def get_parameter_config(
    parameter_config: str | Path | dict = Path(io.PATH_CONFIG_DEFAULT),
) -> dict:
    """Read an input parameter configuration dict for running model parameter scenarios.
    Input can either be a configuration dict already (in which case nothing is changed),
    or a path to a yaml file specifying the configs

    Args:
        parameter_config (str | Path | dict, optional): configuration dict or path to yaml file. Defaults to Path(io.PATH_CONFIG_DEFAULT).

    Returns:
        dict: dict of config options
    """
    if isinstance(parameter_config, str):
        parameter_config = Path(parameter_config)
    if isinstance(parameter_config, Path):
        util.check_file_exists(parameter_config)
        parameter_config = io.read_config_file(parameter_config)
    return parameter_config


def run_parameter_config(
    config: str | Path | dict = Path(io.PATH_CONFIG_DEFAULT),
) -> Generator[model_result_type, None, None] | Generator[Path, None, None]:
    """Run all parameter combinations of all models specified by a parameter configuration

    Args:
        config (str | Path | dict, optional): config dict (or path to it). Defaults to Path(io.PATH_CONFIG_DEFAULT).

    Yields:
        Generator[model_result_type, None, None] | Generator[Path, None, None]: if no output filetype is specified,
        return the model results themselves. Otherwise return the paths to the output files
    """

    config_dict = get_parameter_config(config)

    model_directory = config_dict.get("model_directory", io.DIR_MODEL_DEFAULT)
    model_directory = Path(model_directory)

    model_input = io.read_model_input(config_dict)
    model_result = generate_model_result(model_input, model_directory=model_directory)
    model_output = create_model_output(model_result, config_dict)

    yield from model_output


def generate_model_result(
    model_input: Generator[tuple[str, pd.DataFrame], None, None],
    model_directory: Path = Path(io.DIR_MODEL_DEFAULT),
) -> Generator[model_result_type, None, None]:
    """Run each model after the parameter inputs have been organized based on model

    Args:
        model_input (Generator[tuple[str, pd.DataFrame], None, None]): input model name and parameter values to test
        model_directory (Path): where the csm model files are saved

    Yields:
        Generator[model_result_type, None, None]: generator of model results
    """
    for model_name, param_df in model_input:

        model = CSM.from_name(model_name, model_directory)

        _, result_iter = zip(*param_df.apply(pd.Series.to_dict, axis=1).items())
        result_calculate = map(model.calculate_all, result_iter)

        result_iterate = tqdm(
            result_calculate, desc=model_name, total=len(param_df.index)
        )
        result_unprocessed = tuple(result_iterate)
        keys_dataframe = set(
            k for k, v in result_unprocessed[0].items() if isinstance(v, pd.DataFrame)
        )
        result_unprocessed_dataframe = tuple(
            {k: r.pop(k) for k in keys_dataframe} for r in result_unprocessed
        )
        # Assuming all results will have the same keys in the result_df dict
        result_df = {
            k: pd.concat(
                (r[k] for r in result_unprocessed_dataframe), keys=param_df.index
            )
            for k in result_unprocessed_dataframe[0].keys()
        }

        result_scalar = pd.DataFrame(result_unprocessed, index=param_df.index)

        yield model_name, (result_scalar, result_df)


def create_model_output(
    model_result: Generator[model_result_type, None, None],
    config: dict,
) -> Generator[model_result_type, None, None] | Generator[Path, None, None]:
    """Create the model output in the specified output format, or return the model results directly if not output specified

    Args:
        model_result (Generator[model_result_type, None, None]): resutls from model
        config (dict): configuration dict

    Yields:
        Generator[model_result_type, None, None] | Generator[Path, None, None]: either the model results returned directly or the paths to the output files
    """

    # Lookup to get which function should be used to create the output file
    func_create_output_lookup = {
        "excel": io.generate_output_excel,
    }

    if (output_file_type := config.get("output_type", None)) is None:
        # if there is no output file type, simply return the results from the model(s)
        yield from model_result

    else:
        output_dir = Path(config.get("output_directory", io.DIR_OUTPUT_DEFAULT))

        if output_file_type not in func_create_output_lookup.keys():
            raise KeyError(
                f"Invalid output file type: '{output_file_type:s}'. Allowable values are {', '.join(func_create_output_lookup.keys())} or None",
            )
        func_create_output = func_create_output_lookup[output_file_type]

        # Call the appropriate function on the model results
        for model_name, model_result in model_result:  # type: ignore
            yield from func_create_output(model_name, model_result, output_dir)  # type: ignore
