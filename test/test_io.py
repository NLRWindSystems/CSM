import pytest
from pathlib import Path
from csm import io


def test_read_config_file():
    assert isinstance(io.read_config_file(io.PATH_CONFIG_DEFAULT), dict)


def test_read_config_file_missing():
    with pytest.raises(FileNotFoundError):
        io.read_config_file(Path("file that does not exist"))
