import pytest
from csm import run
from test.conftest import PATH_CONFIG


@pytest.fixture
def sample_config():
    return {
        "parameters": {
            "scenario_2": {
                "x": 1,
                "y": [2, 3],
                "model": "model2",
            },
            "scenario_1": {
                "p": [4],
                "q": {
                    "a": 5,
                    "b": [6, 7],
                    "model": "model1",
                },
            },
        },
    }


def test_get_parameter_config():
    assert isinstance(run.get_parameter_config(PATH_CONFIG), dict)


def test_get_parameter_config_str():
    assert isinstance(run.get_parameter_config(str(PATH_CONFIG)), dict)


def test_create_input_parameter_scenarios(sample_config):
    expected = (
        {
            "model": "model2",
            "scenario": "scenario_2",
            "x": 1,
            "y": 2,
        },
        {
            "model": "model2",
            "scenario": "scenario_2",
            "x": 1,
            "y": 3,
        },
        {
            "model": "model1",
            "scenario": "scenario_1_q",
            "p": 4,
            "a": 5,
            "b": 6,
        },
        {
            "model": "model1",
            "scenario": "scenario_1_q",
            "p": 4,
            "a": 5,
            "b": 7,
        },
    )

    actual = run.create_input_parameter_scenarios(sample_config)
    for a, e in zip(actual, expected):
        assert a == e


def test_create_input_parameter_scenarios_no_params():
    with pytest.raises(KeyError):
        tuple(run.create_input_parameter_scenarios({}))


def test_create_input_parameter_scenarios_no_model():
    with pytest.raises(KeyError):
        tuple(run.create_input_parameter_scenarios({"a": 1, "b": 2}))


def test_create_input_parameter_scenarios_none_model():
    with pytest.raises(KeyError):
        tuple(
            run.create_input_parameter_scenarios(
                {"parameters": {"a": 1, "b": 2, "model": None}}
            )
        )


def test_run_parameter_config():
    tuple(run.run_parameter_config(config=PATH_CONFIG))


def test_run_parameter_config_excel_output(tmp_path):
    config = run.get_parameter_config(PATH_CONFIG)
    config["output_type"] = "excel"
    config["output_directory"] = tmp_path

    for p in run.run_parameter_config(config):
        assert p.is_file()


def test_run_parameter_config_invalid_output():
    config = run.get_parameter_config(PATH_CONFIG)
    config["output_type"] = "invalid_output"

    with pytest.raises(KeyError):
        tuple(run.run_parameter_config(config))
