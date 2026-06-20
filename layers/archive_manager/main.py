from pathlib import Path
import re, sys, string, shutil, tempfile, requests, uuid
import config
from config import message_bus_add
from packaging.version import Version
from packaging.requirements import Requirement
from wheel_filename import WheelFilename
from functions import python_fn, packages_fn, subprocess_wrapper
from concurrent.futures import ThreadPoolExecutor, as_completed
from time import sleep, perf_counter

# конфигурации, вынести потом в отдельный config.json
DOWNLOAD_MAX_WORKERS = 5
DOWNLOAD_TIMEOUT = 0.3
DOWNLOAD_PYPI_URL = 'https://pypi.org/'


class PackagesArchive:
    @staticmethod
    def ping_pypi() -> bool:
        """Проверка соединения с PyPi"""
        try:
            status = requests.get(url=DOWNLOAD_PYPI_URL).status_code
            return status == 200
        except Exception:  # noqa
            return False

    # получение списка актуальных версий пакета, на PyPi
    @staticmethod
    def get_pypi_available_versions(pkg_name: str, python_version: str, no_alpha: bool = False) -> list[str]:
        """
        Получение актуальных пакетов для текущей версии python.
        Кидает запрос с нереалистичным названием версии пакета, и pip на ошибку выдает список доступных версий именно для этой версии
        :param pkg_name: наименование пакета
        :param python_version: версия пакета
        :param no_alpha: не показывать alpha, beta версии вида `0.1.0a1`
        :return: отсортированный список доступных версий, например: [ '0.2.5', '1.99', '2.0a1', '2.0.0', ]
        """
        cmd = [
            sys.executable, '-m', 'pip', 'download', f"{pkg_name}==99999999",
            '--no-deps', '--no-clean',
            '--python-version', f'{python_version}'
        ]
        answer = subprocess_wrapper.run(cmd, capture_output=True, text=True, check=False)
        match = re.search(r'\(from versions: (.*?)\)', answer.stderr)
        if match:
            if match.group(1).lower() == 'none':
                return []
        versions = []
        if no_alpha:
            if match:
                for v in match.group(1).split(','):
                    if any(l in v for l in (string.ascii_lowercase + string.ascii_uppercase)):
                        continue
                    versions.append(v.strip())
        else:
            versions = [v.strip() for v in match.group(1).split(',')] if match else []
            try:
                versions = sorted(versions, key=Version)
            except Exception:  # noqa
                pass
        return versions

    # получение последней версии пакета, например '3.10.1'
    @classmethod
    def get_pypi_latest_version(cls, pkg_name: str, python_version: str, no_alpha: bool = False) -> str | None:
        """
        Получение последней версии пакета
        :param pkg_name: наименование пакета
        :param python_version: версия пакета
        :param no_alpha: не показывать alpha, beta версии вида `0.1.0a1`
        :return: последняя актуальная версия пакета на PyPi.
        """
        versions = cls.get_pypi_available_versions(
            pkg_name=pkg_name,
            python_version=python_version,
            no_alpha=no_alpha,
        )
        if versions:
            return versions[-1]
        return None

    # скачивание пакетов с PyPi, в несколько потоков с ограничениями MAX_WORKERS, TIMEOUT (чтобы не перегружать PyPi)
    @classmethod
    def download(cls, packages_list: list[str]) -> None:
        """
        Загрузка пакетов.
        :param packages_list: список пакетов к установке, например ['fastapi==0.136.3', 'uvicorn']
        :return: список сообщений об установке, например
        [
            {
                'status' : True, 'message' : 'Пакет fastapi==0.136.3` установлен',
                'status' : False, 'message' : 'Пакет fastapi==0.136.4` неустановлен, не найдена версия',
            }
        ]
        """
        request_id = str(uuid.uuid4())[:8]
        start_time = perf_counter()
        # проверка что сервер PyPi доступен
        if not cls.ping_pypi():
            message_bus_add(
                level='error',
                subcomponent='archive_manager',
                message=f'Нет соединения с PyPi.',
                event='no connect PyPi server',
                error='Нет соединения с сервером PyPi',
            )
            raise RuntimeError('Нет соединения с сервером PyPi')

        tasks = []
        python_exe_paths_list = python_fn.get_archive_python_executables()
        if not python_exe_paths_list:
            message_bus_add(
                level='warning',
                subcomponent='archive_manager',
                message=f'Отсутствуют python дистрибутивы в python_storage : {config.PYTHON_STORAGE_DIR}.',
                event='no find python distributives',
            )
            return

        for python_exe_path in python_exe_paths_list:
            for pack in packages_list:
                tasks.append((pack, python_exe_path))

        packages_order = len(tasks)

        message_bus_add(
            level='start',
            subcomponent='archive_manager',
            message=f'Начало загрузки списка пакетов, всего ожидается {packages_order} пакетов (с учётом {len(python_exe_paths_list)} версий Python)',
            event='start download packages list',
        )

        packages_downloaded = 0
        with ThreadPoolExecutor(max_workers=DOWNLOAD_MAX_WORKERS) as executor:
            futures = []
            for i, (pack, path) in enumerate(tasks):
                # Задержка перед отправкой каждой задачи, чтобы не додосить PiPy одновременными запросами
                sleep(DOWNLOAD_TIMEOUT)

                future = executor.submit(
                    cls._download,
                    pkg_name=pack,
                    python_exe_path=path,
                    request_id=request_id,
                )
                futures.append(future)

            for future in as_completed(futures):
                res = future.result()
                if res:
                    packages_downloaded += 1

        message_bus_add(
            level='stop',
            subcomponent='archive_manager',
            message=f'Загрузка пакетов завершена, загружено: {packages_downloaded}/{packages_order}',
            event='finish download packages list',
            data={'metric': f'{perf_counter() - start_time:.2f} сек.'}
        )

    # проверка что пакет есть в архиве, по имени пакета и версии python
    @staticmethod
    def is_package_archive_exists(pkg_name: str, python_version: str) -> bool:
        """
        проверка что пакет есть в архиве
        :param python_version: версия python
        :param pkg_name: наименование пакета
        :return: True/False
        """
        return packages_fn.is_package_archive_exists(pkg_name=pkg_name, python_version=python_version)

    # получение списка пакетов из архива
    @staticmethod
    def get_archive_packages_by_version(
            python_versions: list[str] | None = None, packages: list[str] | None = None
    ) -> dict:
        """
        Получение списка пакетов из архива
        :param packages: список пакетов для фильтрация по имени
        :param python_versions: получение пакетов для конкретной версии python
        :return:
        """
        data = {}
        python_execute_paths = python_fn.get_archive_python_executables()
        versions = [python_fn.get_python_version(exe) for exe in python_execute_paths]
        data['python_storage'] = versions
        data['packages_storage'] = packages_fn.get_archive_packages_by_version()

        # отдать сырые данные без фильтрации
        if not python_versions and not packages:
            return data

        # фильтры
        out_data = data
        for pv in data:
            pack_data = {}
            # фильтрация по версиям python
            if python_versions and not any(v == pv for v in python_versions):
                continue

            # фильтрация по имени пакета
            for pack in data[pv]:
                if packages:
                    if any(p == pack for p in packages):
                        pack_data[pack] = data[pv][pack]
                else:
                    pack_data[pack] = data[pv][pack]

            if pack_data:
                out_data[pv] = pack_data

        return out_data

    @staticmethod
    def _pre_download_package(python_exe_path: Path, pkg_name: str, python_version: str) -> tuple[str, str | None]:
        """
        Предпросмотр версии пакета который скачается. В частности для таких названий как fastapi>=0.136.1,<0.136.3
        Если не удалось получить версию пакета, то вернет, название пакета.
        Примеры:
        pkg_name = "fastapi", вернет ( fastapi, "0.136.3" ), название и версию которую скачает
        pkg_name = "fastapi==9999.9999.9999", вернет ( fastapi, None ), так как не нашел версию для него

        :param python_exe_path: интерпретатор
        :param pkg_name: наименование пакета
        :param python_version:  версия python
        :return: (наименование пакета, версия пакета)
        ( Это костыль, но сделанный в обход решения проблемы PyPi.api.json, где нет разбора пакетов именно по версиям python.)
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            cmd = [
                str(python_exe_path), '-m', 'pip', 'download', pkg_name, '--no-deps', '--no-clean',
                '--python-version', f'{python_version}', '-d', str(temp_dir)
            ]
            subprocess_wrapper.run(cmd, check=False, text=True, capture_output=True)

            # если папка пуста, значит whl не найден
            is_empty = not any(temp_path.rglob('*'))
            if is_empty:
                return pkg_name, 'no whl'

            for file in temp_path.rglob('*whl'):
                wheel_info = WheelFilename.parse(file.name)
                downloaded_pkg_name = wheel_info.project
                downloaded_pkg_version = wheel_info.version
                return downloaded_pkg_name, downloaded_pkg_version

            # проверка, вероятно пришёл tar.gz (то есть файл не собран в .whl)
            for _ in temp_path.rglob('*tar.gz'):
                return pkg_name, 'no whl'

            pkg_name = str(Requirement(pkg_name).name)
            return pkg_name, None

    # скачивание пакета (атомарная операция)
    @classmethod
    def _download(cls, pkg_name: str, python_exe_path: Path, request_id: str) -> bool:
        start_time = perf_counter()
        python_version = python_fn.get_python_version(python_exe_path=python_exe_path)

        message_bus_add(
            level='start',
            subcomponent='archive_manager',
            message=f'Загрузка пакета `{pkg_name}` для python_version=={python_version}',
            event='start download package',
            request_id=request_id,
        )

        # предварительно скачать пакет, чтобы посмотреть его версию
        pkg_base_name, pkg_version = cls._pre_download_package(
            python_exe_path=python_exe_path,
            pkg_name=pkg_name,
            python_version=python_version,
        )

        if pkg_version == 'no whl':
            available_versions = cls.get_pypi_available_versions(pkg_name=pkg_base_name, python_version=python_version)
            if not available_versions:
                message = f'Пакет `{pkg_base_name}`, для python==`{python_version}`: не существует.'
            else:
                message = (
                    f'Пакет `{pkg_name}` для python==`{python_version}` не найден готовый .whl., '
                    f'на PyPi.org доступны версии для компиляции из исходников {available_versions}'
                )

            message_bus_add(
                level='error',
                subcomponent='archive_manager',
                message=message,
                event='package not exists',
                request_id=request_id,
            )
            return False

        if pkg_version is None:  # не нашелся пакет запрашиваемой версии
            available_versions = cls.get_pypi_available_versions(pkg_name=pkg_base_name, python_version=python_version)
            if not available_versions:
                message = f'Пакет `{pkg_base_name}`, для python==`{python_version}`: не существует.'
            else:
                message = (
                    f'Пакет `{pkg_base_name} с версией {pkg_version}`, для python==`{python_version}`: не найден, '
                    f'доступны версии {available_versions}.')

            message_bus_add(
                level='error',
                subcomponent='archive_manager',
                message=message,
                event='package not exists',
                request_id=request_id,
            )
            return False

        current_packages_dir = config.PACKAGES_DIR / python_version / f'{pkg_base_name}=={pkg_version}'

        if current_packages_dir.exists():  # пакет уже установлен
            message_bus_add(
                level='warning',
                subcomponent='archive_manager',
                message=f'Пакет `{pkg_base_name}=={pkg_version}`, python==`{python_version}`: уже есть в архиве.',
                event='package already exists',
                request_id=request_id,
            )
            return False

            # закачка пакета
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            cmd = [python_exe_path, '-m', 'pip', 'download', f'{pkg_base_name}=={pkg_version}', '-d', str(temp_dir)]

            subprocess_wrapper.run(cmd, capture_output=True, check=False, text=True)
            pkg_base_name = Requirement(pkg_name).name

            # поиск whl файлов каталога, определение названия и версии
            downloaded_pkg_name = None
            downloaded_pkg_version = None
            for file in temp_path.iterdir():
                whl_file_name = file.name.split('-')[0].replace('_', '-')
                if whl_file_name.lower() == pkg_base_name.lower():
                    wheel_info = WheelFilename.parse(file.name)
                    downloaded_pkg_name = wheel_info.project
                    downloaded_pkg_version = wheel_info.version
                    break

            # перемещение файлов из временной папки в архив
            if downloaded_pkg_name is not None and downloaded_pkg_version is not None:
                current_packages_dir.mkdir(exist_ok=True, parents=True)
                for file in temp_path.glob('*'):
                    try:
                        shutil.move(str(file), current_packages_dir)
                    except shutil.Error:
                        pass  # иногда будут дублироваться зависимости от разных пакетов, поэтому лучше пропустить

                message_bus_add(
                    level='stop',
                    subcomponent='archive_manager',
                    message=f'Пакет `{pkg_name}`, python==`{python_version}`: загружен в архив.',
                    event='package download',
                    request_id=request_id,
                    data={'metric': f'{perf_counter() - start_time:.2f} сек.'}
                )
                return True
            else:
                msg_err = f'Пакет `{pkg_name}`, python==`{python_version}`: Не найден главный wheel для {pkg_name}.'
                message_bus_add(
                    level='error',
                    subcomponent='archive_manager',
                    message=f'Не найден wheel для пакета `{pkg_name}`, python==`{python_version}`',
                    event='package wheel not found',
                    error=msg_err,
                    request_id=request_id,
                )
                raise RuntimeError(msg_err)


if __name__ == '__main__':
    # archive = PackagesArchive()
    # PackagesArchive.download(packages_list=['requests==999.999.999'])
    PackagesArchive.download(packages_list=['uvicorn'])
    # PackagesArchive.download(packages_list=['aec-audio-processing'])
    # print(archive.is_package_archive_exists(pkg_name='fastapi==0.124.4', python_version='3.8'))  # есть ли такой пакет?
    # print(PackagesArchive().get_archive_packages_by_version(python_versions=['3.10']))  # получить список версий из архива
