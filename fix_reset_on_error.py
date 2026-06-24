# fix_reset_on_error.py
with open('app/hardware/drivers/acs_acr1252u.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_read = '''            elif sw1 == 0x63 and sw2 == 0x00:
                # Карта не обнаружена
                print(f"[DEBUG] Card not present (SW1=0x63, SW2=0x00)")
                return None'''

new_read = '''            elif sw1 == 0x63 and sw2 == 0x00:
                # Карта не обнаружена — сбрасываем _last_uid
                self._last_uid = None
                print(f"[DEBUG] Card not present (SW1=0x63, SW2=0x00), reset last_uid")
                return None'''

if old_read in content:
    content = content.replace(old_read, new_read)
    with open('app/hardware/drivers/acs_acr1252u.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Сброс _last_uid добавлен!")
else:
    print("ERROR: Не найден блок")
