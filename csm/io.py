from . import util
import csm

import pandas as pd
import numpy as np
import itertools
from pathlib import Path
import operator
from collections.abc import Generator
import sqlite3
from tqdm import tqdm


def read_model_input() -> Generator[tuple]:
    """Read input parameter scenarios from the config file

    Yields:
        Generator[tuple]: tuple of model name and input parameter dataframe for the model
    """

    param_input = read_input_parameters()

    # The input dicts can theoreticaly appear in any order
    # Using itertools.groupby to organize inputs by model requires them to be sorted before grouping
    param_input = sorted(param_input, key=operator.itemgetter("model"))
    param_input = itertools.groupby(param_input, key=operator.itemgetter("model"))

    for model_name, param_input_model in param_input:

        # Handle inputs with no specified model
        if model_name is None:
            raise Exception("All inputs must indicate which model should be used.")

        # Handle inputs where model name does not correspond to an existing model definition file
        if model_name not in csm.csm_models.keys():
            path_model_file = Path(util.conf["model_directory"]) / (model_name + ".py")
            raise Exception(
                f"Model {model_name:s} requires a corresponding file {str(path_model_file):s}"
            )

        param_input_model = (
            pd.DataFrame(param_input_model)
            .drop(columns="model")
            .rename_axis("scenario_number", axis=0)
            .rename_axis("parameter", axis=1)
        )
        yield model_name, param_input_model


def read_input_parameters() -> Generator[dict]:
    """Read parameters defined in the config file into a generator of dicts containing kwargs to the model(s)
    Different scenarios can be defined as dicts within the input, and all possible combinations of parameter values
    will be run for each scenario. More nested parameter definitions will override less nested ones

    Returns:
        Generator[dict]: generator of invividual scenario parameter kwargs
    """
    parameter_inputs = util.conf.get("parameters")
    if parameter_inputs is None:
        raise Exception("Must specify parameters in the configuration file.")

    parameter_inputs = util.expand_dict_of_dicts(parameter_inputs)
    parameter_inputs = map(util.expand_dict_of_lists, parameter_inputs)
    parameter_inputs = itertools.chain(*parameter_inputs)

    return parameter_inputs


def generate_output_landbosse(
    output_directory: Path,
    model_name: str,
    model_output: tuple,
) -> Generator[Path]:
    """Convert CSM model outputs to LandBOSSE format and save the LandBOSSE excel files
    LandBOSSE requires more inputs than the cost and scaling model generates, so a template containing
    default values outside the scope of the CSM is used
    Files are written sequentially. It is a very ugly and slow process

    Args:
        output_directory (Path): directory to save results
        model_name (str): name of CSM
        model_output (tuple): results from CSM

    Yields:
        Generator[Path]: Path of the saved files
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

    model_output[0].to_csv(output_directory / f"{model_name:s}_summary.csv")

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
            output_directory / "scenario" / f"{model_name:s}_{scenario_number:d}.xlsx"
        )

        lb_grp = lb_grp[lb_components.columns]

        write_input_file_landbosse(
            path_output,
            {"components": lb_grp} | lb,
        )

        yield path_output


def convert_csm_output_to_landbosse(
    model_name: str,
    csm_model_output: tuple,
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

    model_output_single, model_output_multiple = csm_model_output

    columns_landbosse = ["Mass tonne", "Lift height m", "Surface area sq m"]

    o = model_output_single

    ts = model_output_multiple.get("tower_section_data")
    if ts is None:
        raise Exception(
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
    component_data = {k: pd.concat(v, axis=1) for k, v in component_data.items()}
    component_data = {
        k: v.set_axis(columns_landbosse, axis=1) for k, v in component_data.items()
    }
    component_data = pd.concat(component_data, names=["Component"])

    component_rows_blade = (
        o["blade_mass"] / 1000.0,
        o["hub_height"],
        o["blade_surface_area"],
    )
    component_rows_blade = pd.concat(component_rows_blade, axis=1)

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

    ts = ts.reset_index(level=-1).set_index(
        ts["section_number"].map("Tower section {:d}".format).rename("Component"),
        append=True,
    )
    component_rows_tower_section = (
        ts["mass"] / 1000.0,
        ts["lift_height"],
        ts["surface_area"],
    )
    component_rows_tower_section = pd.concat(component_rows_tower_section, axis=1)
    component_rows_tower_section = component_rows_tower_section.set_axis(
        columns_landbosse, axis=1
    )

    component_data = (
        cd.reorder_levels(["scenario_number", "Component"], axis=0)
        for cd in (
            component_data,
            component_rows_blade,
            component_rows_tower_section,
        )
    )
    component_data = pd.concat(component_data)

    return component_data


def generate_output_sqlite(
    output_directory: Path,
    model_name: str,
    model_output: tuple,
) -> Generator[Path]:
    """Saves CSM output to sqlite, in case it is needed.
    Yields instead of returns to match the LandBOSSE output function

    Args:
        output_directory (Path): where the file will be saved
        model_name (str): name of model. used for filename
        model_output (tuple): results from model

    Yields:
        Generator[Path]: path to saved sqlite file
    """

    file_path = output_directory / (model_name + ".sqlite")

    model_summary, model_details = model_output

    with sqlite3.connect(file_path) as con:
        model_summary.to_sql(
            name="model_summary",
            con=con,
            if_exists="replace",
        )
        for k, v in model_details.items():
            v.to_sql(
                name=k,
                con=con,
                if_exists="replace",
            )

    yield file_path


def read_input_template_landbosse() -> dict:
    param_land_landbosse_template = "landbosse_template_path"
    path_landbosse_template = util.conf.get(param_land_landbosse_template)
    if path_landbosse_template is None:
        raise Exception(
            f"In order to produce LandBOSSE output, a template LandBOSSE input file must be specified using {param_land_landbosse_template:s} in the configuration file.",
        )
    return pd.read_excel(path_landbosse_template, sheet_name=None)


def write_input_file_landbosse(
    path: Path,
    df_sheets: dict,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(path) as ew:
        for k, v in df_sheets.items():
            v.to_excel(ew, sheet_name=k, index=False)


if __name__ == "__main__":
    pass
