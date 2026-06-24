# add_debug_to_read.py
with open('app/hardware/drivers/acs_acr1252u.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_read = '''    async def read_card(self) -> str | None:
        """Прочитать UID карты (MIFARE Classic/Ultralight)"""
        # Возвращаем UID из listener (если карта была прочитана)
        if self._last_uid:
            return self._last_uid
        
        # Если listener ещё не прочитал — пробуем сами
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
        print(f"[DEBUG] read_card called, connected={self._connected}, last_uid={self._last_uid}")
        
        # Возвращаем UID из listener (если карта была прочитана)
        if self._last_uid:
            print(f"[DEBUG] Returning cached UID: {self._last_uid}")
            return self._last_uid
        
        # Если listener ещё не прочитал — пробуем сами
        if not self._connected:
            print(f"[DEBUG] Not connected, trying to connect...")
            connected = await self.connect()
            if not connected:
                return None
        
        try:
            from smartcard.util import toHexString
            
            # APDU: Get Data (UID)
            GET_UID = [0xFF, 0xCA, 0x00, 0x00, 0x00]
            
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
                print(f"[DEBUG] Card not present (SW1=0x63, SW2=0x00)")
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
    print("Отладка добавлена!")
else:
    print("ERROR: Не найден read_card")
