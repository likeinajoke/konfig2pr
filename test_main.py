import pytest
from main import validate_package_name, validate_repository, validate_mode, validate_depth


# Тесты для validate_package_name
def test_validate_package_name_valid():
    assert validate_package_name("my-package") == "my-package"
    assert validate_package_name("  my-package  ") == "my-package"  # проверка strip()


def test_validate_package_name_empty():
    with pytest.raises(ValueError, match="Имя пакета должно быть непустой строкой"):
        validate_package_name("")


def test_validate_package_name_none():
    with pytest.raises(ValueError, match="Имя пакета должно быть непустой строкой"):
        validate_package_name(None)


def test_validate_package_name_spaces_only():
    with pytest.raises(ValueError, match="Имя пакета не может быть пустым или содержать только пробелы"):
        validate_package_name("   ")


def test_validate_package_name_not_string():
    with pytest.raises(ValueError, match="Имя пакета должно быть непустой строкой"):
        validate_package_name(123)


# Тесты для validate_repository
def test_validate_repository_valid_url():
    assert validate_repository("https://github.com/user/repo.git") == "https://github.com/user/repo.git"
    assert validate_repository("http://example.com") == "http://example.com"


def test_validate_repository_valid_path():
    assert validate_repository("/path/to/repo") == "/path/to/repo"
    assert validate_repository("C:\\path\\to\\repo") == "C:\\path\\to\\repo"


def test_validate_repository_none():
    with pytest.raises(ValueError, match="URL репозитория или путь к файлу должен быть непустой строкой"):
        validate_repository(None)


def test_validate_repository_invalid_url():
    with pytest.raises(ValueError, match="Некорректный формат URL репозитория"):
        validate_repository("http://invalid-url")


# Тесты для validate_mode
def test_validate_mode_default():
    assert validate_mode(None) == "production"


def test_validate_mode_production():
    assert validate_mode("production") == "production"
    assert validate_mode("PRODUCTION") == "production"
    assert validate_mode("  production  ") == "production"


def test_validate_mode_development():
    assert validate_mode("development") == "development"


def test_validate_mode_test():
    assert validate_mode("test") == "test"


def test_validate_mode_invalid():
    with pytest.raises(ValueError, match="Недопустимый режим работы: invalid-mode"):
        validate_mode("invalid-mode")


def test_validate_mode_not_string():
    with pytest.raises(ValueError, match="Режим работы должен быть строкой"):
        validate_mode(123)


# Тесты для validate_depth
def test_validate_depth_default():
    assert validate_depth(None) == 3


def test_validate_depth_valid():
    assert validate_depth(5) == 5
    assert validate_depth("5") == 5  # если строка, но число


def test_validate_depth_too_low():
    with pytest.raises(ValueError, match="Максимальная глубина анализа должна быть положительным числом"):
        validate_depth(0)


def test_validate_depth_too_high():
    with pytest.raises(ValueError, match="Максимальная глубина анализа не должна превышать 10"):
        validate_depth(15)


def test_validate_depth_invalid_type():
    with pytest.raises(ValueError, match="Максимальная глубина анализа должна быть целым числом"):
        validate_depth("abc")


def test_validate_depth_negative():
    with pytest.raises(ValueError, match="Максимальная глубина анализа должна быть положительным числом"):
        validate_depth(-1)