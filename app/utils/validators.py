# app/utils/validators.py

# импорт регулярных выражений
import re


# функция приводит телефон к единому формату
def normalize_phone(phone: str) -> str:
    # убираем пробелы по краям
    value = phone.strip()

    # если строка пустая — ошибка
    if not value:
        raise ValueError("Телефон не может быть пустым")

    # заменяем международный префикс 00 на +
    if value.startswith("00"):
        value = "+" + value[2:]

    # оставляем только цифры и плюс
    value = re.sub(r"[^\d+]", "", value)

    # плюс может быть только один и только в начале
    if value.count("+") > 1 or ("+" in value[1:]):
        raise ValueError("Телефон имеет неверный формат")

    # если телефон начинается с 8 и содержит 11 цифр,
    # считаем это российским номером и переводим в +7
    if value.startswith("8") and value.isdigit() and len(value) == 11:
        value = "+7" + value[1:]

    # если телефон без плюса — добавляем плюс
    if not value.startswith("+"):
        value = "+" + value

    # извлекаем только цифры без плюса
    digits = value[1:]

    # проверяем, что внутри только цифры
    if not digits.isdigit():
        raise ValueError("Телефон должен содержать только цифры")

    # проверяем длину номера
    if len(digits) < 10 or len(digits) > 15:
        raise ValueError("Телефон должен содержать от 10 до 15 цифр")

    # возвращаем нормализованный номер
    return value


# функция просто валидирует и возвращает нормализованный телефон
def validate_phone(phone: str) -> str:
    # используем основную функцию нормализации
    return normalize_phone(phone)


# функция очищает email
def normalize_email(email: str) -> str:
    # убираем пробелы по краям и переводим в нижний регистр
    value = email.strip().lower()

    # если email пустой — ошибка
    if not value:
        raise ValueError("Email не может быть пустым")

    # возвращаем нормализованный email
    return value


# функция очищает текстовое поле
def normalize_text(value: str) -> str:
    # убираем лишние пробелы по краям
    cleaned = value.strip()

    # если после очистки строка пустая — ошибка
    if not cleaned:
        raise ValueError("Поле не может быть пустым")

    # заменяем повторяющиеся пробелы внутри строки на один
    cleaned = re.sub(r"\s+", " ", cleaned)

    # возвращаем очищенную строку
    return cleaned