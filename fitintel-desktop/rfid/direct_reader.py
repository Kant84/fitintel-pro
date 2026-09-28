# -*- coding: utf-8 -*-
"""Прямой доступ desktop к USB-считывателю через pyscard (PC/SC).
Никаких локальных сервисов: вставил считыватель — работает."""
from smartcard.System import readers
from smartcard.util import toHexString

KEY_B_ITC = "666666666666"


def _hx(s):
    s = (s or "").replace(" ", "").upper()
    return [int(s[i:i + 2], 16) for i in range(0, len(s), 2)]


class DirectReader:
    def __init__(self):
        self._reader = None
        self._pick()

    def _pick(self):
        try:
            rs = readers()
        except Exception:
            rs = []
        for r in rs:                       # ACR1252: берём PICC-слот, не SAM
            if "PICC" in str(r):
                self._reader = r
                return
        self._reader = rs[0] if rs else None

    def status(self):
        ok = self._reader is not None
        return {"connected": ok,
                "reader_name": str(self._reader) if ok else "Считыватель не найден"}

    def _connect(self):
        if not self._reader:
            self._pick()
        if not self._reader:
            return None
        conn = self._reader.createConnection()
        conn.connect()
        return conn

    def detect_uid(self):
        """hex-строка UID или None (карты нет / считывателя нет)."""
        conn = None
        try:
            conn = self._connect()
            if not conn:
                return None
            data, sw1, _ = conn.transmit([0xFF, 0xCA, 0x00, 0x00, 0x00])
            if sw1 == 0x90 and data:
                return toHexString(data).replace(" ", "").upper()
            return None
        except Exception:
            return None
        finally:
            try:
                if conn:
                    conn.disconnect()
            except Exception:
                pass

    def _load_key(self, conn, key_no, key_bytes):
        conn.transmit([0xFF, 0x82, 0x00, key_no, 0x06] + key_bytes)

    def _auth(self, conn, block, key_type, key_no):
        kt = 0x61 if str(key_type).upper() == "B" else 0x60
        conn.transmit([0xFF, 0x86, 0x00, 0x00, 0x05,
                       0x01, 0x00, block, kt, key_no])

    def read_sector(self, sector=0, key_type="B", key_hex=KEY_B_ITC):
        """Вернёт {'block_0':..., 'block_1':...} (hex, без пробелов)."""
        conn = None
        try:
            conn = self._connect()
            if not conn:
                return {}
            self._load_key(conn, 0, _hx(key_hex))
            out = {}
            first = int(sector) * 4
            for b in range(4):
                blk = first + b
                self._auth(conn, blk, key_type, 0)
                data, sw1, _ = conn.transmit([0xFF, 0xB0, 0x00, blk, 0x10])
                if sw1 == 0x90:
                    out[f"block_{b}"] = toHexString(data).replace(" ", "").upper()
            return out
        except Exception:
            return {}
        finally:
            try:
                if conn:
                    conn.disconnect()
            except Exception:
                pass

    def write_block(self, sector=0, block=1, key_type="B",
                    key_hex=KEY_B_ITC, data_hex=""):
        """Запись одного блока (16 байт hex = 32 символа). True/False."""
        conn = None
        try:
            conn = self._connect()
            if not conn:
                return False
            absolute = int(sector) * 4 + int(block)
            self._load_key(conn, 0, _hx(key_hex))
            self._auth(conn, absolute, key_type, 0)
            payload = _hx(data_hex)
            if len(payload) != 16:
                return False
            _, sw1, _ = conn.transmit([0xFF, 0xD6, 0x00, absolute, 0x10] + payload)
            return sw1 == 0x90
        except Exception:
            return False
        finally:
            try:
                if conn:
                    conn.disconnect()
            except Exception:
                pass