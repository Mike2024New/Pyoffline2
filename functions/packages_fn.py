import config
from pathlib import Path
from packaging.version import Version
from wheel_filename import WheelFilename


# парсинг названий пакетов, например: "requests>=2.30.0" -> ("requests", ">=", "2.30.0")
def extract_version_from_package_name(pkg_name: str) -> tuple[str, str | None, str | None]:
    """
    Парсит строку зависимости.
    Возвращает (имя_пакета, оператор, версия)
    Примеры:
        "requests" -> ("requests", None, None)
        "requests==2.31.0" -> ("requests", "==", "2.31.0")
        "requests>=2.30.0" -> ("requests", ">=", "2.30.0")
    :param pkg_name: название пакета
    :return: кортеж вида (название, операнд, версия), либо (название, None, None) если не указана версия
    """
    # Сначала проверяем на URL-формат
    if " @ " in pkg_name:
        name, url = pkg_name.split(" @ ", 1)
        return name, "@", url

    # Ищем оператор
    import re
    pattern = r"""^([a-zA-Z0-9_\-\.]+)([=><!~]+)(.+)$"""
    match = re.match(pattern=pattern, string=pkg_name)
    if match:
        name, op, version = match.groups()
        return name, op, version

    # Только имя
    return pkg_name, None, None


# показать пакеты из архива (те которые есть в наличии) по версиям python: {3.10 : {'fastapi': ['0.136.3'],...}
def get_archive_packages_by_version() -> dict:
    """
    Показать пакеты из папки resources, например:
    3.10 : {'fastapi': ['0.136.3'], 'python-dotenv': ['1.2.2'], 'uvicorn': ['0.49.0']}
    3.12 : {'aiosqlite': ['0.22.1'], 'fastapi': ['0.136.3'], 'python-dotenv': ['1.2.2'], 'uvicorn': ['0.49.0']}
    3.14 : {'fastapi': ['0.136.3'], 'python-dotenv': ['1.2.2'], 'uvicorn': ['0.49.0']}
    3.8 : {'fastapi': ['0.124.4'], 'python-dotenv': ['1.0.1'], 'uvicorn': ['0.33.0']}
    :return: dict
    """
    out_info = {}
    for folder in config.PACKAGES_DIR.iterdir():
        packages = {}
        for package in folder.iterdir():
            name, version = package.name.split('==')
            if not packages.get(name):
                packages[name] = []
            packages[name].append(version)
        for name in packages:
            packages[name] = sorted(packages[name], key=Version)
        out_info[folder.name] = packages
    return out_info


# проверка что пакет в наличии в архиве, по имени пакета и версии Python, например: `fastapi` или с версией `fastapi==0.136.3`
def is_package_archive_exists(pkg_name: str, python_version: str) -> bool:
    """
    Проверка, что пакет есть в архиве
    :param python_version: версия Python
    :param pkg_name: наименование пакета
    :return: True / False ( пакет есть в архиве? )
    """
    pkg_base_name, _, pkg_version = extract_version_from_package_name(pkg_name=pkg_name)
    arcive_packages = get_archive_packages_by_version()
    pkg_base_name = pkg_base_name.replace('-', '_')

    for pv in arcive_packages:
        if python_version != pv:
            continue
        if pkg_base_name in arcive_packages[pv] or pkg_base_name.replace('-', '_') in arcive_packages[pv]:
            # проверка была с учётом ситуации когда например pydantic-settings написан как pydantic_settings
            if pkg_version is None:
                return True
            for versions_list in arcive_packages[pv][pkg_base_name]:
                if pkg_version in versions_list:
                    return True
    return False


def find_wheel(pkg_name: str, python_version) -> Path | None:
    """
    Поиск whl файла пакета в архиве. С учётом версии. Если версия пакета не указана то будет взята максимальная (последняя версия).
    :param pkg_name: название пакета
    :param python_version: версия python
    :return:
    """
    pkg_name, _, pkg_version = extract_version_from_package_name(pkg_name)  # если версия None то будет показан latest
    # сперва найти целевую папку с версиями
    packages = {}
    for folder in config.PACKAGES_DIR.iterdir():
        if folder.name == python_version:
            for file in folder.rglob('*.whl'):
                file_wheel_meta = WheelFilename.parse(file.name)
                wheel_name = file_wheel_meta.project.lower()
                wheel_version = file_wheel_meta.version
                if pkg_name == wheel_name:
                    if pkg_version is not None and wheel_version == pkg_version:
                        return file
                    packages[wheel_version] = file  # сборка версий в словарь
            from packaging.version import Version
            packages_versions = sorted(packages.keys(), key=Version)
            return packages[packages_versions[-1]]  # возвращение самой последней версии
    return None


def parse_package_name(pkg_name: str) -> tuple[str, None, str | None, list[str]]:
    """

    """
    from packaging.requirements import Requirement
    try:
        pkg_data = Requirement(pkg_name)
        name = pkg_data.name
        version = pkg_data.specifier or None
        extras = list(pkg_data.extras) or []
        return str(name), None, str(version), extras
    except Exception as err:
        raise RuntimeError(f'Ошибка парсинга пакета {pkg_name}, текст ошибки: {err}')


if __name__ == '__main__':
    # print(get_archive_packages_by_version())
    # print(is_package_archive_exists(pkg_name='python-dotenv==1.2.2', python_version='3.14'))
    # print(find_wheel(pkg_name='fastapi==0.137.1', python_version='3.12'))
    # print(is_package_archive_exists(pkg_name='pydantic-settings', python_version='3.12'))
    # print(extract_version_from_package_name(pkg_name='fastapi==0.136.3'))
    print(parse_package_name(pkg_name='passlib[argon2]'))
    print(parse_package_name(pkg_name='wheel-filename==2.1.0'))
    # print(new_extras(pkg_name='fastapi[standard,test]'))
