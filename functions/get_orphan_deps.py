# чтобы получить список зависимостей именно целевого проекта, код нужно выполнить от целевого проекта
source = """from importlib.metadata import metadata, PackageNotFoundError
import json,sys


def get_all_deps(pkg_name: str, visited: set = None) -> set:
    # возвращает все зависимости указанных пакетов
    visited = visited or set()
    if pkg_name in visited:
        return set()
    visited.add(pkg_name.replace('_', '-'))

    try:
        reqs = metadata(pkg_name).get_all('Requires-Dist', []) or []
    except PackageNotFoundError:
        return set()

    deps = set()
    for req in reqs:
        if 'extra ==' not in req:
            dep = req.split()[0].split('>')[0].split('<')[0].split('=')[0].split('[')[0].split(';')[0].split('~')[0]
            dep = dep.replace('_', '-')
            deps.add(dep)
            deps.update(get_all_deps(dep, visited))
    return deps

packages_list = json.loads(sys.argv[1]) # список пакетов (обычно из pyproject.toml dependencies)
packages_result = {}
for pack in packages_list:
    packages_result[pack] = list(get_all_deps(pkg_name=pack))  # set -> list для JSON

print(json.dumps(packages_result))
"""

import subprocess
from pathlib import Path

__all__ = ['get_orphan_dependencies']


def _get_transitive_dependencies(python_exe_path: Path, packages_list: list[str]) -> dict[str, list[str]]:
    """
    Парсер пакетов целевого проекта
    Возвращает транзитивные зависимости для каждого пакета из списка (например для пакетов из pyproject.toml dependencies.

    :param python_exe_path: путь к интерпретатору python, например: C:/Users/demo/.venv/Scripts/python.exe
    :param packages_list: список пакетов для изучения, например: ['typer', ]
    :return: Вернет словарь с всем зависимостями этого пакета, например для ['typer', ], результат будет:
    {
        'typer': ['annotated-doc', 'colorama', 'pygments', 'markdown-it-py', 'shellingham', 'mdurl', 'rich']
    }
    где внутри списка находятся все его скрытые зависимости, которые не видит "pip uninstall -y", удаляя только верх.
    """
    global source
    import json
    cmd = [python_exe_path, '-c', source, json.dumps(packages_list)]
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)

    return json.loads(result.stdout)


def get_orphan_dependencies(python_exe_path: Path, packages_list: list[str], deleted_package: str) -> list[str]:
    """
    Возвращает список зависимостей, которые станут "сиротами" после удаления пакета
    (контролирует, пересечение зависимостей в разных пакетах и не удалит случайно лишнего)
    :param python_exe_path: путь к интерпретатору python, например: C:/Users/demo/.venv/Scripts/python.exe
    :param packages_list: список пакетов для изучения, например: ['typer', ] - обычно этот список получается из pyproject.toml dependencies
    :param deleted_package: удаляемый пакет (например `fastapi` из примера выше)
    :return: список зависимостей "сирот", которые больше ни где не используются.
    (это нужно для чистки за pip uninstall который удаляет только верхний слой,
    """
    if not python_exe_path.exists():
        raise RuntimeError(f'Указан путь к несуществующему проекту `{python_exe_path}`')
    packages_dict = _get_transitive_dependencies(
        python_exe_path=python_exe_path,
        packages_list=packages_list,
    )

    if deleted_package not in packages_dict:
        raise RuntimeError(f'Пакет `{deleted_package}`, отсутствует в коллекции пакетов `{packages_dict.keys()}`')

    no_deleted_depends = set()
    deleted_packages_list = []

    # удаляемый пакет исключить из множетсва оставляемых пакетов
    removed_deps = packages_dict.pop(deleted_package)

    # объединение всех зависимостей, кроме удаляемого пакета
    for key in packages_dict:
        no_deleted_depends.update(packages_dict[key])

    # оставить только уникальные пакеты (те которые не используются в других зависимостях)
    is_del_package_used_other_packages = False
    for pack in removed_deps:
        if pack not in no_deleted_depends:
            if pack in packages_dict.keys():  # если подзависимость является названием другого пакета
                continue
            deleted_packages_list.append(pack)
        if deleted_package in no_deleted_depends:
            is_del_package_used_other_packages = True
    if not is_del_package_used_other_packages:
        deleted_packages_list.append(deleted_package)
    return deleted_packages_list


if __name__ == '__main__':
    res = get_orphan_dependencies(
        python_exe_path=Path(r'C:\Users\Projects\Desktop\app\.venv\Scripts\python.exe'),
        deleted_package='fastapi',
        packages_list=['pyaudio', 'print(123)'],  # инъекции убраны через sys.argv (123 не выполнится)
    )
    print(res)
