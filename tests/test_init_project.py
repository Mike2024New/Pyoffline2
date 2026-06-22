from functions import python_fn
import config
import pytest
from layers.archive_manager.main import PackagesArchive
from layers.python_manager.main import PythonManager
from layers.pack_installer.main import PackagesManager


@pytest.fixture(scope='module')
def main(tmp_path_factory):
    # подмена базовых путей для теста
    test_dir = tmp_path_factory.mktemp('pyoffline_test')
    config.ROOT_DIR = test_dir
    config.RESOURCES_DIR = test_dir / 'resource'
    config.PACKAGES_DIR = config.RESOURCES_DIR / 'packages_storage'
    config.RESOURCES_DIR.mkdir(exist_ok=True, parents=True)
    config.PACKAGES_DIR.mkdir(exist_ok=True, parents=True)

    yield test_dir  # сохраняет контекст test_dir для методов завязанных на эту фикстуру


def test_download_package_1(main):
    python_exe_paths = python_fn.get_archive_python_executables()
    python_versions = [python_fn.get_python_version(exe) for exe in python_exe_paths]
    assert len(python_versions) > 0, 'Для проведения этого теста нужна хотябы одна версия python в python_storage'
    python_exe_version = python_versions[0]
    # скачивание пакетов для примера
    packages_list = ['python-dotenv']
    PackagesArchive.download(packages_list=packages_list)
    # создание виртуального окружения
    target_project_dir = main / 'demo'
    target_project_python_exe = target_project_dir / config.PYTHON_EXE_PATH_POSTFIX

    PythonManager.create(project_path=target_project_dir, python_version=python_exe_version)
    assert target_project_dir.exists(), f'не была создана папка целевого проекта'
    assert target_project_python_exe.exists(), f'не было создано виртуальное окружение проекта'
    is_version_correct = python_fn.get_python_version(target_project_python_exe)
    assert is_version_correct == python_exe_version, f'Не верная версия python в целевом проекте'

    # установка пакета в целевой проект
    PackagesManager.install(target_project_path=target_project_dir, pkg_name=packages_list[0])
