from pathlib import Path
from typing import List, Optional
import tomllib
import tomli_w
from config import PYTHON_EXE_PATH_POSTFIX

__all__ = ['TomlManager']


class TomlManager:
    """Менеджер для работы с pyproject.toml, редактирование depends"""

    def __init__(
            self, project_path: Path,
            project_name: str = "MyProject", version: str = "0.1.0", description: str = ""
    ):
        self.python_exe_path = project_path / PYTHON_EXE_PATH_POSTFIX
        self.toml_path = project_path / "pyproject.toml"
        self.data = None
        self._init(project_name=project_name, version=version, description=description)

    # Загружает pyproject.toml
    def _load(self) -> None:
        """Загружает pyproject.toml"""
        if not self.toml_path.exists():
            self._init(project_name="MyProject", version="0.1.0", description="")
        with open(self.toml_path, "rb") as f:
            self.data = tomllib.load(f)

    # Сохраняет pyproject.toml
    def _save(self) -> None:
        """Сохраняет pyproject.toml"""
        with open(self.toml_path, "wb") as f:
            tomli_w.dump(self.data, f)

    # Создаёт минимальный pyproject.toml если его нет
    def _init(self, project_name: str, version: str, description: str) -> None:
        """Создаёт минимальный pyproject.toml если его нет"""
        if self.toml_path.exists():
            return

        self.data = {
            "project": {
                "name": project_name,
                "version": version,
                "description": description,
                "dependencies": [],
            },
            "build-system": {
                "requires": ["setuptools>=61.0"],
                "build-backend": "setuptools.build_meta",
            }
        }
        self._save()

    #
    @staticmethod
    def pkg_normalizer(pkg_name: str):
        return pkg_name.replace('_', '-')

    def add_dependency(self, pkg_name: str, version: Optional[str] = None) -> None:
        """
        Добавляет зависимость в pyproject.toml
        Примеры:
            add_dependency("requests")
            add_dependency("requests", "2.31.0")
        """
        self._load()

        if version:
            dep = f"{pkg_name}=={version}"
        else:
            dep = pkg_name

        dep = self.pkg_normalizer(pkg_name=dep)
        dependencies = self.data.get("project", {}).get("dependencies", [])

        if dep in dependencies:
            return

        dependencies.append(dep)
        self.data["project"]["dependencies"] = dependencies
        self._save()

    def remove_dependency(self, pkg_name: str) -> None:
        """
        Удаляет зависимость из pyproject.toml по имени пакета (без учёта версии).

        Примеры:
            remove_dependency("requests")   # удалит "requests==2.31.0"
            remove_dependency("pydantic")   # удалит "pydantic==2.13.4", но не "pydantic-settings"
        """
        self._load()

        dependencies = self.data.get("project", {}).get("dependencies", [])
        pkg_name = self.pkg_normalizer(pkg_name=pkg_name)
        # Найти точное совпадение имени (до символов '=', '>', '<', '~')
        found = None
        for dep in dependencies:
            # Извлечь имя пакета из строки зависимости
            dep_name = dep.split('=', 1)[0].split('<', 1)[0].split('>', 1)[0].split('~', 1)[0].strip()

            if dep_name == pkg_name:
                found = dep
                break

        if not found:
            return

        dependencies.remove(found)
        self.data["project"]["dependencies"] = dependencies
        self._save()

    def list_dependencies(self) -> List[str]:
        """Возвращает список всех зависимостей"""
        self._load()
        return self.data.get("project", {}).get("dependencies", [])

    def clear_dependencies(self) -> None:
        """Очищает все зависимости"""
        self._load()
        self.data["project"]["dependencies"] = []
        self._save()


if __name__ == "__main__":
    # Пример использования
    toml = TomlManager(project_path=Path(r'C:\Users\Projects\Desktop\demo'))
    print(toml.list_dependencies())
    toml.add_dependency(pkg_name='pydantic-settings')
    toml.add_dependency(pkg_name='pydantic', version='1.2.3')
    toml.remove_dependency(pkg_name='pydantic')  # не тронет pydantic-settings
