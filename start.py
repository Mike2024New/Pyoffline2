import subprocess

infrastructure_url_from_git = 'git+https://github.com/Mike2024New/infrastructure.git'
infrastructure_depend_name = 'infrastructure'

header_print = lambda msg: print(f'{"=" * 50}\n{msg}\n{"=" * 50}\n')
header_print(f'СБОРКА/ПЕРЕСБОРКА ПРОЕКТА')
header_print(f'3. Загрузка python.')
import sys
from layers.python_manager.main import PythonManager

PythonManager.download_python(python_version='3.12')
header_print(f'4. Показать cli интерфейс')
cmd = [sys.executable, 'cli.py']
subprocess.run(cmd, capture_output=False)
header_print(f'СБОРКА ПРОЕКТА ЗАВЕРШЕНА')

# from build import start_build
#
# header_print(f'5. Сборка приложения')
# start_build(name='pyoff')
