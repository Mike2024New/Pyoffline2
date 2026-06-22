import typer, subprocess
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
def version():
    """Получение текущей версии"""
    print(f'[cyan]PyOffline v1.0.0[/cyan]')


@app.command()
def show():
    """
    Архив, доступных python версий и пакетов.
    Пример формата архива:
    {'python_storage': ['3.12', '3.14'], 'packages_storage': {'3.12': {'requests': ['2.34.2']}, '3.14': {'requests': ['2.34.2']}}}
    Примеры команд:
        [yellow]show[/yellow]
    """
    print(PackagesArchive.get_archive_packages_by_version())


@app.command()
def get(packages: list[str]):
    """
    Скачать пакеты с PyPi.org (при наличии соединения с Pypi)
    (под капотом используется pip download)
    Примеры команд:
        [yellow]get fastapi uvicorn[/yellow] - скачает последние версии указанных библиотек
        [yellow]get python-dotenv==1.2.2[/yellow] - скачает конкретную версию пакета
        [yellow]get passlib[bcrypt][/yellow] - скачает пакет + extras указанный в скобках
    """
    if len(packages) == 1:
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
    Скачивание списка библиотек из файла, например из requirements.txt, поддерживаются комментарии вида
    Примеры команд:
        [yellow]get-from ./requirements.txt[/yellow]
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
def update(
        keep: int | None = typer.Option(None, '--keep', '-k')
):
    """
    Получение latest версий (если они есть на PyPi) для всех пакетов всех версий python в архиве.
    можно оставлять только заданное количество последних версий, чтобы архив не разрастался.
    Опции:
        -k (--keep) - оставлять только заданное количество последних версий, а более старые версии удалять.
    Примеры команд:
        [yellow]`update -k 1`[/yellow] - оставит только последнюю latest версию
    """
    PackagesArchive.update(keep=keep)


@app.command()
def add(
        pkg_list: list[str],
        project_path: Path | None = typer.Option(Path.cwd(), "--project-path", "-p", help="Путь к проекту"),
):
    """
    Установка пакета в целевой проект, создает toml если его нет в целевом проекте и добавляет в него пакет.
    Версия python пакета определяется автоматически.
    Параметры (только в режиме разработчика, в обычном режиме указывать их не нужно):
        -p (--project-path) - путь к целевому проекту
        -pkg (--pkg-name) - название пакета, можно несколько через запятую
    Примеры команд:
        [yellow]add fastapi, uvicorn[/yellow] - указать пакеты через пробел или через запятую
        [yellow]add fastapi, uvicorn -p ./app[/yellow] - если другой проект то указать путь к нему через -p
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
    Примеры команд:
        [yellow]remove fastapi, uvicorn[/yellow] - указать пакеты через пробел или через запятую
        [yellow]remove fastapi, uvicorn -p ./app[/yellow] - если другой проект то указать путь к нему через -p
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
    Примеры команд:
        [yellow]remove-all[/yellow] - удаление всех пакетов
        [yellow]remove-all -p ./app[/yellow] - если другой проект то указать путь к нему через -p
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
    Опции:
        -pv (--python-version) версия python
        -rp (--replace-project) заменить venv в существующем проекте если есть.
    Примеры команд:
        [yellow]init -pv 3.12[/yellow] - создаст проект в текущей директории
        [yellow]init -pv 3.12 -rp[/yellow] - пересоздаст проект в текущ директории (флаг -rp)
        [yellow]init -p ./target-project -pv 3.12 -rp[/yellow] - создание проекта по указанному пути
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
    Обязательные параметры:
        python_version - желаемая версия python
    Примеры команд:
        [yellow]get_python 3.12[/yellow] - скачает портативную версию python-standalone 3.12
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
        Примеры команд:
            [yellow]build -n pyoff[/yellow] - создаст дистрибутив с названием pyoff
        """
        from build import start_build
        start_build(name=name)


    @app.command()
    def run_tests(
            v: bool = typer.Option(False, '-v', flag_value=True),
            s: bool = typer.Option(False, '-s', flag_value=True),
    ):
        """
        Запуск тестов.
        Опции:
            -v - подробный режим с путем к каждому модулю
            -s - показывать принты внутри тестов
        Примеры команд:
            [yellow]run-tests -v -s[/yellow] - запуск тестов
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
