import re
from pathlib import Path
import config
from functions.subprocess_wrapper import run


# Получение exe путей, python доступных в архиве
def get_archive_python_executables() -> list[Path]:
    """Получение путей к исполняемым файлам Python"""
    pythons_list = []
    if config.IS_WINDOWS:
        for python_dir in config.PYTHON_STORAGE_DIR.rglob('python'):
            # для windows (.exe всегда лежит на верхнем уровне):
            if python_dir.is_dir():
                exe_file = python_dir / 'python.exe'
                if exe_file.exists():
                    pythons_list.append(exe_file)
    else:
        # для linux обычно лежит в bin:
        for python_dir in config.PYTHON_STORAGE_DIR.rglob('bin'):
            bin_file = python_dir / 'python'
            if bin_file.exists():
                pythons_list.append(bin_file)
    return pythons_list


# поиск пути к интерпретатору в архиве python, по версии
def get_archive_python_exe_path_by_version(version: str = '3.12') -> Path | None:
    """Поиск пути к интерпретатору в архиве python"""
    pythons_list = get_archive_python_executables()
    for path in pythons_list:
        vers = get_python_version(python_exe_path=path)
        if vers == version:
            return path
    return None


# получение python версии на основании python_exe (через subprocess python --version)
def get_python_version(python_exe_path) -> str | None:
    """
    Получение версии python из исполняемого файла (через subprocess python --version)
    :param python_exe_path: путь к интерпретатору python
    :return: название версии
    """
    try:
        cmd = [python_exe_path, '--version']
        answer = run(cmd, capture_output=True, text=True)
    except Exception as err:
        raise RuntimeError(f'Не удалось получить версию python, ошибка: {err}')

    python_version = re.match(pattern=r'python\s+(3\.\d{1,3})', string=answer.stdout.lower())
    return python_version.group(1) if python_version is not None else None


if __name__ == '__main__':
    print(get_archive_python_executables())
    # print(get_archive_python_exe_path_by_version(version='3.10'))
    # import sys
    # print(get_python_version(python_exe_path=sys.executable))
