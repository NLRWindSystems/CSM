from csm import run, io
from test.conftest import PATH_CONFIG


def test_get_parameter_config():
    assert isinstance(run.get_parameter_config(io.PATH_CONFIG_DEFAULT), dict)


def test_get_parameter_config_str():
    assert isinstance(run.get_parameter_config(str(io.PATH_CONFIG_DEFAULT)), dict)


def test_run_parameter_config():
    result = run.run_parameter_config(config=PATH_CONFIG)
    result = tuple(result)
    assert len(result) == 3
