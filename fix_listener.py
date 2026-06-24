# fix_listener.py
with open('app/hardware/drivers/acs_acr1252u.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_listener = '''    async def start_event_listener(self):
        """Polling карты в цикле"""
        while True:
            try:
                if self._connected:
                    uid = await self.read_card()
                    if uid and not self._card_present:
                        self._card_present = True
                        await self._emit_event(HardwareEvent(
                            HWEventType.ENTRY, self.device_id,
                            credential=uid,
                            details={"uid": uid, "action": "card_present"}
                        ))
                    elif not uid and self._card_present:
                        self._card_present = False
                        await self._emit_event(HardwareEvent(
                            HWEventType.EXIT, self.device_id,
                            details={"action": "card_removed"}
                        ))
                await asyncio.sleep(0.5)
            except Exception as e:
                print(f"[ACS {self.device_id}] Listener error: {e}")
                await asyncio.sleep(2)'''

new_listener = '''    async def start_event_listener(self):
        """Polling карты в цикле"""
        while True:
            try:
                if self._connected:
                    try:
                        from smartcard.util import toHexString
                        GET_UID = [0xFF, 0xCA, 0x00, 0x00, 0x00]
                        response, sw1, sw2 = self._connection.transmit(GET_UID)
                        
                        if sw1 == 0x90 and sw2 == 0x00:
                            uid = toHexString(response)
                            if uid != self._last_uid:
                                self._last_uid = uid
                                self._card_present = True
                                print(f"[ACS {self.device_id}] Card detected: UID={uid}")
                                await self._emit_event(HardwareEvent(
                                    HWEventType.ENTRY, self.device_id,
                                    credential=uid,
                                    details={"uid": uid, "action": "card_present"}
                                ))
                        elif sw1 == 0x63 and sw2 == 0x00:
                            # Карта не обнаружена — НЕ сбрасываем _last_uid
                            if self._card_present:
                                self._card_present = False
                                print(f"[ACS {self.device_id}] Card removed")
                                await self._emit_event(HardwareEvent(
                                    HWEventType.EXIT, self.device_id,
                                    details={"action": "card_removed"}
                                ))
                    except Exception as e:
                        if "извлечена" not in str(e):
                            print(f"[ACS {self.device_id}] Listener read error: {e}")
                await asyncio.sleep(0.5)
            except Exception as e:
                print(f"[ACS {self.device_id}] Listener error: {e}")
                await asyncio.sleep(2)'''

if old_listener in content:
    content = content.replace(old_listener, new_listener)
    with open('app/hardware/drivers/acs_acr1252u.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Listener исправлен!")
else:
    print("ERROR: Не найден listener")
