# app/hardware/drivers/acs_acr1252u.py — Драйвер для ACS ACR1252U-M1 NFC Reader
import asyncio
from datetime import datetime
from app.hardware.base import BaseDeviceDriver, DeviceType, ConnectionProtocol, DeviceStatus, AccessResult, HWEventType, HardwareEvent
from app.hardware.registry import register_driver


@register_driver
class AcsAcr1252uDriver(BaseDeviceDriver):
    """
    Драйвер для ACS ACR1252U-M1 USB NFC Reader/Writer.
    
    Поддерживает:
    - Чтение UID MIFARE Classic/Ultralight
    - Запись данных в сектора MIFARE Classic
    - PC/SC интерфейс через pyscard
    """

    VENDOR = "ACS"
    MODELS = ["ACR1252U", "ACR1252U-M1"]
    DEVICE_TYPES = [DeviceType.READER]
    PROTOCOLS = [ConnectionProtocol.SDK]

    def __init__(self, config: dict):
        super().__init__(config)
        self.reader_name = config.get("reader_name", "ACS ACR1252U")
        self._connected = False
        self._card_present = False
        self._last_uid = None

    async def connect(self) -> bool:
        """Подключение к PC/SC reader"""
        try:
            from smartcard.System import readers
            from smartcard.scard import SCARD_SCOPE_USER
            
            available_readers = readers()
            for reader in available_readers:
                if self.reader_name in str(reader):
                    self._connection = reader.createConnection()
                    self._connection.connect()
                    self._connected = True
                    self._status = DeviceStatus.ONLINE
                    self._last_ping = datetime.utcnow()
                    print(f"[ACS {self.device_id}] Connected to {reader}")
                    return True
            
            print(f"[ACS {self.device_id}] Reader not found: {self.reader_name}")
            print(f"[ACS {self.device_id}] Available: {[str(r) for r in available_readers]}")
            self._status = DeviceStatus.OFFLINE
            return False
            
        except Exception as e:
            print(f"[ACS {self.device_id}] Connect failed: {e}")
            self._status = DeviceStatus.OFFLINE
            return False

    async def close(self, **kwargs) -> bool:
        """Закрыть соединение с устройством"""
        return await self.disconnect()

    async def disconnect(self):
        if hasattr(self, '_connection') and self._connection:
            try:
                self._connection.disconnect()
            except:
                pass
        self._connected = False
        self._status = DeviceStatus.OFFLINE

    async def ping(self) -> bool:
        if not self._connected:
            return await self.connect()
        try:
            self._last_ping = datetime.utcnow()
            self._status = DeviceStatus.ONLINE
            return True
        except:
            self._status = DeviceStatus.OFFLINE
            return False

    async def open(self, credential: str = None, **kwargs) -> AccessResult:
        """Для NFC reader — 'open' = прочитать карту"""
        uid = await self.read_card()
        if uid:
            return AccessResult.GRANTED
        return AccessResult.ERROR

    async def read_card(self) -> str | None:
        """Прочитать UID карты (MIFARE Classic/Ultralight)"""
        print(f"[DEBUG] read_card called, connected={self._connected}, last_uid={self._last_uid}")
        
        try:
            from smartcard.util import toHexString
            import asyncio
            
            # APDU: Get Data (UID)
            GET_UID = [0xFF, 0xCA, 0x00, 0x00, 0x00]
            
            # Retry: несколько попыток чтения с connect/disconnect
            for attempt in range(3):
                try:
                    print(f"[DEBUG] Attempt {attempt+1}: connecting...")
                    
                    # Подключаемся заново
                    if hasattr(self, '_connection') and self._connection:
                        try:
                            self._connection.disconnect()
                        except:
                            pass
                    
                    from smartcard.System import readers
                    available_readers = readers()
                    for reader in available_readers:
                        if self.reader_name in str(reader):
                            self._connection = reader.createConnection()
                            self._connection.connect()
                            self._connected = True
                            break
                    
                    if not self._connected:
                        print(f"[DEBUG] Reader not found")
                        return None
                    
                    print(f"[DEBUG] Transmitting GET_UID...")
                    response, sw1, sw2 = self._connection.transmit(GET_UID)
                    print(f"[DEBUG] Response: SW1={hex(sw1)}, SW2={hex(sw2)}")
                    
                    if sw1 == 0x90 and sw2 == 0x00:
                        uid = toHexString(response)
                        self._last_uid = uid
                        print(f"[ACS {self.device_id}] Card read: UID={uid}")
                        await self._emit_event(HardwareEvent(
                            HWEventType.ENTRY, self.device_id,
                            credential=uid,
                            details={"uid": uid, "action": "read"}
                        ))
                        return uid
                    elif sw1 == 0x63 and sw2 == 0x00:
                        # Карта не обнаружена
                        if attempt < 2:
                            print(f"[DEBUG] Card not present, retrying...")
                            await asyncio.sleep(0.2)
                            continue
                        else:
                            self._last_uid = None
                            print(f"[DEBUG] Card not present after retries")
                            return None
                    else:
                        print(f"[ACS {self.device_id}] Read error: SW1={hex(sw1)}, SW2={hex(sw2)}")
                        return None
                        
                except Exception as e:
                    err_msg = str(e)
                    if "извлечена" in err_msg or "0x80100069" in err_msg:
                        if attempt < 2:
                            print(f"[DEBUG] Card not present (error), retrying...")
                            await asyncio.sleep(0.2)
                            continue
                        else:
                            self._last_uid = None
                            print(f"[DEBUG] Card not present after retries (error)")
                            return None
                    else:
                        raise
            
            return None
                
        except Exception as e:
            print(f"[ACS {self.device_id}] Read failed: {e}")
            return None

    async def write_mifare_sector(
        self,
        sector: int,
        key_a: str,
        data: str,
        **kwargs
    ) -> bool:
        """
        Записать данные в сектор MIFARE Classic.
        
        Args:
            sector: Номер сектора (0-15)
            key_a: Ключ A (12 hex символов, например "FFFFFFFFFFFF")
            data: Данные (32 hex символа = 16 байт)
        """
        if not self._connected:
            return False
        
        try:
            from smartcard.util import toBytes
            
            # Проверяем формат ключа
            if len(key_a) != 12:
                print(f"[ACS {self.device_id}] Invalid key length: {len(key_a)}")
                return False
            
            # Проверяем формат данных
            if len(data) != 32:
                print(f"[ACS {self.device_id}] Invalid data length: {len(data)}")
                return False
            
            # Аутентификация сектора
            # Load Keys
            LOAD_KEYS = [0xFF, 0x82, 0x00, 0x00, 0x06] + toBytes(key_a)
            response, sw1, sw2 = self._connection.transmit(LOAD_KEYS)
            if not (sw1 == 0x90 and sw2 == 0x00):
                print(f"[ACS {self.device_id}] Load keys failed: SW1={hex(sw1)}, SW2={hex(sw2)}")
                return False
            
            # Authenticate
            block = sector * 4  # Первый блок сектора
            AUTH = [0xFF, 0x86, 0x00, 0x00, 0x05, 0x01, 0x00, block, 0x60, 0x00]
            response, sw1, sw2 = self._connection.transmit(AUTH)
            if not (sw1 == 0x90 and sw2 == 0x00):
                print(f"[ACS {self.device_id}] Auth failed: SW1={hex(sw1)}, SW2={hex(sw2)}")
                return False
            
            # Write data (16 bytes per block)
            data_bytes = toBytes(data)
            for i in range(0, len(data_bytes), 16):
                block_num = block + (i // 16)
                block_data = data_bytes[i:i+16]
                if len(block_data) < 16:
                    block_data += [0x00] * (16 - len(block_data))
                
                WRITE_BLOCK = [0xFF, 0xD6, 0x00, block_num, 0x10] + block_data
                response, sw1, sw2 = self._connection.transmit(WRITE_BLOCK)
                if not (sw1 == 0x90 and sw2 == 0x00):
                    print(f"[ACS {self.device_id}] Write block {block_num} failed")
                    return False
            
            print(f"[ACS {self.device_id}] MIFARE sector {sector} written successfully")
            return True
            
        except Exception as e:
            print(f"[ACS {self.device_id}] Write failed: {e}")
            return False

    async def get_device_info(self) -> dict:
        return {
            "vendor": self.VENDOR,
            "model": "ACR1252U-M1",
            "reader_name": self.reader_name,
            "connected": self._connected,
            "last_uid": self._last_uid,
            "status": self._status.value,
        }

    async def start_event_listener(self):
        """ACS ACR1252U — polling отключён, используйте read_card() через API"""
        # Не запускаем polling, чтобы не конфликтовать с API вызовами
        while True:
            await asyncio.sleep(60)  # Спим, ничего не делаем

    async def stop_event_listener(self):
        pass
