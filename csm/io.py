import typing
import operator
import itertools
from pathlib import Path
from collections.abc import Generator

import yaml
import numpy as np
import pandas as pd
from tqdm import tqdm

from csm import util


csm_result_type = tuple[pd.DataFrame, dict[str, pd.DataFrame]]

DIR_MODEL_DEFAULT = "./csm/model"
DIR_OUTPUT_DEFAULT = "./output"
PATH_LANDBOSSE_TEMPLATE = "./input/landbosse_input_template.xlsx"
PATH_CONFIG_DEFAULT = "./input/config.yaml"


def read_config_file(
    path_config: Path,
) -> dict:
    return yaml.safe_load(open(path_config))


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

    param_input = read_input_parameters(config)

    # The input dicts can theoreticaly appear in any order
    # Using itertools.groupby to organize inputs by model requires them to be sorted before grouping
    param_groupby = operator.itemgetter("model")
    param_input_grouped = itertools.groupby(
        sorted(param_input, key=param_groupby),
        key=param_groupby,
    )

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


def read_input_parameters(
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

    yield from parameter_inputs


def generate_output_landbosse(
    model_name: str,
    model_output: csm_result_type,
    output_dir: Path,
) -> Generator[Path, None, None]:
    """Convert CSM model outputs to LandBOSSE format and save the LandBOSSE excel files
    LandBOSSE requires more inputs than the cost and scaling model generates, so a template containing
    default values outside the scope of the CSM is used.
    Files are written sequentially. It is a very ugly and slow process

    Args:
        model_name (str): name of CSM
        model_output (csm_result_type): results from CSM
        output_dir (Path): directory to save the output files

    Yields:
        Generator[Path, None, None]: Path of the saved files
    """

    landbosse_input = convert_csm_output_to_landbosse(model_name, model_output)

    lb = read_input_template_landbosse()

    lb_components = lb.pop("components")

    lb_scenario_groups = landbosse_input.groupby("scenario_number")
    lb_scenario_groups = tqdm(
        lb_scenario_groups,
        desc=f"{model_name:s}: converting to LandBOSSE format",
        total=lb_scenario_groups.ngroups,
    )

    model_output[0].to_csv(output_dir / f"{model_name:s}_summary.csv")

    for scenario_number, lb_grp in lb_scenario_groups:
        lb_grp = lb_grp.reset_index(level="Component").reset_index(drop=True)

        other_columns = lb_components.columns.difference(lb_grp.columns)

        for component_type, component_grp in lb_components.groupby(
            by=lb_components["Component"].str.split(" ").str[0]
        ):
            component_first_row = component_grp.iloc[0]

            # will convert int to float
            lb_grp.loc[
                lb_grp["Component"].str.startswith(component_type),
                other_columns,
            ] = lb_components.loc[component_first_row.name, other_columns].values

        path_output = (
            output_dir / "scenario" / f"{model_name:s}_{scenario_number:d}.xlsx"
        )

        lb_grp = lb_grp[lb_components.columns]

        write_input_file_landbosse(
            path_output,
            {"components": lb_grp} | lb,
        )

        yield path_output


def convert_csm_output_to_landbosse(
    model_name: str,
    model_output: csm_result_type,
) -> pd.DataFrame:
    """Convert the results of the CSM into a format that LandBOSSE accepts.
    This function only covers certain columns from the 'components' input sheet to LandBOSSE,
    other sheets are left as the default using the template LandBOSSE input

    Args:
        model_name (str): name of CSM
        csm_model_output (tuple): results from CSM

    Returns:
        pd.DataFrame: Contents of the 'components' input sheet for LandBOSSE with values from the CSM
    """

    model_output_single, model_output_multiple = model_output

    columns_landbosse = ["Mass tonne", "Lift height m", "Surface area sq m"]

    o = model_output_single

    if (ts := model_output_multiple.get("tower_section_data")) is None:
        raise KeyError(
            f"{model_name:s}: tower_section_data is required to create a LandBOSSE input sheet. You may need to add a function to generate it."
        )
    ts = ts.copy()

    component_rows_nacelle = (
        o["nacelle_mass"] / 1000.0,
        o["nacelle_lift_height"],
        o["nacelle_surface_area"],
    )
    component_rows_drivetrain = (
        o["nacelle_mass"] * np.nan,
        o["nacelle_lift_height"],
        o["nacelle_surface_area"],
    )
    component_rows_hub = (
        o["hub_mass"] / 1000.0,
        o["hub_height"],
        o["hub_surface_area"],
    )

    component_data = {
        "Nacelle": component_rows_nacelle,
        "Drivetrain": component_rows_drivetrain,
        "Hub": component_rows_hub,
    }
    component_data = pd.concat(
        {
            k: pd.concat(v, axis=1).set_axis(columns_landbosse, axis=1)
            for k, v in component_data.items()
        },
        names=["Component"],
    )

    component_rows_blade = pd.concat(
        (
            o["blade_mass"] / 1000.0,
            o["hub_height"],
            o["blade_surface_area"],
        ),
        axis=1,
    )

    # Expand out the blades to match LandBOSSE input.
    # It can handle any number of blades
    expand_blades = (
        model_output_single["num_blades"]
        .apply(lambda n: list(range(1, n + 1)))
        .explode()
        .map("Blade {:d}".format)
        .rename("Component")
    )
    component_rows_blade = component_rows_blade.loc[expand_blades.index].set_index(
        expand_blades, append=True
    )
    component_rows_blade = component_rows_blade.set_axis(columns_landbosse, axis=1)

    ts.index = ts.index.set_levels(
        ts.index.levels[ts.index.names.index("tower_section_id")].map(
            "Tower section {:d}".format
        ),
        level="tower_section_id",
    ).rename("Component", level="tower_section_id")

    component_rows_tower_section = (
        ts["mass"] / 1000.0,
        ts["lift_height"],
        ts["surface_area"],
    )
    component_rows_tower_section = pd.concat(
        component_rows_tower_section,
        axis=1,
    ).set_axis(columns_landbosse, axis=1)

    component_data = pd.concat(
        cd.reorder_levels(["scenario_number", "Component"], axis=0)
        for cd in (
            component_data,
            component_rows_blade,
            component_rows_tower_section,
        )
    )

    return component_data


def read_input_template_landbosse() -> dict:
    return pd.read_excel(Path(PATH_LANDBOSSE_TEMPLATE), sheet_name=None)


def write_input_file_landbosse(
    path: Path,
    df_sheets: dict[str, pd.DataFrame],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(path) as ew:
        for k, v in df_sheets.items():
            v.to_excel(ew, sheet_name=k, index=False)


def generate_output_excel(
    model_name: str,
    model_output: csm_result_type,
    output_dir: Path,
) -> Generator[Path, None, None]:
    """Saves CSM output to excel, in case it is needed.
    Yields instead of returns to match the LandBOSSE output function

    Args:
        model_name (str): name of model. used for filename
        model_output (csm_result_type): results from model
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
