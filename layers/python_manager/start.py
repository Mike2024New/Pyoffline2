import shutil, subprocess
import config
from layers.python_manager.main import PythonManager


def start(python_version: str = '3.12') -> None:
    """
    Установка python в корень приложения (чтобы можно было скачивать другие версии python через getpybs)
    :param python_version: версия python которая будет скачана с getpybs
    :return: None
    Если по каким то причинам не срабатывает скрипт, то в ручную создать в корне проекта папку python и положить
    в неё стандартный портативный python (standalone)
    """
    # 1. Скачать python если его ещё нет
    PythonManager.download_python(python_version=python_version)
    python_exe_path = PythonManager.get_archive_python_exe_path_by_version(python_version)
    python_exe_folder = python_exe_path.parent

    while True:
        if python_exe_folder.parent.parts[-1] == python_version:
            break
        python_exe_folder = python_exe_folder.parent

    # 2. Скопировать python в папку
    if config.PYTHON_EMBED_DIR.exists():
        shutil.rmtree(config.PYTHON_EMBED_DIR)

    shutil.copytree(str(python_exe_folder), config.PYTHON_EMBED_DIR)

    # # 3. Установка getpybs для того чтобы можно было скачивать версии Python
    cmd = [config.PYTHON_EMBED_EXE, '-m', 'pip', 'install', '--no-warn-script-location', 'getpybs']
    subprocess.run(cmd, check=False, capture_output=True, shell=False)


if __name__ == '__main__':
    start(python_version='3.11')
    # print(config.PYTHON_EMBED_EXE)
