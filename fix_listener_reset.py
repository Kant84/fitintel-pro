# fix_listener_reset.py
with open('app/hardware/drivers/acs_acr1252u.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_listener = '''                        elif sw1 == 0x63 and sw2 == 0x00:
                            # Карта не обнаружена — НЕ сбрасываем _last_uid
                            if self._card_present:
                                self._card_present = False
                                print(f"[ACS {self.device_id}] Card removed")
                                await self._emit_event(HardwareEvent(
                                    HWEventType.EXIT, self.device_id,
                                    details={"action": "card_removed"}
                                ))'''

new_listener = '''                        elif sw1 == 0x63 and sw2 == 0x00:
                            # Карта не обнаружена — сбрасываем _last_uid
                            if self._card_present:
                                self._card_present = False
                                self._last_uid = None
                                print(f"[ACS {self.device_id}] Card removed")
                                await self._emit_event(HardwareEvent(
                                    HWEventType.EXIT, self.device_id,
                                    details={"action": "card_removed"}
                                ))'''

if old_listener in content:
    content = content.replace(old_listener, new_listener)
    with open('app/hardware/drivers/acs_acr1252u.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Listener сбрасывает _last_uid!")
else:
    print("ERROR: Не найден listener")
