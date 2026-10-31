# fitintel-desktop/secure_store.py - C2: токены в Windows Credential Manager.
# В client_settings.json токенов нет. Fallback на json - только для миграции.
import ctypes
import ctypes.wintypes as wt
import json
import logging

log = logging.getLogger(__name__)
_TARGET = "FitIntelDesktop/tokens"
_CRED_TYPE_GENERIC = 1
_CRED_PERSIST_LOCAL_MACHINE = 2


class _CREDENTIALW(ctypes.Structure):
    _fields_ = [
        ("Flags", wt.DWORD), ("Type", wt.DWORD),
        ("TargetName", wt.LPWSTR), ("Comment", wt.LPWSTR),
        ("LastWritten", wt.FILETIME),
        ("CredentialBlobSize", wt.DWORD),
        ("CredentialBlob", ctypes.POINTER(ctypes.c_char)),
        ("Persist", wt.DWORD), ("AttributeCount", wt.DWORD),
        ("Attributes", ctypes.c_void_p),
        ("TargetAlias", wt.LPWSTR), ("UserName", wt.LPWSTR),
    ]


_advapi = ctypes.windll.advapi32
_kernel32 = ctypes.windll.kernel32
_advapi.CredReadW.restype = ctypes.c_bool
_advapi.CredReadW.argtypes = [wt.LPCWSTR, wt.DWORD, wt.DWORD,
                              ctypes.POINTER(ctypes.POINTER(_CREDENTIALW))]
_advapi.CredWriteW.argtypes = [ctypes.POINTER(_CREDENTIALW), wt.DWORD]
_advapi.CredDeleteW.argtypes = [wt.LPCWSTR, wt.DWORD, wt.DWORD]


def _write(blob: bytes) -> bool:
    buf = ctypes.create_string_buffer(blob, len(blob))
    cred = _CREDENTIALW()
    cred.Flags = 0
    cred.Type = _CRED_TYPE_GENERIC
    cred.TargetName = _TARGET
    cred.Comment = "FitIntel Pro session tokens (C2)"
    cred.CredentialBlobSize = len(blob)
    cred.CredentialBlob = ctypes.cast(buf, ctypes.POINTER(ctypes.c_char))
    cred.Persist = _CRED_PERSIST_LOCAL_MACHINE
    cred.AttributeCount = 0
    cred.Attributes = None
    cred.TargetAlias = None
    cred.UserName = None
    return bool(_advapi.CredWriteW(ctypes.byref(cred), 0))


def _read() -> bytes | None:
    p = ctypes.POINTER(_CREDENTIALW)()
    if not _advapi.CredReadW(_TARGET, _CRED_TYPE_GENERIC, 0, ctypes.byref(p)):
        return None
    try:
        c = p.contents
        return ctypes.string_at(c.CredentialBlob, c.CredentialBlobSize)
    finally:
        _kernel32.LocalFree(p)


def load_tokens() -> dict:
    try:
        raw = _read()
        if raw:
            return json.loads(raw.decode("utf-8"))
    except Exception as e:
        log.warning("secure_store read: %s", e)
    return {}


def save_tokens(access: str | None = None, refresh: str | None = None) -> None:
    tokens = load_tokens()
    if access:
        tokens["access"] = access
    if refresh:
        tokens["refresh"] = refresh
    try:
        if not _write(json.dumps(tokens).encode("utf-8")):
            log.error("CredWrite failed")
    except Exception as e:
        log.error("secure_store write: %s", e)


def get_token() -> str:
    return load_tokens().get("access") or ""


def get_refresh_token() -> str:
    return load_tokens().get("refresh") or ""


def clear_tokens() -> None:
    try:
        _advapi.CredDeleteW(_TARGET, _CRED_TYPE_GENERIC, 0)
    except Exception:
        pass


def strip_tokens_from_json(cfg: dict) -> dict:
    for k in ("token", "access_token", "refresh_token"):
        cfg.pop(k, None)
    return cfg
