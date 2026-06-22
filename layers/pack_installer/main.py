import subprocess
import uuid
import config
from config import message_bus_add
from pathlib import Path
from time import perf_counter
from functions.toml_manager import TomlManager
from functions.get_orphan_deps import get_orphan_dependencies
from functions import python_fn
from functions import packages_fn
from wheel_filename import WheelFilename

SUBCOMPONENT = 'PACK_INSTALLER'


def get_toml_manager(target_project_path: Path):
    return TomlManager(project_path=target_project_path)


class PackagesManager:
    """
    Простой менеджер пакетов в целевом проекте
    """

    @staticmethod
    def get_packages_from_project(target_project_path: Path) -> list[str]:
        toml_manager = get_toml_manager(target_project_path=target_project_path)
        return toml_manager.list_dependencies()

    @classmethod
    def _is_package_installed(cls, target_project_path: Path, pkg_name: str) -> bool:
        """
        Проверка установлен ли этот пакет уже в целевом проекте или нет
        :param target_project_path: целевой проект
        :param pkg_name: название проверяемого пакета
        :return: True/False
        """
        pkg_parse_name, _, _ = packages_fn.extract_version_from_package_name(pkg_name)
        target_project_python_exe = target_project_path / config.PYTHON_EXE_PATH_POSTFIX

        cmd = [target_project_python_exe, '-m', 'pip', 'list']
        res = subprocess.run(cmd, shell=False, text=True, capture_output=True, cwd=target_project_path)
        pkg_base_name, _, _, _ = packages_fn.parse_package_name(pkg_name)
        for row in res.stdout.splitlines():
            row = row.split(' ')
            pip_list_package, pkg_version = row[0], row[1]
            if pkg_base_name == pip_list_package:
                return True
        return False

    @classmethod
    def install(cls, target_project_path: Path, pkg_name: str) -> None:
        """
        Установка пакета из оффлайн репозитория (папка resources packages), версия подбирается автоматически, на основании
        пути к интерпретатору целевого проекта.
        Обновляет pyproject.toml целевого проекта
        :param target_project_path: целевой проект
        :param pkg_name: название устанавливаемого пакета
        :return: None
        """

        request_id = str(uuid.uuid4())[:8]
        start_time = perf_counter()

        message_bus_add(
            subcomponent=SUBCOMPONENT,
            level='start',
            event='start install package',
            message=f'Установка пакета {pkg_name} в целевой проект.',
            request_id=request_id,
            data={
                'target_dir': target_project_path,
                'package': pkg_name,
            }
        )

        target_project_python_exe = target_project_path / config.PYTHON_EXE_PATH_POSTFIX
        python_version = python_fn.get_python_version(target_project_python_exe)

        # проверка что пакет есть в архиве
        is_pkg_exists_archive = packages_fn.is_package_archive_exists(
            pkg_name=pkg_name,
            python_version=python_version
        )
        if not is_pkg_exists_archive:
            msg_error = f'Пакет `{pkg_name}` для python `{python_version}`, отсутствует в архиве.'
            message_bus_add(
                event='package not found in archive',
                message=msg_error,
                subcomponent=SUBCOMPONENT,
                level='error',
                request_id=request_id,
                error=msg_error,
            )
            raise RuntimeError(msg_error)

        toml_manager = get_toml_manager(target_project_path=target_project_path)
        try:
            # 1. Нужно проверить, что пакет ещё не установлен
            cmd = [target_project_python_exe, '-m', 'pip', 'show', pkg_name]
            subprocess.run(cmd, cwd=target_project_path, capture_output=True, check=False, shell=False)
            pkg_name = pkg_name.replace('-', '_')

            if not target_project_python_exe:
                raise RuntimeError(
                    f'В проекте `{target_project_path}` отстутствует виртуальное окружение, '
                    f'либо папка с ним называется не .venv'
                )

            # получение текущей версии python
            python_version = python_fn.get_python_version(target_project_python_exe)

            wheel_file = packages_fn.find_wheel(
                pkg_name=pkg_name,
                python_version=python_version
            )
            file_wheel_meta = WheelFilename.parse(wheel_file.name)
            # зарегистрировать пакет в toml
            toml_manager.add_dependency(
                pkg_name=file_wheel_meta.project,
                version=file_wheel_meta.version
            )

            cmd = [
                str(target_project_python_exe), '-m', 'pip', 'install',
                '--no-index',  # Не ходить в интернет
                '--find-links', wheel_file.parent,  # Искать здесь
                pkg_name
            ]
            subprocess.run(cmd, check=False, capture_output=True, shell=False)

            message_bus_add(
                subcomponent=SUBCOMPONENT,
                level='stop',
                event=f'finish install package',
                message=f'Пакет `{pkg_name}` успешно установлен в целевой проект.',
                request_id=request_id,
                data={
                    'metric': f'{perf_counter() - start_time:.2f} сек.',
                }
            )
        except Exception as err:
            message_bus_add(
                subcomponent=SUBCOMPONENT,
                level='error',
                error=err,
                event='package install err',
                message=f'Ошибка установки пакета {err}',
                request_id=request_id,
            )
            raise RuntimeError(f'Не удалось установить пакет `{pkg_name}` в `{target_project_path}`, причина: {err}')

    @classmethod
    def uninstall(cls, target_project_path: Path, pkg_name: str) -> None:
        """
        Удаление пакета из целевого проекта. Подчищает за ним пакеты "сироты", если они не используются в других пакетах
        (модифицированный pip uninstall -y <package-name>, с рекурсивным анализом транзитивных зависимостей)
        Обновляет pyproject.toml целевого проекта
        Обновляет pyproject.toml целевого проекта
        :param target_project_path: целевой проект
        :param pkg_name: название удаляемого пакета
        :return: None
        """
        request_id = str(uuid.uuid4())[:8]
        start_time = perf_counter()

        if not cls._is_package_installed(
                target_project_path=target_project_path,
                pkg_name=pkg_name,
        ):
            return

        message_bus_add(
            subcomponent=SUBCOMPONENT,
            level='start',
            event='start remove package',
            message=f'Удаление пакета `{pkg_name}` из целевого проекта',
            request_id=request_id,
            data={
                'target_dir': target_project_path,
                'package': pkg_name,
            }
        )

        try:
            deleted_pkg_name, _, _ = packages_fn.extract_version_from_package_name(pkg_name=pkg_name)
            toml_manager = get_toml_manager(target_project_path=target_project_path)
            packages_from_toml = toml_manager.list_dependencies()

            packages_names_list = []
            for pack in packages_from_toml:
                name, _, _ = packages_fn.extract_version_from_package_name(pkg_name=pack)
                name = name.replace('_', '-')
                packages_names_list.append(name)
            if deleted_pkg_name not in packages_names_list:
                return

            deleted_packages_list = get_orphan_dependencies(
                python_exe_path=target_project_path / config.PYTHON_EXE_PATH_POSTFIX,
                packages_list=packages_names_list,
                deleted_package=deleted_pkg_name,
            )

            for remove_pack in deleted_packages_list:
                cmd = [target_project_path / config.PYTHON_EXE_PATH_POSTFIX, '-m', 'pip', 'uninstall', '-y',
                       remove_pack]
                subprocess.run(cmd, cwd=target_project_path, check=False, capture_output=True, shell=False)

            toml_manager.remove_dependency(pkg_name=deleted_pkg_name)

            message_bus_add(
                subcomponent=SUBCOMPONENT,
                level='stop',
                event=f'finish remove package',
                message=f'Пакет `{pkg_name}` успешно удален из целевого проекта.',
                request_id=request_id,
                data={
                    'metric': f'{perf_counter() - start_time:.2f} сек.',
                }
            )
        except Exception as err:
            message_bus_add(
                subcomponent=SUBCOMPONENT,
                level='error',
                error=err,
                event='package remove err',
                message=f'Ошибка удаления пакета: {err}',
                request_id=request_id,
            )
            raise RuntimeError(f'Не удалось удалить пакет `{pkg_name}` из `{target_project_path}`, причина: {err}')

    @classmethod
    def uninstall_all(cls, target_project_path: Path) -> None:
        """
        Удаление всех пакетов из проекта, очищает dependencies в pyproject.toml
        :param target_project_path: целевой проект
        :return: None
        """
        request_id = str(uuid.uuid4())[:8]
        start_time = perf_counter()

        message_bus_add(
            subcomponent=SUBCOMPONENT,
            level='start',
            event='start remove_all package',
            message=f'Удаление всех пакетов из целевого проекта',
            request_id=request_id,
            data={
                'target_dir': target_project_path,
            }
        )

        try:
            toml_manager = get_toml_manager(target_project_path=target_project_path)
            packages = toml_manager.list_dependencies()
            for pack in packages:
                cls.uninstall(target_project_path, pkg_name=pack)
            toml_manager.clear_dependencies()
            message_bus_add(
                subcomponent=SUBCOMPONENT,
                level='stop',
                event=f'finish remove_all package',
                message='Пакеты успешно удалены из целевого проекта',
                request_id=request_id,
                data={
                    'metric': f'{perf_counter() - start_time:.2f} сек.',
                }
            )
        except Exception as err:
            message_bus_add(
                subcomponent=SUBCOMPONENT,
                level='error',
                error=err,
                event='package remove_all err',
                message=f'Ошибка удаления пакетов: {err}',
                request_id=request_id,
            )
            raise RuntimeError(f'Не удалось очистить пакеты в `{target_project_path}`, причина: {err}')

    @classmethod
    def sync(cls, target_project_path: Path) -> None:
        """
        Установка/переустановка пакетов в проект на основании pyproject.toml
        :param target_project_path: целевой проект
        :return: None
        """
        # получение всех пакетов
        toml_manager = get_toml_manager(target_project_path=target_project_path)
        packages = toml_manager.list_dependencies()
        cls.uninstall_all(target_project_path=target_project_path)

        for pack in packages:
            cls.install(
                target_project_path=target_project_path,
                pkg_name=pack
            )

    @classmethod
    def project_info(cls, target_project_path: Path) -> dict:
        """Общая информация о проекте"""
        depends = cls.get_packages_from_project(target_project_path)
        depends = [
            dep for dep in depends if cls._is_package_installed(
                target_project_path=target_project_path,
                pkg_name=dep)
        ]
        target_project_python_exe = target_project_path / config.PYTHON_EXE_PATH_POSTFIX
        python_version = python_fn.get_python_version(target_project_python_exe)
        return {
            'project_dir': str(target_project_path.as_posix()),
            'project_interpreter': str(target_project_python_exe.as_posix()),
            'python_version': python_version,
            'depends': depends,
        }


if __name__ == '__main__':
    packgages_manager = PackagesManager()
    target_path = Path(r'C:\Users\Projects\Desktop\app')
    # packgages_manager.install(target_project_path=target_path, pkg_name='fastapi')
    # packgages_manager.install(target_project_path=target_path, pkg_name='pydantic')
    # packgages_manager.uninstall(target_project_path=target_path, pkg_name='fastapi')
    # packgages_manager.uninstall(target_project_path=target_path, pkg_name='pydantic')
    packgages_manager.uninstall_all(target_project_path=target_path)

    # # установка пакета в целевой проект + запись в pyproject.toml -> dependencies
    # packgages_manager.install(target_project_path=target_path, pkg_name='pydantic')
    # # удаление пакета из целевого проекта + удаление из pyproject.toml -> dependencies
    # packgages_manager.uninstall(target_project_path=target_path, pkg_name='fastapi')
    # # удаление всех пакетов из целевого проекта (очистка) + очистка  pyproject.toml -> dependencies
    # packgages_manager.uninstall_all(target_project_path=target_path)
