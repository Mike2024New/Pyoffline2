import config
import json
from config.schemas import icons_default, hidden_default

__all__ = ['ICONS', 'HIDDEN_DIRS', 'HIDDEN_FILES']

if not config.TREE_ICONS_CONFIG.exists():
    with open(file=config.TREE_ICONS_CONFIG, mode='w', encoding='utf-8') as f:
        f.write(json.dumps(icons_default, ensure_ascii=False, indent=2))

if not config.TREE_HIDDEN_CONFIG.exists():
    with open(file=config.TREE_HIDDEN_CONFIG, mode='w', encoding='utf-8') as f:
        f.write(json.dumps(hidden_default, ensure_ascii=False, indent=2))

with open(file=config.TREE_ICONS_CONFIG, mode='r', encoding='utf-8') as f:
    ICONS = json.loads(f.read())

with open(file=config.TREE_HIDDEN_CONFIG, mode='r', encoding='utf-8') as f:
    hidden_config = json.loads(f.read())

HIDDEN_DIRS = hidden_config['hidden_dirs']
HIDDEN_FILES = hidden_config['hidden_files']
