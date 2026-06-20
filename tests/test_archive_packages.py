from functions import python_fn
import config
import pytest
from layers.archive_manager.main import PackagesArchive
from functions import packages_fn


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


def load_packages(packages_list):
    python_exe_paths = python_fn.get_archive_python_executables()
    python_versions = [python_fn.get_python_version(exe) for exe in python_exe_paths]

    assert len(python_versions) > 0, 'Для проведения этого теста нужна хотябы одна версия python в python_storage'

    PackagesArchive.download(packages_list=packages_list)

    for pv in python_versions:
        for pack in packages_list:
            pack_exists = packages_fn.is_package_archive_exists(pkg_name=pack, python_version=pv)
            assert pack_exists, f'Не скачался пакет `{pack}` для python `{pv}`'


def test_download_package_1(main):
    packages_list = ['python-dotenv==1.0.0', 'python-dotenv==1.0.1']
    load_packages(packages_list=packages_list)


def test_download_package_2(main):
    packages_list = ['fastapi', 'uvicorn']
    load_packages(packages_list=packages_list)


def test_download_package_3(main):
    packages_list = ['no_exists_package_no_correct_name_@@@@_no_such_exists']
    with pytest.raises(AssertionError):
        load_packages(packages_list=packages_list)
