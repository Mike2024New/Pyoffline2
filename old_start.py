import sys
import subprocess
from pathlib import Path

infrastructure_url_from_git = 'git+https://github.com/Mike2024New/infrastructure.git'
infrastructure_depend_name = 'infrastructure'

header_print = lambda msg: print(f'{"=" * 50}\n{msg}\n{"=" * 50}\n')
"""
Пусковой скрипт для сборки компонентов, после копирования с github.
Устанавливает зависимости из pyproject.toml
Ставит пакет (репозиторий) infrastructure
ВАЖНО:
    1. В этом скрипте не должно быть ни каких библиотек кроме встроенных в python
    2. Перед запуском скрипта должно быть создано виртуальное окружение.
    3. Название папки виртуального окружения .venv
    ( windows: "python -m create venv .venv" или linux: "python3 -m create venv .venv" )
"""

header_print(f'СБОРКА/ПЕРЕСБОРКА ПРОЕКТА')
print(sys.executable)
try:
    header_print(f'1. Проверка uv.')
    try:
        cmd = ['uv', '--version']
        subprocess.run(cmd, capture_output=False)
    except Exception:  # noqa
        header_print(f'1.1. Установка uv')
        cmd = [sys.executable, '-m', 'pip', 'install', 'uv==0.11.18']
        subprocess.run(cmd, capture_output=False)

    if not (Path.cwd() / 'pyproject.toml').exists():
        header_print(f'1.2. Инициализация uv')
        cmd = ['uv', 'init']
        subprocess.run(cmd, capture_output=False)

    header_print(f'2. Установка зависимостей')
    cmd = ['uv', 'sync']
    subprocess.run(cmd, capture_output=False)

    header_print(f'2.1. Удаление старой версии пакета с утилитами')
    try:  # на случай если uv ещё не был установлен
        cmd = ['uv', 'remove', infrastructure_depend_name]
        subprocess.run(cmd, capture_output=False)
    except Exception:  # noqa
        pass

    header_print(f'2.2. Установка пакета с утилитами')
    cmd = ['uv', 'add', infrastructure_url_from_git]
    subprocess.run(cmd, capture_output=False)

except Exception as err:
    raise RuntimeError(
        f'Не удалось установить зависимости по причине {err}\n'
        f'Проверьте что у вас создано виртуальное окружение\n'
        f'За тем выполните `pip install uv` (если он не установлен в системе)\n'
        f'`uv sync` - установка зависимых библиотек'
    )

header_print(f'3. Загрузка python.')
import sys
from layers.python_manager.start import start

start(python_version='3.12')

header_print(f'4. Показать cli интерфейс')
cmd = [sys.executable, 'cli.py']
subprocess.run(cmd, capture_output=False)
header_print(f'СБОРКА ПРОЕКТА ЗАВЕРШЕНА')

# from build import start_build
#
# header_print(f'5. Сборка приложения')
# start_build(name='pyoff')
