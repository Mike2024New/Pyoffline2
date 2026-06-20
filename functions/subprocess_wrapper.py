import subprocess
from pathlib import Path


def run(
        cmd: list[str],
        cwd: Path | None = None,
        capture_output: bool = False,
        shell: bool = False,
        check: bool = True,
        text: bool = False,
) -> subprocess.CompletedProcess | None:
    """
    Запуск команд через subprocess. Не возвращает результат, а печатает прямо в консоль
    """
    if capture_output:
        res = subprocess.run(cmd, capture_output=capture_output, text=text, cwd=cwd, shell=shell, check=check)
        return res
    subprocess.run(cmd, capture_output=capture_output, text=text, cwd=cwd, shell=shell, check=check)
    return None
