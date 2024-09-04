from csm import CSM
import pytest
import pandas as pd
import numpy as np
from test.model import test_model
from pandas.testing import assert_frame_equal


DIR_MODEL_TEST = "./test/model"


@pytest.fixture
def csm_simple():
    return test_model.Basic()


@pytest.fixture
def csm_dataframe():
    return test_model.DataFrame()


@pytest.fixture
def csm_dataframe_noargs():
    return test_model.DataFrameNoArgs()


@pytest.fixture
def input_vectorized():
    input_vectorized = pd.DataFrame(
        data={
            "a": [1, 2, 3],
            "b": [4, 5, 6],
        },
    )
    input_vectorized = input_vectorized.rename_axis("test_scenario")
    return input_vectorized


def test_CSM_instantiate():
    with pytest.raises(TypeError):
        CSM()


def test_CSM_from_name():
    assert isinstance(CSM.from_name("Basic", DIR_MODEL_TEST), CSM)


def test_CSM_from_name_invalid():
    with pytest.raises(FileNotFoundError):
        CSM.from_name("model that does not exist")


def test_CSM_repr():
    model = test_model.Basic()
    assert str(model) == "CSM(Basic)"


def test_get_available_models_no_models():
    assert CSM.get_available_models("directory that does not exist") == {}


def test_create_model(csm_simple):
    assert csm_simple._name == "Basic"
    assert csm_simple._parameters == {"a", "b", "c", "d", "e"}
    assert csm_simple._inputs == {"a", "b"}
    assert csm_simple._outputs == {"c", "d", "e"}
    assert csm_simple._function_args == {
        "c": ["a", "b"],
        "d": ["c", "a"],
        "e": ["d"],
    }


def test_create_recursive_model():
    with pytest.raises(RecursionError):
        test_model.Recursive()


def test_get_inputs(csm_simple):
    assert csm_simple.get_inputs() == ["a", "b"]


def test_get_outputs(csm_simple):
    assert csm_simple.get_outputs() == ["c", "d", "e"]


def test_get_name(csm_simple):
    assert csm_simple.get_name() == "Basic"


@pytest.mark.parametrize(
    "param_name, inputs, calculatable",
    [
        ("c", ["a", "b"], True),
        ("c", ["a"], False),
        ("c", [], False),
        ("c", ["a", "b"], True),
        ("c", ["b", "a"], True),
        ("d", ["a"], False),
        ("d", ["a", "b"], True),
        ("d", ["c"], False),
        ("e", ["d"], True),
        ("e", ["a", "c"], True),
        ("e", ["a", "b"], True),
    ],
)
def test_is_calculatable_with_inputs(csm_simple, param_name, inputs, calculatable):
    assert csm_simple.is_calculatable_with_inputs(param_name, inputs) is calculatable


@pytest.mark.parametrize(
    "param_name, required_inputs",
    [
        ("a", ["a"]),
        ("c", ["a", "b"]),
        ("d", ["a", "b"]),
    ],
)
def test_required_inputs_to_calculate(param_name, required_inputs, csm_simple):
    assert csm_simple.required_inputs_to_calculate(param_name) == required_inputs


def test_required_inputs_to_calculate_invalid(csm_simple):
    with pytest.raises(KeyError):
        csm_simple.required_inputs_to_calculate("param that does not exist")


@pytest.mark.parametrize(
    "param_name, input_data, expected_output",
    [
        ("a", {"a": 1, "b": 2}, 1),
        ("b", {"a": 1, "b": 2}, 2),
        ("b", {"b": 2, "a": 1}, 2),
        ("c", {"a": 1, "b": 2}, 4),
        ("d", {"a": 1, "b": 5}, 9),
        ("e", {"a": 1, "b": 2}, 7),
        ("e", {"a": 5, "c": 1}, 8),
        ("e", {"d": 10}, 11),
    ],
)
def test_calculate_parameter_scalar_input_scalar_output(
    csm_simple, param_name, input_data, expected_output
):
    assert csm_simple.calculate_parameter(param_name, **input_data) == expected_output
    assert csm_simple.calculate_parameter(param_name, input_data) == expected_output


def test_calculate_parameter_scalar_input_dataframe_output(csm_dataframe):
    expected = pd.DataFrame(data={"a": [1, 1, 1], "b": [2, 2, 2]}).rename_axis(
        "test_index_name",
    )
    actual = csm_dataframe.calculate_parameter("df_output", **{"a": 1, "b": 2})
    assert_frame_equal(actual, expected)


def test_calculate_parameter_scalar_input_dataframe_noargs_output(
    csm_dataframe_noargs,
):
    expected = pd.DataFrame(data={"a": [1, 2], "b": [4, 5]}).rename_axis(
        "test_index_name",
    )
    actual = csm_dataframe_noargs.calculate_parameter("df_output")
    assert_frame_equal(actual, expected)


@pytest.mark.parametrize(
    "param_name, input_data, expected_output",
    [
        ("a", {"a": np.array([1, 2]), "b": np.array([3, 4])}, np.array([1, 2])),
        ("b", {"a": np.array([1, 2]), "b": np.array([3, 4])}, np.array([3, 4])),
        ("b", {"b": np.array([3, 4]), "a": np.array([1, 2])}, np.array([3, 4])),
        ("c", {"a": np.array([1, 2]), "b": np.array([3, 4])}, np.array([5, 7])),
        ("d", {"a": np.array([1, 2]), "b": np.array([3, 4])}, np.array([7, 10])),
        ("e", {"a": np.array([1, 2]), "b": np.array([3, 4])}, np.array([8, 11])),
        ("e", {"a": np.array([1, 2]), "c": np.array([3, 4])}, np.array([6, 8])),
        ("e", {"d": np.array([10, 11])}, np.array([11, 12])),
    ],
)
def test_calculate_parameter_vector_input_vector_output(
    csm_simple, param_name, input_data, expected_output
):
    assert np.array_equal(
        csm_simple.calculate_parameter(param_name, **input_data),
        expected_output,
    )


def test_calculate_parameter_vector_input_dataframe_output(csm_dataframe):
    expected = (
        pd.DataFrame(data={"a": [1, 1, 1], "b": [3, 3, 3]}).rename_axis(
            "test_index_name",
        ),
        pd.DataFrame(data={"a": [2, 2, 2], "b": [4, 4, 4]}).rename_axis(
            "test_index_name",
        ),
    )
    actual = csm_dataframe.calculate_parameter(
        "df_output", {"a": np.array([1, 2]), "b": np.array([3, 4])}
    )
    for a, e in zip(actual, expected):
        assert_frame_equal(a, e, check_dtype=False)


@pytest.mark.parametrize(
    "param_name, expected_output",
    [
        ("a", np.array([1, 2, 3])),
        ("b", np.array([4, 5, 6])),
        ("c", np.array([6, 8, 10])),
        ("d", np.array([8, 11, 14])),
        ("e", np.array([9, 12, 15])),
    ],
)
def test_calculate_parameter_dataframe_input_vector_output(
    csm_simple,
    input_vectorized,
    param_name,
    expected_output,
):
    assert np.array_equal(
        csm_simple.calculate_parameter(param_name, input_vectorized),
        expected_output,
    )


def test_calculate_parameter_dataframe_input_dataframe_output(
    csm_dataframe,
    input_vectorized,
):

    expected = pd.DataFrame(
        data={"a": [1, 1, 1, 2, 2, 2, 3, 3, 3], "b": [4, 4, 4, 5, 5, 5, 6, 6, 6]},
        index=pd.MultiIndex.from_product(
            iterables=[[0, 1, 2], [0, 1, 2]],
            names=["test_scenario", "test_index_name"],
        ),
    )
    actual = csm_dataframe.calculate_parameter("df_output", input_vectorized)
    assert_frame_equal(actual, expected)


def test_calculate_parameter_dataframe_input_dataframe_noargs_output(
    csm_dataframe_noargs,
    input_vectorized,
):
    expected_rows = len(input_vectorized.index)
    expected = pd.DataFrame(
        data={
            "a": [1, 2] * expected_rows,
            "b": [4, 5] * expected_rows,
        },
        index=pd.MultiIndex.from_product(
            iterables=[range(expected_rows), [0, 1]],
            names=["test_scenario", "test_index_name"],
        ),
    )
    actual = csm_dataframe_noargs.calculate_parameter("df_output", input_vectorized)
    assert_frame_equal(actual, expected)


def test_calculate_parameter_nonexistent_scalar_input(csm_simple):
    with pytest.raises(KeyError):
        csm_simple.calculate_parameter("nonexistent_parameter", {"a": 1, "b": 2})


def test_calculate_parameter_missing_input(csm_simple):
    with pytest.raises(KeyError):
        csm_simple.calculate_parameter("d", **{"a": 1})


def test_dataframe_missing_type_hint():
    csm = test_model.MissingReturnTypeHint()
    csm.calculate_parameter("df_output", a=1, b=2)
