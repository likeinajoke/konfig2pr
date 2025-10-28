import argparse
import sys
import os
from pathlib import Path


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
        raise ValueError("URL репозитория или путь к файлу не может быть пустым")

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

    except ValueError as e:
        print(f"Ошибка валидации: {e}", file=sys.stderr)
        sys.exit(1)
    except SystemExit:
        # argparse вызывает sys.exit при неправильных аргументах
        sys.exit(1)
    except Exception as e:
        print(f"Непредвиденная ошибка: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()