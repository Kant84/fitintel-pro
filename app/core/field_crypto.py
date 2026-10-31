# app/core/field_crypto.py - шифрование отдельных полей на хранении (C1)
import logging
import os

log = logging.getLogger(__name__)

_PREFIX = "enc:v1:"
_fernet = None
_checked = False


def _get_fernet():
    global _fernet, _checked
    if _checked:
        return _fernet
    _checked = True
    key = (os.environ.get("FISCAL_CRYPTO_KEY") or "").strip()
    if not key:
        log.warning("FISCAL_CRYPTO_KEY не задан - поля хранятся в открытом виде")
        return None
    try:
        from cryptography.fernet import Fernet
        _fernet = Fernet(key.encode())
    except Exception as e:
        log.error("FISCAL_CRYPTO_KEY недействителен: %s", e)
        _fernet = None
    return _fernet


def encrypt_field(value):
    if value is None or value == "":
        return value
    if isinstance(value, str) and value.startswith(_PREFIX):
        return value
    f = _get_fernet()
    if f is None:
        return value
    return _PREFIX + f.encrypt(str(value).encode()).decode()


def decrypt_field(value):
    if not isinstance(value, str) or not value.startswith(_PREFIX):
        return value
    f = _get_fernet()
    if f is None:
        log.warning("Поле зашифровано, но FISCAL_CRYPTO_KEY не задан")
        return ""
    try:
        return f.decrypt(value[len(_PREFIX):].encode()).decode()
    except Exception as e:
        log.error("Не удалось расшифровать поле: %s", e)
        return ""
