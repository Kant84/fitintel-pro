"""RFID/NFC reader driver — PC/SC (pyscard) + Mifare Classic read/write."""
from smartcard.System import readers
from smartcard.util import toHexString, toBytes
from smartcard.Exceptions import CardConnectionException, NoCardException
import struct

# APDU команды для Mifare Classic
CMD_GET_UID = [0xFF, 0xCA, 0x00, 0x00, 0x00]
CMD_LOAD_KEY = [0xFF, 0x82, 0x00, 0x00, 0x06]
CMD_AUTH_BLOCK = [0xFF, 0x86, 0x00, 0x00, 0x05]
CMD_READ_BLOCK = [0xFF, 0xB0, 0x00]
CMD_UPDATE_BLOCK = [0xFF, 0xD6, 0x00]

# Стандартные ключи Mifare
KEY_DEFAULT = [0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF]
KEYA = [0xA0, 0xA1, 0xA2, 0xA3, 0xA4, 0xA5]


class RFIDReader:
    def __init__(self):
        self.reader = None
        self.connection = None
        self._detect_reader()

    def _detect_reader(self):
        rds = readers()
        if not rds:
            raise RuntimeError("Считыватель не найден. Подключите USB-устройство (ACR122U, OMNIKEY, PN532)")
        self.reader = rds[0]
        print(f"[RFID] Найден считыватель: {self.reader}")

    def connect_card(self):
        if not self.reader:
            self._detect_reader()
        self.connection = self.reader.createConnection()
        try:
            self.connection.connect()
            return True
        except NoCardException:
            return False

    def disconnect(self):
        if self.connection:
            self.connection.disconnect()
            self.connection = None

    def get_uid(self) -> str:
        if not self.connection:
            raise RuntimeError("Нет подключения к карте")
        data, sw1, sw2 = self.connection.transmit(CMD_GET_UID)
        if sw1 == 0x90 and sw2 == 0x00:
            return toHexString(data).replace(" ", "")
        raise RuntimeError(f"Ошибка чтения UID: {sw1:02X} {sw2:02X}")

    def authenticate(self, sector: int, key_type: str = "A", key: list = None):
        if not self.connection:
            raise RuntimeError("Нет подключения к карте")
        block = sector * 4
        key = key or KEY_DEFAULT
        load_cmd = CMD_LOAD_KEY + key
        data, sw1, sw2 = self.connection.transmit(load_cmd)
        if not (sw1 == 0x90 and sw2 == 0x00):
            raise RuntimeError(f"Ошибка загрузки ключа: {sw1:02X} {sw2:02X}")
        auth_cmd = CMD_AUTH_BLOCK + [
            0x01,
            0x00,
            block,
            0x60 if key_type == "A" else 0x61,
            0x00
        ]
        data, sw1, sw2 = self.connection.transmit(auth_cmd)
        if sw1 == 0x90 and sw2 == 0x00:
            return True
        raise RuntimeError(f"Ошибка аутентификации сектора {sector}: {sw1:02X} {sw2:02X}")

    def read_block(self, block: int) -> bytes:
        if not self.connection:
            raise RuntimeError("Нет подключения к карте")
        cmd = CMD_READ_BLOCK + [block, 0x10]
        data, sw1, sw2 = self.connection.transmit(cmd)
        if sw1 in (0x90, 0x63) and sw2 in (0x00, 0x00):
            return bytes(data)
        raise RuntimeError(f"Ошибка чтения блока {block}: {sw1:02X} {sw2:02X}")

    def write_block(self, block: int, data: bytes):
        if not self.connection:
            raise RuntimeError("Нет подключения к карте")
        if len(data) != 16:
            raise ValueError("Данные должны быть ровно 16 байт")
        cmd = CMD_UPDATE_BLOCK + [block, 0x10] + list(data)
        resp, sw1, sw2 = self.connection.transmit(cmd)
        if sw1 in (0x90, 0x63):
            return True
        raise RuntimeError(f"Ошибка записи блока {block}: {sw1:02X} {sw2:02X}")

    def read_sector(self, sector: int, key_type: str = "A", key: list = None) -> dict:
        self.authenticate(sector, key_type, key)
        result = {}
        for i in range(4):
            block = sector * 4 + i
            try:
                data = self.read_block(block)
                result[f"block_{block}"] = toHexString(list(data)).replace(" ", "")
            except Exception as e:
                result[f"block_{block}"] = f"ERROR: {e}"
        return result

    def write_sector_trailer(self, sector: int, key_a: list = None, key_b: list = None, access_bits: list = None):
        block = sector * 4 + 3
        key_a = key_a or KEY_DEFAULT
        key_b = key_b or KEY_DEFAULT
        access_bits = access_bits or [0xFF, 0x07, 0x80]
        trailer = key_a + access_bits + key_b
        if len(trailer) != 16:
            raise ValueError("Trailer must be 16 bytes")
        return self.write_block(block, bytes(trailer))

    def is_connected(self) -> bool:
        try:
            rds = readers()
            return len(rds) > 0
        except Exception:
            return False

    def wait_for_card(self, timeout_sec: int = 30) -> bool:
        import time
        start = time.time()
        while time.time() - start < timeout_sec:
            if self.connect_card():
                return True
            time.sleep(0.5)
        return False


_reader_instance = None

def get_reader() -> RFIDReader:
    global _reader_instance
    if _reader_instance is None:
        _reader_instance = RFIDReader()
    return _reader_instance


def release_reader():
    global _reader_instance
    if _reader_instance:
        _reader_instance.disconnect()
        _reader_instance = None