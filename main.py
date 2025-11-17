import argparse
import sys
import os
import tempfile
import subprocess
from pathlib import Path
import re
import requests
import tarfile
from urllib.parse import urljoin, urlparse


def validate_package_name(name):
    """Проверяет корректность имени пакета"""
    if not name or not isinstance(name, str):
        raise ValueError("Имя пакета должно быть непустой строкой")
    if len(name.strip()) == 0:
        raise ValueError("Имя пакета не может быть пустым или содержать только пробелы")
    return name.strip()


def validate_repository(repo):
    """Проверяет корректность URL репозитория или пути к файлу"""
    if not repo or not isinstance(repo, str):
        raise ValueError("URL репозитория или путь к файлу должен быть непустой строкой")
    repo = repo.strip()
    if len(repo) == 0:
        raise ValueError("URL репозитория или путь к файлу должен быть непустой строкой")

    # Проверяем, является ли это URL
    if repo.startswith(('http://', 'https://')):
        # Проверяем базовый формат URL
        if '://' not in repo or '.' not in repo.split('://')[1].split('/')[0]:
            raise ValueError("Некорректный формат URL репозитория")
    else:
        # Считаем, что это путь к файлу/директории
        # Не проверяем существование файла, так как это может быть тестовый репозиторий
        pass

    return repo


def validate_mode(mode):
    """Проверяет корректность режима работы"""
    if mode is None:
        return 'production'  # значение по умолчанию

    if not isinstance(mode, str):
        raise ValueError("Режим работы должен быть строкой")

    valid_modes = ['production', 'development', 'test']
    mode = mode.lower().strip()

    if mode not in valid_modes:
        raise ValueError(f"Недопустимый режим работы: {mode}. Допустимые значения: {', '.join(valid_modes)}")

    return mode


def validate_depth(depth):
    """Проверяет корректность глубины анализа"""
    if depth is None:
        return 3  # значение по умолчанию

    try:
        depth = int(depth)
    except (TypeError, ValueError):
        raise ValueError("Максимальная глубина анализа должна быть целым числом")

    if depth < 1:
        raise ValueError("Максимальная глубина анализа должна быть положительным числом")

    if depth > 10:
        raise ValueError("Максимальная глубина анализа не должна превышать 10")

    return depth


def extract_dependencies_from_cargo_toml(cargo_toml_path):
    """Извлекает прямые зависимости из Cargo.toml"""
    dependencies = []

    with open(cargo_toml_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Регулярное выражение для поиска секций зависимостей
    sections = re.findall(r'\[([^\]]+)\](.*?)(?=\n\[|$)', content, re.DOTALL)

    for section_name, section_content in sections:
        section_name = section_name.strip()
        if section_name == 'dependencies' or section_name.startswith('dependencies.'):
            # Ищем зависимости в формате:
            # name = "version"
            # name = { version = "x.y.z", optional = true, ... }
            dep_matches = re.findall(r'^\s*([a-zA-Z0-9_-]+)\s*=\s*(.*)$', section_content, re.MULTILINE)

            for dep_name, dep_value in dep_matches:
                dep_name = dep_name.strip()

                # Убираем комментарии из значения
                dep_value = dep_value.split('#')[0].strip()

                # Простая строка (например, "1.0.0")
                if dep_value.startswith('"') and dep_value.endswith('"'):
                    version = dep_value[1:-1]
                    dependencies.append({'name': dep_name, 'version': version})
                # Таблица (например, { version = "1.0.0", ... })
                elif dep_value.startswith('{') and dep_value.endswith('}'):
                    # Ищем version внутри таблицы
                    version_match = re.search(r'version\s*=\s*"([^"]+)"', dep_value)
                    if version_match:
                        version = version_match.group(1)
                        dependencies.append({'name': dep_name, 'version': version})
                    else:
                        # Если version не указан, добавляем без версии
                        dependencies.append({'name': dep_name, 'version': 'unknown'})
                # Просто имя (редко, но может быть)
                else:
                    dependencies.append({'name': dep_name, 'version': 'unknown'})

    return dependencies


def download_crate_source(crate_name, repo, version=None):
    """Скачивает исходный код пакета с crates.io"""
    # Если версия не указана, получаем последнюю
    if not version:
        # Получаем информацию о пакете
        metadata_url = f"{repo}{crate_name}"
        response = requests.get(metadata_url)
        if response.status_code != 200:
            raise RuntimeError(f"Не удалось получить информацию о пакете {crate_name}: {response.status_code} или был неверно указан адрес репозитория")

        data = response.json()
        version = data['crate']['max_version']

    # Формируем URL для скачивания
    download_url = f"{repo}{crate_name}/{version}/download"

    # Скачиваем архив
    response = requests.get(download_url)
    if response.status_code != 200:
        raise RuntimeError(f"Не удалось скачать пакет {crate_name} версии {version}: {response.status_code}")

    return response.content


def extract_cargo_toml_from_archive(archive_content, temp_dir):
    """Извлекает Cargo.toml из архива и возвращает путь к нему"""
    # Создаём временный файл для архива
    with tempfile.NamedTemporaryFile(delete=False, suffix='.crate') as archive_file:
        archive_file.write(archive_content)
        archive_path = archive_file.name

    try:
        # Распаковываем .crate архив (это .tar.gz)
        with tarfile.open(archive_path, 'r:gz') as tar:
            if sys.version_info >= (3, 12):
                # В Python 3.12+ filter по умолчанию 'data', но мы явно указываем для безопасности
                tar.extractall(path=temp_dir, filter='data')
            else:
                # В более старых версиях filter не поддерживается, просто извлекаем
                tar.extractall(path=temp_dir)

                # Ищем директорию пакета (обычно это crate-name-version)
            extracted_dirs = os.listdir(temp_dir)
            if not extracted_dirs:
                raise FileNotFoundError(f"Архив пустой")

        # Ищем Cargo.toml в распакованной директории
        crate_dir = os.path.join(temp_dir, os.listdir(temp_dir)[0])  # первая поддиректория
        cargo_toml_path = os.path.join(crate_dir, 'Cargo.toml')

        if not os.path.exists(cargo_toml_path):
            raise FileNotFoundError(f"Файл Cargo.toml не найден в архиве пакета")

        return cargo_toml_path

    finally:
        # Удаляем временный файл архива
        os.unlink(archive_path)


def get_direct_dependencies_from_crates_io(crate_name, repository_url):
    """Получает имена и параметры зависимостей через API crates.io"""

    # Узнаём последнюю версию пакета
    metadata_url = f"{repository_url}{crate_name}"
    response = requests.get(metadata_url)
    if response.status_code != 200:
        raise RuntimeError("Не удалось получить данные пакета")

    data = response.json()
    version = data["crate"]["max_version"]

    # Получаем список зависимостей
    deps_url = f"{repository_url}{crate_name}/{version}/dependencies"
    deps_resp = requests.get(deps_url)

    if deps_resp.status_code != 200:
        raise RuntimeError("Не удалось получить список зависимостей")

    deps_data = deps_resp.json()

    dependencies = []
    for d in deps_data["dependencies"]:
        dependencies.append({
            "name": d["crate_id"],
            "version": d["req"],
            "optional": d["optional"],
            "default_features": d.get("default_features", None),
            "features": d.get("features", []),
            "kind": d.get("kind", None)
        })

    return dependencies



def parse_arguments():
    parser = argparse.ArgumentParser(
        description='Инструмент визуализации графа зависимостей для менеджера пакетов'
    )

    parser.add_argument(
        '--package',
        type=str,
        required=True,
        help='Имя анализируемого пакета'
    )

    parser.add_argument(
        '--repository',
        type=str,
        required=True,
        help='URL-адрес репозитория или путь к файлу тестового репозитория'
    )

    parser.add_argument(
        '--mode',
        type=str,
        default='production',
        help='Режим работы с тестовым репозиторием (production, development, test). По умолчанию: production'
    )

    parser.add_argument(
        '--depth',
        type=int,
        default=3,
        help='Максимальная глубина анализа зависимостей (1-10). По умолчанию: 3'
    )

    return parser.parse_args()


def main():
    try:
        args = parse_arguments()

        # Валидация параметров
        package_name = validate_package_name(args.package)
        repository = validate_repository(args.repository)
        mode = validate_mode(args.mode)
        depth = validate_depth(args.depth)

        # Вывод параметров в формате ключ-значение
        print("Параметры конфигурации:")
        print(f"package = {package_name}")
        print(f"repository = {repository}")
        print(f"mode = {mode}")
        print(f"depth = {depth}")

        # Получаем прямые зависимости с crates.io
        dependencies = get_direct_dependencies_from_crates_io(package_name, repository)

        # Выводим прямые зависимости
        print(f"Прямые зависимости: '{package_name}'")

        if dependencies:
            for dep in dependencies:
                print(f"- {dep['name']}:")
        else:
            print("Зависимости не найдены.")

    except ValueError as e:
        print(f"Ошибка валидации: {e}", file=sys.stderr)
        sys.exit(1)
    except FileNotFoundError as e:
        print(f"Ошибка: {e}", file=sys.stderr)
        sys.exit(1)
    except RuntimeError as e:
        print(f"Ошибка выполнения: {e}", file=sys.stderr)
        sys.exit(1)
    except requests.RequestException as e:
        print(f"Ошибка сети: {e}", file=sys.stderr)
        sys.exit(1)
    except SystemExit:
        # argparse вызывает sys.exit при неправильных аргументах
        sys.exit(1)
    except Exception as e:
        print(f"Непредвиденная ошибка: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()