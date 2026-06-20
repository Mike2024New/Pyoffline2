from layers.python_manager.start import start
from layers.python_manager.main import PythonManager
from functions import python_fn
import subprocess
import config
import pytest


def check_python(version: str):
    # проверка что Python появился в списках
    python_exe_list = python_fn.get_archive_python_executables()
    python_exe_path = None
    for pyth in python_exe_list:
        if python_fn.get_python_version(python_exe_path=pyth) == version:
            python_exe_path = pyth
    assert python_exe_path is not None, f'python версии {version} не был загружен'
    # проверка загруженного python
    cmd = [python_exe_path, '--version', ]
    res = subprocess.run(cmd, capture_output=True)
    assert res.returncode == 0, 'скачался не корректный дистрибутив python'


@pytest.fixture(scope='module')
def main(tmp_path_factory):
    # подмена базовых путей для теста
    test_dir = tmp_path_factory.mktemp('pyoffline_test')
    config.ROOT_DIR = test_dir
    config.RESOURCES_DIR = test_dir / 'resource'
    config.PYTHON_STORAGE_DIR = config.RESOURCES_DIR / 'python_storage'
    config.PYTHON_EMBED_DIR = test_dir / 'python_embed'

    if config.IS_WINDOWS:
        config.SYSTEM_PYTHON_EXE = config.PYTHON_EMBED_DIR / 'python.exe'
    else:  # для linux
        config.SYSTEM_PYTHON_EXE = config.PYTHON_EMBED_DIR / 'bin' / 'python'

    config.PYTHON_STORAGE_DIR.mkdir(exist_ok=True, parents=True)
    config.PYTHON_EMBED_DIR.mkdir(exist_ok=True, parents=True)
    config.RESOURCES_DIR.mkdir(exist_ok=True, parents=True)

    yield test_dir  # сохраняет контекст test_dir для методов завязанных на эту фикстуру


def test_download_embed_python(main):
    """
    Проверка что embed python корректно скачивается и размещается в корневой папке
    """
    version = '3.10'
    start(python_version='3.10')
    assert config.PYTHON_EMBED_EXE.exists(), 'embed python не был загружен'
    check_python(version)


def test_download_python_to_storage(main):
    """Проверка что python скачивается в python storage"""
    version = '3.12'
    PythonManager.download_python(python_version=version)
    check_python(version)
