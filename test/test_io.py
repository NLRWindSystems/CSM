import pytest
from pathlib import Path
from csm import io


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


def test_read_config_file():
    assert isinstance(io.read_config_file(io.PATH_CONFIG_DEFAULT), dict)


def test_read_config_file_missing():
    with pytest.raises(FileNotFoundError):
        io.read_config_file(Path("file that does not exist"))


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

    actual = io.create_input_parameter_scenarios(sample_config)
    for a, e in zip(actual, expected):
        assert a == e


def test_create_input_parameter_scenarios_no_params():
    with pytest.raises(KeyError):
        tuple(io.create_input_parameter_scenarios({}))


def test_create_input_parameter_scenarios_no_model():
    with pytest.raises(KeyError):
        tuple(io.create_input_parameter_scenarios({"a": 1, "b": 2}))


def test_create_input_parameter_scenarios_none_model():
    with pytest.raises(KeyError):
        tuple(
            io.create_input_parameter_scenarios(
                {"parameters": {"a": 1, "b": 2, "model": None}}
            )
        )
