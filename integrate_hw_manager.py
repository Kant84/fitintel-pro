# integrate_hw_manager.py
with open('app/services/access_service.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_start = '''    def _send_open_command(self, device: Device, sector: int = 0) -> bool:
        """
        Отправить команду открытия на устройство.
        
        Поддерживает:
        - HTTP API: отправляет POST/GET запрос на device.address
        - MQTT: публикует сообщение (заглушка)
        - KERONG: офлайн протокол (заглушка)
        """
        try:
            if device.protocol == "http":'''

new_start = '''    def _send_open_command(self, device: Device, sector: int = 0) -> bool:
        """
        Отправить команду открытия на устройство.
        
        Поддерживает:
        - Hardware Manager (реальные драйверы: HTTP, MQTT, KERONG, Modbus, Era, X1)
        - Fallback HTTP прямой запрос
        """
        try:
            # 1. Пробуем через Hardware Manager (реальные драйверы)
            from app.hardware.manager import DeviceManager
            from app.hardware.base import AccessResult
            
            hw_device = DeviceManager.get_device(device.code)
            if hw_device:
                import asyncio
                try:
                    loop = asyncio.get_running_loop()
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                
                result = loop.run_until_complete(DeviceManager.open_device(device.code, sector=sector))
                if result == AccessResult.GRANTED:
                    print(f"[DEVICE] Hardware Manager open SUCCESS for {device.code} (sector {sector})")
                    return True
                else:
                    print(f"[DEVICE] Hardware Manager open FAILED for {device.code} (sector {sector}), result={result}")
                    return False
            
            # 2. Fallback: прямой HTTP запрос (если нет в Hardware Manager)
            if device.protocol == "http":'''

if old_start in content:
    content = content.replace(old_start, new_start)
    with open('app/services/access_service.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Hardware Manager интегрирован!")
else:
    print("ERROR: Не найдена строка")
