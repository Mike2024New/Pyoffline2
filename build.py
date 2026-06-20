from infrastructure.builder.main import build, BuildParameters
import config
from pathlib import Path


# запуск сборки приложения
def start_build(name: str = 'pyoff', open_folder: bool = True) -> Path:
    """
    Сборка исполняемого файла приложения
    :param name: наименование приложения
    :param open_folder: открывать ли папку с приложением после сборки
    :return:
    """
    build_settings = BuildParameters(
        name=name,
        entry_point_path=config.ROOT_DIR / 'cli.py',
        one_file=True,
        create_resources_symlink=False,
        open_folder=open_folder,
        # копирование доп папок (в данном случае python)
        copy_dirs=[
            (config.PYTHON_EMBED_DIR, config.PYTHON_EMBED_DIR.parts[-1],),  # папка с системным python
            (config.RESOURCES_DIR, config.RESOURCES_DIR.parts[-1],)  # папка с ресурсами (python_storage, пакеты)
        ]

    )
    return build(build_settings)


if __name__ == '__main__':
    start_build()
