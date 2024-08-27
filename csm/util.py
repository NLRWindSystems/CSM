import itertools
import numpy as np
import importlib
from pathlib import Path
from collections.abc import Generator
import os
import types

DIR_MODELS_DEFAULT = "./csm/model"


def get_csm_module(
    model_name: list | tuple | str | None = None,
    dir_models: Path | str | None = None,
) -> types.ModuleType:
    return get_csm_modules(dir_models=dir_models, model_name=model_name)[model_name]


def get_csm_modules(
    model_name: list | tuple | str | None = None,
    dir_models: str | Path | None = None,
) -> dict:
    """Dynamically import all .py files in the models_directory folder as cost and scaling models"""

    DIR_MODELS_DEFAULT = "./csm/model"

    wd = os.getcwd()

    if isinstance(dir_models, str):
        dir_models = Path(dir_models)
    elif isinstance(dir_models, dict):
        dir_models = Path(dir_models.get("model_directory", DIR_MODELS_DEFAULT))
    else:
        os.chdir(Path(__file__).parent.parent)
        dir_models = Path(DIR_MODELS_DEFAULT)

    if isinstance(model_name, str):
        modules_to_import = [model_name]
    else:
        modules_to_import = dir_models.glob("[!__]*[!__].py")
        modules_to_import = (p.stem for p in modules_to_import)
        if isinstance(model_name, (list, tuple)):
            modules_to_import = (m for m in modules_to_import if m in model_name)

    csm_modules = {
        m: importlib.import_module(
            name=f".{m:s}",
            package=".".join(dir_models.parts),
        )
        for m in modules_to_import
    }

    os.chdir(wd)

    if len(csm_modules) == 0:
        raise ImportError("No CSM modules found.")

    return csm_modules


def expand_dict_of_dicts(
    dict_with_dicts: dict,
    upstream_key: str | None = None,
) -> Generator[dict]:
    """Recursively un-nest a dictionary that (possibly) contains nested dictionaries.
    Each nested dictionary is expanded to include the keys and values of all dictionaries it is within.

    Args:
        dict_with_dicts (dict): dictionary that possibly contains nested dictionaries
        upstream_key (str | None, optional): used to identify the level of nesting. Defaults to None.

    Yields:
        Generator[dict]: generator of flat dictionaries
    """

    # Determine which entries in the dict are and are not dicts themselves
    dict_entries = dict()
    non_dict_entries = dict()
    for k, v in dict_with_dicts.items():
        if isinstance(v, dict):
            dict_entries[k] = v
        else:
            non_dict_entries[k] = v

    if len(dict_entries) > 0:

        # For each dict element, recursively expand it's contents, appending the upstream dict keys
        for k, v in dict_entries.items():

            k = str(k)  # convert key to string if not already

            if upstream_key is None:
                combined_key = k
            else:
                combined_key = upstream_key + "_" + k

            yield from expand_dict_of_dicts(
                dict_with_dicts=non_dict_entries | v,
                upstream_key=combined_key,
            )
    else:
        # Exit recursion if the dictionary does not contain any dicts within
        yield dict(scenario=upstream_key, **non_dict_entries)


def dict_list_product(**dict_of_lists) -> Generator[dict]:
    """Expand a dictionary that only contains lists into an iterable of dicts representing the cartesian product of the lists

    Yields:
        Generator[dict]: dictionaries with no lists
    """

    # Any value can optionally be specified as [[start, end], count] instead a list of values
    for k in dict_of_lists.keys():
        v = dict_of_lists[k]
        if isinstance(v[0], list):

            if not (len(v) == 2 and isinstance(v[1], int)):
                raise Exception(
                    f"{k:s} - the correct input format is [[start, end], count] where count is an integer. Value entered is {str(v):s}.",
                )
            dict_of_lists[k] = np.linspace(*v[0], v[1])

    yield from (
        dict(zip(dict_of_lists, x)) for x in itertools.product(*dict_of_lists.values())
    )


def expand_dict_of_lists(dict_with_lists: dict) -> Generator[dict]:
    """Expand a dictionary that may or may not contain lists into an iterable of dicts representing the cartesian product
    of the lists as well as the non-list items

    Args:
        dict_with_lists (dict): dictionary that may or may not contain lists

    Yields:
        Generator[dict]: iterator of dicts containing the cartesian product of the lists
    """

    non_list_entries = dict()
    list_entries = dict()

    for k, v in dict_with_lists.items():
        if isinstance(v, list):
            list_entries[k] = v
        else:
            non_list_entries[k] = v

    product_dict = (
        dict(**d, **non_list_entries) for d in dict_list_product(**list_entries)
    )
    yield from product_dict


if __name__ == "__main__":
    pass
