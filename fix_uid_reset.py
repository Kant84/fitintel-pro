# fix_uid_reset.py
with open('app/hardware/drivers/acs_acr1252u.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_read = '''    async def read_card(self) -> str | None:
        """Прочитать UID карты (MIFARE Classic/Ultralight)"""
        # Если listener уже прочитал карту — возвращаем cached UID
        if self._last_uid:
            uid = self._last_uid
            # Сбрасываем после чтения
            # self._last_uid = None
            return uid'''

new_read = '''    async def read_card(self) -> str | None:
        """Прочитать UID карты (MIFARE Classic/Ultralight)"""
        # Если listener уже прочитал карту — возвращаем cached UID
        if self._last_uid:
            uid = self._last_uid
            # Сбрасываем после чтения через API
            self._last_uid = None
            return uid'''

if old_read in content:
    content = content.replace(old_read, new_read)
    with open('app/hardware/drivers/acs_acr1252u.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("UID сбрасывается после чтения!")
else:
    print("ERROR: Не найден read_card")
