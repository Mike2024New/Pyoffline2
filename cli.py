import typer
from rich import print
import config
from pathlib import Path
from layers.python_manager.main import PythonManager
from layers.archive_manager.main import PackagesArchive
from layers.pack_installer.main import PackagesManager

app = typer.Typer(
    no_args_is_help=True,
    # если пользователь дал команду без аргументов то не падать с ошибкой а показать справку
    rich_markup_mode='rich',
    # добавить rich панели (группировка комманд по заголовкам)
    add_completion=False,  # убрать блок option в всплывающем меню
)


@app.callback()
def main():
    """CLI интерфейс"""


@app.command()
def show():
    """
    Архив, доступных python версий и пакетов [yellow]show[/yellow]
    Пример формата архива:
    {'python_storage': ['3.12', '3.14'], 'packages_storage': {'3.12': {'requests': ['2.34.2']}, '3.14': {'requests': ['2.34.2']}}}
    """
    print(PackagesArchive.get_archive_packages_by_version())


@app.command()
def get(packages: list[str]):
    """
    Скачать пакеты с PyPi.org
    (под капотом используется pip download)
    Пример комманды: [yellow]get requests uvicorn[/yellow]
    """
    if len(packages) == 1:
        # packages = packages[0].replace(',', ' ').split()
        packages = [p.strip().rstrip(',') for p in packages if p.strip()]
    try:
        PackagesArchive.download(packages_list=packages)
    except Exception:  # noqa
        pass


@app.command()
def get_from(
        file_name: str,
):
    """
    Скачивание списка библиотек из файла, например из requirements.txt, поддерживаются комментарии вида #
    Пример команды: [yellow]get-from ./reuirements.txt[/yellow]
    """
    file_name = Path(file_name)
    if not file_name.exists():
        print(f'[red]Файл `{file_name}` не найден.[/red]')
        return
    with open(file=file_name, mode='r', encoding='utf8') as f:
        text = f.read()
        x = text.splitlines()
        packages_list = []
        for i in x:
            if i and i[0].isalpha():
                packages_list.append(i.split()[0].replace(',', ''))
        try:
            PackagesArchive.download(packages_list=packages_list)
        except Exception:  # noqa
            pass


@app.command()
def add(
        pkg_list: list[str],
        project_path: Path | None = typer.Option(Path.cwd(), "--project-path", "-p", help="Путь к проекту"),
):
    """
    Установка пакета в целевой проект, создает toml если его нет в целевом проекте и добавляет в него пакет.
    Версия python пакета определяется автоматически.
    Параметры:
        -p (--project-path) - путь к целевому проекту
        -pkg (--pkg-name) - название пакета, можно несколько через запятую
    Пример команды:
        [yellow]add fastapi, uvicorn -p ./app[/yellow]
    """

    if not config.EXE_MODE and project_path is None:
        print(f'[yellow]Установка/удаление пакетов в режиме разработчика доступна через параметр -p[/yellow]')
        return

    project_path = project_path if project_path else Path.cwd()

    for pkg in pkg_list:
        PackagesManager.install(
            target_project_path=Path(project_path),
            pkg_name=pkg,
        )


@app.command()
def remove(
        pkg_list: list[str],
        project_path: Path | None = typer.Option(None, "--project-path", "-p", help="Путь к проекту"),
):
    """
    Удаление пакетов из целевого проекта, удаляет пакет из toml проекта.
    Версия python пакета определяется автоматически.
    Параметры:
        -p (--project-path) - путь к целевому проекту
        -pkg (--pkg-name) - название пакета, можно несколько через запятую
    Пример команды:
        [yellow]remove fastapi, uvicorn -p ./app[/yellow]
    """

    if not config.EXE_MODE and project_path is None:
        print(f'[yellow]Установка/удаление пакетов в режиме разработчика доступна через параметр -p[/yellow]')
        return

    project_path = project_path if project_path else Path.cwd()
    for pkg in pkg_list:
        print(pkg)
        PackagesManager.uninstall(
            target_project_path=Path(project_path),
            pkg_name=pkg,
        )


@app.command()
def remove_all(
        project_path: Path | None = typer.Option(None, "--project-path", "-p", help="Путь к проекту"),
):
    """
    Удаление всех пакетов из целевого проекта, очищает toml проекта.
    Версия python пакета определяется автоматически.
    Параметры:
        -pkg (--pkg-name) - название пакета, можно несколько через запятую
    Пример команды:
        [yellow]add -p C:/Users/Projects/app --pkg fastapi[/yellow]
        [yellow]remove-all -p ./app[/yellow]
    """

    if not config.EXE_MODE and project_path is None:
        print(f'[yellow]Установка/удаление пакетов в режиме разработчика доступна через параметр -p[/yellow]')
        return

    project_path = project_path if project_path else Path.cwd()
    PackagesManager.uninstall_all(target_project_path=Path(project_path))


@app.command()
def init(
        project_path: Path | None = typer.Option(None, "--project-path", "-p", help="Путь к проекту"),
        python_version: str | None = typer.Option(..., '-pv', '--python-version'),
        replace_project: bool = typer.Option(False, '-rp', '--replace-project', is_flag=True),
):
    """
    Создание проекта виртуального окружения (папка .venv в корне проекта).
    Пример команды:
        [yellow]init ./app -pv 3.12 -rp[/yellow]
        (создать проект на python 3.12, заменив существующий)
    Обязательные аргументы:
        project_path целевая директория
    Опции:
        -pv (--python-version) версия python
        -rp (--replace-project) заменить venv в существующем проекте если есть.
    """

    if not config.EXE_MODE and project_path is None:
        print(f'[yellow]Установка/удаление пакетов в режиме разработчика доступна через параметр -p[/yellow]')
        return

    project_path = project_path if project_path else Path.cwd()

    PythonManager.create(
        project_path=Path(project_path),
        python_version=python_version,
        replace_project=replace_project,
    )


@app.command()
def get_python(python_version: str):
    """
    Загрузка python с https://github.com/astral-sh/python-build-standalone/releases
    Обязательный параметр python_version.
    Пример команды: [yellow]get_python 3.12[/yellow]
    """
    PythonManager.download_python(python_version=python_version)


@app.command()
def folder():
    """Открыть домашнюю папку приложения"""
    from infrastructure.path_utils.open_folder import open_folder
    open_folder(config.ROOT_DIR)


# доступно только в режиме разработки
if not config.EXE_MODE:
    @app.command()
    def build(
            name: str = typer.Option('pyoff', '--name', '-n')
    ):
        """
        Сборка exe (bin) приложения.
        Опции:
            -n (--name) - название приложения.
        """
        from build import start_build
        start_build(name=name)


    @app.command()
    def run_tests(
            v: bool = typer.Option(False, '-v', flag_value=True),
            s: bool = typer.Option(False, '-s', flag_value=True),
    ):
        import subprocess
        """
        Запуск тестов.
        Опции:
            -v - подробный режим с путем к каждому модулю
            -s - показывать принты внутри тестов 
        """
        cmd = ['pytest']

        # # добавление опций / add options
        cmd.extend(['-v']) if v else cmd.extend([])
        cmd.extend(['-s']) if s else cmd.extend([])
        result = subprocess.run(cmd, cwd=config.ROOT_DIR)

        if result.returncode != 0:
            print(
                f"[red]Тесты не пройдены (код {result.returncode})[/red]")
            return False
        else:
            print("[green]Все тесты пройдены[/green]")
            return True

if __name__ == '__main__':
    app()
