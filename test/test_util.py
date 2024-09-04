from pathlib import Path
import types
import pytest

from csm import util

from test.conftest import MODEL_DIRECTORY, MODEL_FILENAME


def test_import_module():
    module = util.import_module(Path(MODEL_DIRECTORY) / MODEL_FILENAME)
    assert isinstance(module, types.ModuleType)


def test_import_missing_module():
    with pytest.raises(FileNotFoundError):
        util.import_module(Path("module that does not exist.py"))


def test_check_file_exists():
    util.check_file_exists(Path(__file__))


def test_check_file_exists_error():
    with pytest.raises(FileNotFoundError):
        util.check_file_exists(Path("file that does not exist.py"))


def test_expand_dict_of_dicts():

    input_output = [
        (
            {"a": {"b": {"b1": 1, "b2": 2}}},
            [{"scenario": "a_b", "b1": 1, "b2": 2}],
        ),
        (
            {"a": 2, "b": {"b1": 1}},
            [{"a": 2, "scenario": "b", "b1": 1}],
        ),
        (
            {"a": {"b": {"c": {"d": 3}}}},
            [{"scenario": "a_b_c", "d": 3}],
        ),
        (
            {"a": [1, 2], "b": 6, "c": {"c1": [3, 4], "c2": 5}},
            [{"a": [1, 2], "b": 6, "scenario": "c", "c1": [3, 4], "c2": 5}],
        ),
    ]
    for input, output in input_output:
        assert list(util.expand_dict_of_dicts(input)) == output


def test_dict_list_product():
    input_output = [
        (
            {"a": [1, 2], "b": [3, 4]},
            [{"a": 1, "b": 3}, {"a": 1, "b": 4}, {"a": 2, "b": 3}, {"a": 2, "b": 4}],
        ),
        (
            {"a": [1]},
            [{"a": 1}],
        ),
        (
            {"a": [[1, 2], 2], "b": [4, 5]},
            [{"a": 1, "b": 4}, {"a": 1, "b": 5}, {"a": 2, "b": 4}, {"a": 2, "b": 5}],
        ),
    ]
    for input, output in input_output:
        assert list(util.dict_list_product(**input)) == output
        assert list(util.expand_dict_of_lists(input)) == output


def test_dict_list_product_error():
    inputs = [
        {"a": [1, 2], "b": 3},
        {"a": 2},
        {"a": {"b": 1}},
    ]
    for input in inputs:
        with pytest.raises(TypeError):
            set(util.dict_list_product(**input))


def test_expand_dict_of_lists():
    input_output = [
        (
            {"a": 1, "b": [3, 4]},
            [
                {"a": 1, "b": 3},
                {"a": 1, "b": 4},
            ],
        ),
        (
            {"a": [1, 2], "b": [3, 4]},
            [
                {"a": 1, "b": 3},
                {"a": 1, "b": 4},
                {"a": 2, "b": 3},
                {"a": 2, "b": 4},
            ],
        ),
        (
            {"a": [1]},
            [
                {"a": 1},
            ],
        ),
        (
            {"a": {"b": 1}, "c": [2, 3]},
            [
                {"a": {"b": 1}, "c": 2},
                {"a": {"b": 1}, "c": 3},
            ],
        ),
    ]
    for input, output in input_output:
        assert list(util.expand_dict_of_lists(input)) == output
