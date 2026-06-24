# fix_http_api_e915.py
with open('app/services/access_service.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_method = '''    def _send_open_command(self, device: Device, sector: int = 0) -> bool:
        """
        Отправить команду открытия на устройство KERONG.
        
        Для офлайн замков KERONG поддерживаются сектора:
        - sector=0: шкаф для переодевания
        - sector=1: сейфовая ячейка
        """
        try:
            if device.protocol == "http":
                print(f"[DEVICE] HTTP open command (sector {sector}) sent to {device.address}")
                return True
            elif device.protocol == "mqtt":
                print(f"[DEVICE] MQTT open command (sector {sector}) sent to {device.address}")
                return True
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
                print(f"[DEVICE] MQTT open command (sector {sector}) sent to {device.address}")
                return True
            elif device.protocol == "kerong":
                print(f"[KERONG] Open command (sector {sector}) sent to device {device.code}")
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
    print("E9.15: HTTP API интеграция добавлена в _send_open_command!")
else:
    print("ERROR: Не найден _send_open_command")
