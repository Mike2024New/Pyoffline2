import uuid
import sys
import platform
from pathlib import Path

COMPONENT_ID = str(uuid.uuid4())[:8]
VERSION = '0.1.0'


def get_platform_name():
    """Определение целевой платформы для путей PYTHON_STORAGE и PACKAGES_STORAGE (windows/linux/macos)"""
    if sys.platform == 'win32':
        return 'windows-x86_64'
    elif sys.platform == 'darwin':
        return 'macos-x86-64'
    else:
        arch = platform.machine()
        return f'linux-{arch}-gnu'


__all__ = [
    'PYTHON_STORAGE_DIR', 'PYTHON_EXE_PATH_POSTFIX', 'PACKAGES_DIR',
    'message_bus_add',
    'IS_WINDOWS', 'COMPONENT_ID',
    'ROOT_DIR',
]

IS_WINDOWS = 'windows' in platform.system().lower()

# для сборщика (pyinstaller)
EXE_MODE = getattr(sys, 'frozen', False)

# определение корневой точки приложения
ROOT_DIR = Path(sys.executable).parent if EXE_MODE else Path(__file__).parent.parent

platform_name = get_platform_name()

# системный python
PYTHON_EMBED_DIR = ROOT_DIR / 'python_embed'
if IS_WINDOWS:
    PYTHON_EMBED_EXE = PYTHON_EMBED_DIR / 'python.exe'
else:  # для linux
    PYTHON_EMBED_EXE = PYTHON_EMBED_DIR / 'bin' / 'python'

# директория с ресурсами
RESOURCES_DIR = ROOT_DIR / 'resources'

# магазин версий Python
PYTHON_STORAGE_DIR = RESOURCES_DIR / 'python_storage' / platform_name
PYTHON_STORAGE_DIR.mkdir(exist_ok=True, parents=True)

# архив
PACKAGES_DIR = RESOURCES_DIR / 'packages_storage' / platform_name
PACKAGES_DIR.mkdir(exist_ok=True, parents=True)

# папка с логами
LOGS_DIR = ROOT_DIR / 'logs'
LOGS_FILE_PATH = LOGS_DIR / 'log.jsonl'
LOGS_DIR.mkdir(exist_ok=True, parents=True)

PYTHON_EXE_PATH_POSTFIX = 'null'
if IS_WINDOWS:
    PYTHON_EXE_PATH_POSTFIX = Path('.venv') / 'Scripts' / 'python.exe'
else:
    PYTHON_EXE_PATH_POSTFIX = Path('.venv') / 'bin' / 'python'

# шина сообщений
from infrastructure.message_bus.factory import message_bus_factory, MessagePrintSettings, FileLogSettings

message_bus_add = message_bus_factory(
    component_id=COMPONENT_ID,
    component_name='PyOffline',
    print_message=True,
    message_print_settings=MessagePrintSettings(
        print_date=True,
        raw_message=False,
        ignore_levels=[],
        ignore_levels_invers=False,
    ),
    file_log_json_path=LOGS_FILE_PATH,
    file_log_settings=FileLogSettings(
        max_files=10,
        max_size_mb=10,
        rotation_disable=False,
    )
)
