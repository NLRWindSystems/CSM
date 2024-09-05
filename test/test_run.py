import pytest
from csm import run, io
from test.conftest import PATH_CONFIG


def test_get_parameter_config():
    assert isinstance(run.get_parameter_config(io.PATH_CONFIG_DEFAULT), dict)


def test_get_parameter_config_str():
    assert isinstance(run.get_parameter_config(str(io.PATH_CONFIG_DEFAULT)), dict)


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
