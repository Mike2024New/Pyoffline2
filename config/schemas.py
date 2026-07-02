__all__ = [
    'icons_default', 'hidden_default',
]

# схемы для tree значения в конфигурации по умолчанию
icons_default = {
    # Папка
    'directory': '📁',
    # Python
    '.py': '🐍',
    '.pyc': '🐍',
    '.pyo': '🐍',
    '.pyd': '🐍',
    # Документация и текст
    '.md': '📝',
    '.txt': '📄',
    '.rst': '📄',
    '.json': '📄',
    '.toml': '📄',
    '.yaml': '📄',
    '.yml': '📄',
    '.xml': '📄',
    '.html': '📄',
    '.css': '📄',
    '.scss': '📄',
    # Код
    '.js': '📄',
    '.ts': '📄',
    '.c': '📄',
    '.cpp': '📄',
    '.h': '📄',
    '.java': '📄',
    '.go': '📄',
    '.rs': '📄',
    # Изображения
    '.png': '🖼️',
    '.jpg': '🖼️',
    '.jpeg': '🖼️',
    '.gif': '🖼️',
    '.svg': '🖼️',
    '.ico': '🖼️',
    # Архивы
    '.zip': '📦',
    '.tar': '📦',
    '.gz': '📦',
    '.rar': '📦',
    '.7z': '📦',
    # Системное/бинарное
    '.exe': '⚙️',
    '.dll': '⚙️',
    '.so': '⚙️',
    '.dylib': '⚙️',
    '.sh': '⚙️',
    '.bat': '⚙️',
    '.ps1': '⚙️',
    # Прочее
    '.lock': '🔒',
    '.log': '📄',
    '.env': '🔒',
    '.gitignore': '🔒',
    '.dockerignore': '🔒',
    'LICENSE': '📄',
}
hidden_default = {
    'hidden_dirs': [
        '.git', '.venv', '.idea', '__pycache__', '.pytest_cache', '.mypy_cache',
        '*.egg-info', 'logs', 'python_embed', 'python', 'releases'
    ],
    'hidden_files': [
        '*.lock', '.env'
    ],
}
