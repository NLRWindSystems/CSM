from pathlib import Path
from collections.abc import Generator

import yaml
import pandas as pd


DIR_MODEL_DEFAULT = Path(__file__).parent / "model"
DIR_OUTPUT_DEFAULT = "./output"
PATH_CONFIG_DEFAULT = "./input/config.yaml"
CSM_RESULT_TYPE = tuple[pd.DataFrame, dict[str, pd.DataFrame]]


def read_config_file(
    path_config: Path,
) -> dict:
    return yaml.safe_load(open(path_config))


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
