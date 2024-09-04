import types
import typing
import itertools
import importlib.util
from pathlib import Path
from collections.abc import Generator

import numpy as np


# def import_model(
#     model_name: str,
#     dir_model: str | Path,
# ) -> typing.Callable:
#     """Checks if a CSM model exists before importing it and creating a new instance

#     Args:
#         model_name (str): name of model (which must correspond to the name of the .py file)
#         dir_model (Path): directory where model is saved

#     Raises:
#         FileNotFoundError: if file does not exist

#     Returns:
#         typing.Callable: the imported model
#     """

#     dir_model = Path(dir_model)

#     path_model = dir_model / (model_name + ".py")

#     if not path_model.is_file():
#         raise FileNotFoundError(
#             f"Could not find {model_name:s}.py in {str(dir_model):s}."
#         )

#     module = import_module(path_model)

#     model = getattr(module, model_name)
#     if model is None:
#         raise ImportError(f"Could not import {model_name:s} from {path_model:s}")

#     return model


def import_module(
    path_module: Path,
) -> types.ModuleType:
    check_file_exists(path_module)
    spec = importlib.util.spec_from_file_location(path_module.stem, path_module)
    module = importlib.util.module_from_spec(spec)  # type: ignore
    spec.loader.exec_module(module)  # type: ignore
    return module


def check_file_exists(path: Path):
    if not path.is_file():
        raise FileNotFoundError(f"File {str(path):s} does not exist.")


def expand_dict_of_dicts(
    dict_with_dicts: dict,
    upstream_key: str | None = None,
) -> Generator[dict[str, typing.Any], None, None]:
    """Recursively un-nest a dictionary that (possibly) contains nested dictionaries.
    Each nested dictionary is expanded to include the keys and values of all dictionaries it is within.

    Args:
        dict_with_dicts (dict): dictionary that possibly contains nested dictionaries
        upstream_key (str | None, optional): used to identify the level of nesting. Defaults to None.

    Yields:
        Generator[dict[str, typing.Any], None, None]: generator of flat dictionaries
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


def dict_list_product(**dict_of_lists) -> Generator[dict[str, typing.Any], None, None]:
    """Expand a dictionary that only contains lists into an iterable of dicts representing the cartesian product of the lists

    Yields:
        Generator[dict[str, typing.Any], None, None]: dictionaries with no lists
    """

    # Any value can optionally be specified as [[start, end], count] instead a list of values
    for k in dict_of_lists.keys():
        v = dict_of_lists[k]

        if not isinstance(v, list):
            raise TypeError("Input dict can only contain list values.")

        if isinstance(v[0], list):
            if len(v) == 2 and isinstance(v[1], int):
                (start, stop) = v[0]
                dict_of_lists[k] = np.linspace(start, stop, v[1])

    yield from (
        dict(zip(dict_of_lists, x)) for x in itertools.product(*dict_of_lists.values())
    )


def expand_dict_of_lists(
    dict_with_lists: dict,
) -> Generator[dict[str, typing.Any], None, None]:
    """Expand a dictionary that may or may not contain lists into an iterable of dicts representing the cartesian product
    of the lists as well as the non-list items

    Args:
        dict_with_lists (dict): dictionary that may or may not contain lists

    Yields:
        Generator[dict[str, typing.Any], None, None]: iterator of dicts containing the cartesian product of the lists
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
