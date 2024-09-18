from csm import CSM
import pytest
import pandas as pd
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
def csm_simple_all_inputs():
    return {"a": 1, "b": 2}


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
    assert set(csm_simple._inputs) == {"a", "b"}


def test_get_function_args(csm_simple):
    assert csm_simple.get_function_args() == {
        "c": ["a", "b"],
        "d": ["c", "a"],
        "e": ["d"],
    }


def test_create_recursive_model():
    with pytest.raises(RecursionError):
        test_model.Recursive()


def test_get_inputs(csm_simple):
    assert set(csm_simple.get_inputs()) == {"a", "b"}


def test_get_outputs(csm_simple):
    assert set(csm_simple.get_outputs()) == {"c", "d", "e"}


def test_get_name(csm_simple):
    assert csm_simple.get_name() == "Basic"


@pytest.mark.parametrize(
    "param_name, inputs, calculable",
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
def test_is_calculable_with_inputs(csm_simple, param_name, inputs, calculable):
    assert csm_simple.is_calculable_with_inputs(param_name, inputs) is calculable


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


def test_display_function(csm_simple, capsys):
    expected = """
    def e(d):
        return d + 1
    """
    csm_simple.display_function("e")
    actual = capsys.readouterr()
    assert actual.out.strip() == expected.strip()


@pytest.mark.parametrize("param_name", ["a", "x"])
def test_display_function_invalid_input(csm_simple, param_name):
    with pytest.raises(KeyError):
        csm_simple.display_function(param_name)


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
    assert csm_simple.calculate(param_name, **input_data) == expected_output
    assert csm_simple.calculate(param_name, input_data) == expected_output


def test_calculate_parameter_scalar_input_dataframe_output(csm_dataframe):
    expected = pd.DataFrame(data={"a": [1, 1, 1], "b": [2, 2, 2]}).rename_axis(
        "test_index_name",
    )
    actual = csm_dataframe.calculate("df_output", **{"a": 1, "b": 2})
    assert_frame_equal(actual, expected)


def test_calculate_parameter_scalar_input_dataframe_noargs_output(
    csm_dataframe_noargs,
):
    expected = pd.DataFrame(data={"a": [1, 2], "b": [4, 5]}).rename_axis(
        "test_index_name",
    )
    actual = csm_dataframe_noargs.calculate("df_output")
    assert_frame_equal(actual, expected)


def test_calculate_parameter_nonexistent_scalar_input(csm_simple):
    with pytest.raises(KeyError):
        csm_simple.calculate("nonexistent_parameter", {"a": 1, "b": 2})


def test_calculate_parameter_missing_input(csm_simple):
    with pytest.raises(KeyError):
        csm_simple.calculate("d", **{"a": 1})


def test_dataframe_missing_type_hint():
    csm = test_model.MissingReturnTypeHint()
    csm.calculate("df_output", a=1, b=2)


def test_model_no_functions():
    with pytest.raises(ValueError):
        test_model.NoFunctions()


def test_calculate_all(csm_simple, csm_simple_all_inputs):
    expected = {**csm_simple_all_inputs, "c": 4, "d": 6, "e": 7}
    assert csm_simple.calculate_all(csm_simple_all_inputs) == expected
    assert csm_simple.calculate_all(**csm_simple_all_inputs) == expected


def test_calculate_all_no_inputs(csm_simple):
    assert csm_simple.calculate_all() == {}


def test_calculate_all_unnecessary_inputs(csm_simple, csm_simple_all_inputs):
    with pytest.warns():
        csm_simple.calculate_all(**csm_simple_all_inputs, unnecessary_parameter=100)
