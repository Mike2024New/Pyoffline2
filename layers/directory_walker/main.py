from pathlib import Path
from layers.directory_walker import ICONS, HIDDEN_DIRS, HIDDEN_FILES


def get_icon(entry: Path) -> str:
    """Определяет иконку для файла или папки."""
    if entry.is_dir():
        return ICONS['directory']

    # Проверка имя файла без расширения (для LICENSE, README и т.д.)
    if entry.name in ICONS:
        return ICONS[entry.name]

    # Проверка по расширению
    ext = entry.suffix.lower()
    return ICONS.get(ext, '📄')  # По умолчанию документ


def is_hidden_path(entry: Path, hidden_list: set[str]) -> bool:
    """
    Проверка находится ли текущий путь в списке hidden
    :param entry: путь к файлу
    :param hidden_list: множество скрытых файлов, например: {'main.py', 'schemas*' } (не пропустит main.py, и все которые нач на schemas)
    :return: False/True
    """
    name = entry.name
    for pattern in hidden_list:
        if pattern == name:  # точное совпадение
            return True
        elif pattern.startswith('*') and pattern.endswith('*'):  # *substring*
            if pattern.strip('*') in name:
                return True
        elif pattern.startswith('*'):  # *suffix
            if name.endswith(pattern[1:]):
                return True
        elif pattern.endswith('*'):  # prefix*
            if name.startswith(pattern[:-1]):
                return True
    return False


def generate_tree(directory: Path, prefix: str = "", is_last: bool = True, ) -> tuple[list[list[str]], list[Path]]:
    lines = []
    collected_files = []

    try:
        items = sorted(directory.iterdir(), key=lambda x: (x.is_file(), x.name.lower()))
    except PermissionError:
        lines.append([f"{prefix}{'└─ ' if is_last else '├─ '}⚠️ Нет доступа к папке", 'dir'])
        return lines, collected_files

    for i, item in enumerate(items):
        is_last_item = (i == len(items) - 1)
        connector = "└─ " if is_last_item else "├─ "
        icon = get_icon(item)

        if item.is_dir() and is_hidden_path(item, HIDDEN_DIRS):
            lines.append([f"{prefix}{connector}{icon} {item.name} [содержимое скрыто]", 'dir'])
            continue

        if item.is_file() and is_hidden_path(item, HIDDEN_FILES):
            if is_last_item and lines and lines[-1][-1] == 'file':
                lines[-1][0] = lines[-1][0].replace("├─ ", "└─ ")
            continue

        if item.is_dir():
            lines.append([f"{prefix}{connector}{icon} {item.name}", 'dir'])
            child_prefix = prefix + ("    " if is_last_item else "│   ")
            child_lines, child_files = generate_tree(
                directory=item,
                prefix=child_prefix,
                is_last=is_last_item,
            )
            lines.extend(child_lines)
            collected_files.extend(child_files)
        else:
            collected_files.append(item)
            lines.append([f"{prefix}{connector}{icon} {item.name}", 'file'])

    return lines, collected_files


def read_content_from_file(files_list: list[Path]) -> list[str]:
    """Чтение файлов"""
    content_list = []
    for file in files_list:
        content = f'\n\n' + f'=' * 70 + f'\n' + f'  {get_icon(file)} {file}\n' + f'=' * 70 + f'\n\n'
        try:
            with open(file=file, mode='r', encoding='utf-8') as f:
                content += f.read()
                content_list.append(content)
        except Exception as err:
            content += f'Не удалось прочитать файл, причина: {err}'
    return content_list


def show_tree_catalog(root_dir: Path) -> tuple[list[str], list[str]]:
    if not root_dir.exists():
        raise RuntimeError(f"Ошибка: Путь '{root_dir}' не существует.")

    if not root_dir.is_dir():
        raise RuntimeError(f"Ошибка: '{root_dir}' не является папкой.")

    root_icon = get_icon(root_dir)

    tree_lines_raw, files_list = generate_tree(
        directory=root_dir,
        prefix="",
        is_last=True,
    )

    tree_lines = [f"{root_icon} {root_dir.name}"] + [t[0] for t in tree_lines_raw]  # дерево проекта
    content_list = read_content_from_file(files_list=files_list)  # сбор контента (содержимое файлов)
    return tree_lines, content_list


if __name__ == "__main__":
    import config

    tree, files = show_tree_catalog(
        root_dir=config.ROOT_DIR,
    )
    [print(t) for t in tree]
    [print(f) for f in files]
