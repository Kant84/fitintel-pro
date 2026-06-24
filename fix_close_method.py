# fix_close_method.py
with open('app/hardware/drivers/acs_acr1252u.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Добавляем метод close перед disconnect
old_disconnect = '''    async def disconnect(self):
        if hasattr(self, '_connection') and self._connection:
            try:
                self._connection.disconnect()
            except:
                pass
        self._connected = False
        self._status = DeviceStatus.OFFLINE'''

new_disconnect = '''    async def close(self, **kwargs) -> bool:
        """Закрыть соединение с устройством"""
        return await self.disconnect()

    async def disconnect(self):
        if hasattr(self, '_connection') and self._connection:
            try:
                self._connection.disconnect()
            except:
                pass
        self._connected = False
        self._status = DeviceStatus.OFFLINE'''

if old_disconnect in content:
    content = content.replace(old_disconnect, new_disconnect)
    with open('app/hardware/drivers/acs_acr1252u.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Метод close добавлен!")
else:
    print("ERROR: Не найден disconnect")
