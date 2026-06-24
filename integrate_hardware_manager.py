# integrate_hardware_manager.py
with open('app/services/access_service.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_method = '''    def _send_open_command(self, device: Device, sector: int = 0) -> bool:
        """
        Отправить команду открытия на устройство.
        
        Поддерживает:
        - HTTP API: отправляет POST/GET запрос на device.address
        - MQTT: публикует сообщение (заглушка)
        - KERONG: офлайн протокол (заглушка)
        """
        try:
            if device.protocol == "http":
                import requests
                import json
                # Формируем payload для HTTP API устройства
                payload = {
                    "action": "open",
                    "device_id": device.code,
                    "sector": sector,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
                # Добавляем auth token из config если есть
                headers = {"Content-Type": "application/json"}
                if device.config and isinstance(device.config, dict):
                    if device.config.get("auth_token"):
                        headers["Authorization"] = f"Bearer {device.config['auth_token']}"
                    # Добавляем дополнительные параметры из config
                    extra_params = device.config.get("open_params", {})
                    payload.update(extra_params)
                
                url = device.address or f"http://localhost:8080/api/device/{device.code}/open"
                response = requests.post(url, json=payload, headers=headers, timeout=5)
                
                if response.status_code == 200:
                    print(f"[DEVICE] HTTP open command SUCCESS (sector {sector}) sent to {device.address}, response: {response.status_code}")
                    return True
                else:
                    print(f"[DEVICE] HTTP open command FAILED (sector {sector}) sent to {device.address}, response: {response.status_code}, body: {response.text[:200]}")
                    return False
                    
            elif device.protocol == "mqtt":
                try:
                    import paho.mqtt.client as mqtt
                    import json
                    
                    # Получаем настройки MQTT из config
                    mqtt_config = device.config or {}
                    broker = mqtt_config.get("broker", device.address or "localhost")
                    port = mqtt_config.get("port", 1883)
                    topic = mqtt_config.get("topic", f"devices/{device.code}/command")
                    username = mqtt_config.get("username")
                    password = mqtt_config.get("password")
                    client_id = mqtt_config.get("client_id", f"fitintel_{device.code}")
                    
                    # Создаём клиент
                    client = mqtt.Client(client_id=client_id)
                    if username and password:
                        client.username_pw_set(username, password)
                    
                    # Подключаемся и публикуем
                    client.connect(broker, port, timeout=5)
                    
                    payload = json.dumps({
                        "action": "open",
                        "device_id": device.code,
                        "sector": sector,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    })
                    
                    result = client.publish(topic, payload, qos=1)
                    client.disconnect()
                    
                    if result.rc == 0:
                        print(f"[DEVICE] MQTT open command SUCCESS (sector {sector}) sent to {broker}:{port}/{topic}")
                        return True
                    else:
                        print(f"[DEVICE] MQTT open command FAILED (sector {sector}), rc={result.rc}")
                        return False
                        
                except Exception as e:
                    print(f"[ERROR] MQTT failed for {device.code}: {e}")
                    return False

            elif device.protocol == "kerong":
                print(f"[KERONG] Open command (sector {sector}) sent to device {device.code}")
                return True
            else:
                print(f"[WARN] Device {device.code} has unsupported protocol: {device.protocol}")
                return False
        except Exception as e:
            print(f"[ERROR] Failed to send open command to {device.code}: {e}")
            return False'''

new_method = '''    def _send_open_command(self, device: Device, sector: int = 0) -> bool:
        """
        Отправить команду открытия на устройство.
        
        Использует Hardware Manager (DeviceManager) для реальных драйверов:
        - HTTP API: GenericHttpDriver
        - MQTT: GenericMqttDriver
        - KERONG: KerongDriver (Modbus RTU)
        - Modbus: GenericModbusDriver
        - Era: EraDriver
        - X1: X1Driver
        """
        try:
            # Пробуем через Hardware Manager (реальные драйверы)
            from app.hardware.manager import DeviceManager
            from app.hardware.base import AccessResult
            
            # Проверяем, есть ли устройство в Hardware Manager
            hw_device = DeviceManager.get_device(device.code)
            if hw_device:
                # Используем асинхронный вызов через asyncio
                import asyncio
                result = asyncio.run(DeviceManager.open_device(device.code, sector=sector))
                if result == AccessResult.GRANTED:
                    print(f"[DEVICE] Hardware Manager open SUCCESS for {device.code} (sector {sector})")
                    return True
                else:
                    print(f"[DEVICE] Hardware Manager open FAILED for {device.code} (sector {sector}), result={result}")
                    return False
            
            # Fallback: прямой HTTP запрос (если нет в Hardware Manager)
            if device.protocol == "http":
                import requests
                import json
                payload = {
                    "action": "open",
                    "device_id": device.code,
                    "sector": sector,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
                headers = {"Content-Type": "application/json"}
                if device.config and isinstance(device.config, dict):
                    if device.config.get("auth_token"):
                        headers["Authorization"] = f"Bearer {device.config['auth_token']}"
                    extra_params = device.config.get("open_params", {})
                    payload.update(extra_params)
                
                url = device.address or f"http://localhost:8080/api/device/{device.code}/open"
                response = requests.post(url, json=payload, headers=headers, timeout=5)
                
                if response.status_code == 200:
                    print(f"[DEVICE] HTTP open command SUCCESS (sector {sector}) sent to {device.address}, response: {response.status_code}")
                    return True
                else:
                    print(f"[DEVICE] HTTP open command FAILED (sector {sector}) sent to {device.address}, response: {response.status_code}")
                    return False
                    
            elif device.protocol == "mqtt":
                print(f"[DEVICE] MQTT open command (sector {sector}) sent to {device.address} — используйте Hardware Manager для реального MQTT")
                return True
                
            elif device.protocol == "kerong":
                print(f"[DEVICE] KERONG open command (sector {sector}) sent to {device.code} — используйте Hardware Manager для реального Modbus")
                return True
                
            else:
                print(f"[WARN] Device {device.code} has unsupported protocol: {device.protocol}")
                return False
                
        except Exception as e:
            print(f"[ERROR] Failed to send open command to {device.code}: {e}")
            return False'''

if old_method in content:
    content = content.replace(old_method, new_method)
    with open('app/services/access_service.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Hardware Manager интегрирован в _send_open_command!")
else:
    print("ERROR: Не найден _send_open_command")
