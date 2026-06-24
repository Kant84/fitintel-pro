# fix_retry_read.py
with open('app/hardware/drivers/acs_acr1252u.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_read = '''    async def read_card(self) -> str | None:
        """Прочитать UID карты (MIFARE Classic/Ultralight)"""
        print(f"[DEBUG] read_card called, connected={self._connected}, last_uid={self._last_uid}")
        
        # Сначала проверяем, есть ли карта (через transmit)
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
                # Карта не обнаружена — сбрасываем _last_uid
                self._last_uid = None
                print(f"[DEBUG] Card not present (SW1=0x63, SW2=0x00), reset last_uid")
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
        
        # Сначала проверяем, есть ли карта (через transmit)
        if not self._connected:
            print(f"[DEBUG] Not connected, trying to connect...")
            connected = await self.connect()
            if not connected:
                return None
        
        try:
            from smartcard.util import toHexString
            import asyncio
            
            # APDU: Get Data (UID)
            GET_UID = [0xFF, 0xCA, 0x00, 0x00, 0x00]
            
            # Retry: несколько попыток чтения
            for attempt in range(3):
                try:
                    print(f"[DEBUG] Transmitting GET_UID (attempt {attempt+1})...")
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
                        # Карта не обнаружена — пробуем ещё
                        if attempt < 2:
                            print(f"[DEBUG] Card not present, retrying...")
                            await asyncio.sleep(0.2)
                            continue
                        else:
                            # Последняя попытка — сбрасываем _last_uid
                            self._last_uid = None
                            print(f"[DEBUG] Card not present after retries, reset last_uid")
                            return None
                    else:
                        print(f"[ACS {self.device_id}] Read error: SW1={hex(sw1)}, SW2={hex(sw2)}")
                        return None
                        
                except Exception as e:
                    if "извлечена" in str(e) and attempt < 2:
                        print(f"[DEBUG] Card removed during read, retrying...")
                        await asyncio.sleep(0.2)
                        continue
                    else:
                        raise
            
            return None
                
        except Exception as e:
            print(f"[ACS {self.device_id}] Read failed: {e}")
            return None'''

if old_read in content:
    content = content.replace(old_read, new_read)
    with open('app/hardware/drivers/acs_acr1252u.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Retry добавлен!")
else:
    print("ERROR: Не найден read_card")
