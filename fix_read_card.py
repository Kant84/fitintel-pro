# fix_read_card.py
with open('app/hardware/drivers/acs_acr1252u.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_read = '''    async def read_card(self) -> str | None:
        """Прочитать UID карты (MIFARE Classic/Ultralight)"""
        if not self._connected:
            return None
        
        try:
            from smartcard.util import toHexString
            
            # APDU: Get Data (UID)
            GET_UID = [0xFF, 0xCA, 0x00, 0x00, 0x00]
            
            response, sw1, sw2 = self._connection.transmit(GET_UID)
            
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
                return None
            else:
                print(f"[ACS {self.device_id}] Read error: SW1={hex(sw1)}, SW2={hex(sw2)}")
                return None
                
        except Exception as e:
            print(f"[ACS {self.device_id}] Read failed: {e}")
            return None'''

new_read = '''    async def read_card(self) -> str | None:
        """Прочитать UID карты (MIFARE Classic/Ultralight)"""
        # Если listener уже прочитал карту — возвращаем cached UID
        if self._last_uid:
            uid = self._last_uid
            # Сбрасываем после чтения
            # self._last_uid = None
            return uid
        
        if not self._connected:
            return None
        
        try:
            from smartcard.util import toHexString
            
            # APDU: Get Data (UID)
            GET_UID = [0xFF, 0xCA, 0x00, 0x00, 0x00]
            
            response, sw1, sw2 = self._connection.transmit(GET_UID)
            
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
                return None
            else:
                print(f"[ACS {self.device_id}] Read error: SW1={hex(sw1)}, SW2={hex(sw2)}")
                return None
                
        except Exception as e:
            print(f"[ACS {self.device_id}] Read failed: {e}")
            return None'''

if old_read in content:
    content = content.replace(old_read, new_read)
    with open('app/hardware/drivers/acs_acr1252u.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("read_card исправлен!")
else:
    print("ERROR: Не найден read_card")
