import sys
import tempfile, shutil, uuid, tarfile
import config
from config import message_bus_add
from pathlib import Path
from functions import subprocess_wrapper
from functions import python_fn
from time import perf_counter

SUBCOMPONENT = 'python_manager'


class PythonManager:

    @staticmethod
    def create(
            project_path: Path,
            python_version: str, replace_project: bool = False,
            python_exe_path: Path | None = None, venv_folder_name: str = '.venv'
    ) -> None:
        """
        Создание проекта с виртуальным .venv окружением, в целевой директории.

        :param project_path: целевой путь к создаваемому проекту
        :param python_version: желаемая версия python
        :param replace_project: заменить проект если он уже существует? ОСТОРОЖНО, ВЫНОСИТ ВСЮ ПАПКУ .venv
        :param python_exe_path: указать путь к интерпретатору на прямую,
        :param venv_folder_name: название папки виртуального окружения (Для совместимости с другими модулями лучше оставить .venv)
        :return: None
        """
        request_id = str(uuid.uuid4())[:8]
        start_time = perf_counter()
        message_bus_add(
            subcomponent=SUBCOMPONENT,
            level='start',
            event='start create project',
            message=f'Создание проекта `{project_path}`, python=`{python_version}`',
            request_id=request_id,
            data={
                'python_version': python_version,
                'replace_project': replace_project,
                'python_exe_path': python_exe_path,
                'venv_folder_name': venv_folder_name,
                'project_dir': project_path,
            }
        )
        # 1. Поиск интерпретатора
        python_exe_path = python_fn.get_archive_python_exe_path_by_version(version=python_version)
        if python_exe_path is None:
            message_error = f'Не найден python.exe для версии {python_version}'
            message_bus_add(
                subcomponent=SUBCOMPONENT,
                level='error',
                event='no find python exe path',
                message=f'Не найден путь к интерпретатору python={python_version}',
                request_id=request_id,
                error=message_error,
            )
            raise RuntimeError(message_error)

        # 2. Создание проекта
        venv_path_project = project_path / config.PYTHON_EXE_PATH_POSTFIX
        if venv_path_project.exists():
            if replace_project and project_path.exists():
                shutil.rmtree(project_path / venv_folder_name)
            else:
                message_error = f'Проект `{project_path}` уже существует, для пересоздания установите галочку replace_project.'
                message_bus_add(
                    subcomponent=SUBCOMPONENT,
                    level='error',
                    event='project already exists',
                    message=f'Ошибка создания проекта: {message_error}',
                    request_id=request_id,
                    error=message_error,
                )
                raise RuntimeError(message_error)

        project_path.mkdir(parents=True, exist_ok=True)

        # 3. Создание venv
        try:
            cmd = [str(python_exe_path), '-m', 'venv', venv_folder_name]
            subprocess_wrapper.run(cmd, cwd=project_path, check=False)

            message_bus_add(
                subcomponent=SUBCOMPONENT,
                level='stop',
                event='end create project',
                message=f'Проект создан `{project_path}`',
                request_id=request_id,
                data={
                    'metric': f'{perf_counter() - start_time:.2f} сек.',
                }
            )

        except Exception as err:
            message_bus_add(
                subcomponent=SUBCOMPONENT,
                level='error',
                event='error create project',
                message=f'Ошибка создания проекта {err}',
                error=err,
                request_id=request_id,
            )

    @staticmethod
    def get_archive_python_executables() -> list[Path]:
        """
        Получение exe путей, python доступных в архиве (доступно только для windows)
        :return: cписок найденых путей из resources/pythons
        """
        return python_fn.get_archive_python_executables()

    @staticmethod
    def get_archive_python_exe_path_by_version(version: str | None = None) -> Path | None:
        """
        Поиск пути к интерпретатору в архиве python
        :param version:
        :return: путь к Python.exe или None если не найден
        """
        return python_fn.get_archive_python_exe_path_by_version(version=version)

    @staticmethod
    def download_python(python_version: str):
        """
        Скачивание python с: https://github.com/astral-sh/python-build-standalone/releases
        :param python_version: версия python например 3.10, 3.14
        :return:
        """
        request_id = str(uuid.uuid4())[:8]
        start_time = perf_counter()

        if python_fn.get_archive_python_exe_path_by_version(python_version) is not None:
            message_bus_add(
                subcomponent=SUBCOMPONENT,
                level='warning',
                event='python already exists in archive',
                message=f'python {python_version} уже есть в архиве',
                request_id=request_id,
            )
            return

        if not config.PYTHON_EMBED_EXE.exists():
            if config.EXE_MODE:
                raise RuntimeError(
                    f'Удален python приложения. Создайте в корне проекта папку python с интерпретатором внутри.'
                )
            # для загрузки python в режиме разработчика
            python_path_exe = sys.executable
        else:
            python_path_exe = config.PYTHON_EMBED_EXE

        message_bus_add(
            subcomponent=SUBCOMPONENT,
            level='start',
            event='start download python',
            message=f'Закачка python {python_version} началась',
            request_id=request_id,
            data={
                'python_version': python_version,
                'python_system': python_path_exe,
            }
        )

        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                # 1. Скачивание python через python который установлен в корне проекта
                cmd = [
                    python_path_exe, '-m', 'getpybs', '--python-version', python_version, '--dest',
                    temp_dir
                ]
                subprocess_wrapper.run(cmd, check=False, cwd=config.ROOT_DIR)

                # 2. Сбор скачанных python файлов
                for file in temp_path.rglob('*.gz'):
                    with tarfile.open(file, 'r:gz') as tar:
                        # извлечение python в целевую папку
                        python_save_path = config.PYTHON_STORAGE_DIR / python_version
                        if python_save_path.exists():
                            shutil.rmtree(python_save_path)  # удаление старого интерпретатора (обновление python)
                        tar.extractall(path=config.PYTHON_STORAGE_DIR / python_version, filter='fully_trusted')

        except Exception as err:
            message_bus_add(
                subcomponent=SUBCOMPONENT,
                level='error',
                error=err,
                event='python download error',
                message=f'Ошибка загрузки python: {err}',
                request_id=request_id,
            )
            raise RuntimeError(f'Не удалось скачать python, причина: {err}')

        message_bus_add(
            subcomponent=SUBCOMPONENT,
            level='stop',
            event=f'python downloaded',
            message=f'Python `{python_version}` успешно загружен',
            request_id=request_id,
            data={
                'metric': f'{perf_counter() - start_time:.2f} сек.',
            }
        )


if __name__ == '__main__':
    # PythonManager().create(
    #     project_path=Path(r'C:\Users\Projects\Desktop\app'),
    #     replace_project=True, python_version='3.12'
    # )
    PythonManager().download_python(python_version='3.10')
    # print(PythonManager().get_archive_python_executables())
    # print(PythonManager().get_archive_python_exe_path_by_version(version='3.10'))
