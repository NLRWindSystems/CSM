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


def test_load_config():
    assert isinstance(run.load_config(PATH_CONFIG), dict)


def test_load_config_str():
    assert isinstance(run.load_config(str(PATH_CONFIG)), dict)


def test_generate_input_parameter_scenarios(sample_config):
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

    actual = run.generate_input_parameter_scenarios(sample_config)
    for a, e in zip(actual, expected):
        assert a == e


def test_generate_input_parameter_scenarios_no_params():
    with pytest.raises(KeyError):
        tuple(run.generate_input_parameter_scenarios({}))


def test_generate_input_parameter_scenarios_no_model():
    with pytest.raises(KeyError):
        tuple(run.generate_input_parameter_scenarios({"a": 1, "b": 2}))


def test_generate_input_parameter_scenarios_none_model():
    with pytest.raises(KeyError):
        tuple(
            run.generate_input_parameter_scenarios(
                {"parameters": {"a": 1, "b": 2, "model": None}}
            )
        )


def test_run_config():
    tuple(run.run_config(config=PATH_CONFIG))


def test_run_config_excel_output(tmp_path):
    config = run.load_config(PATH_CONFIG)
    config["output_type"] = "excel"
    config["output_directory"] = tmp_path

    for p in run.run_config(config):
        assert p.is_file()


def test_run_config_invalid_output():
    config = run.load_config(PATH_CONFIG)
    config["output_type"] = "invalid_output"

    with pytest.raises(KeyError):
        tuple(run.run_config(config))
