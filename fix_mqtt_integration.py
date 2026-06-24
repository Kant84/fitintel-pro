# fix_mqtt_integration.py
with open('app/services/access_service.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_mqtt = '''            elif device.protocol == "mqtt":
                print(f"[DEVICE] MQTT open command (sector {sector}) sent to {device.address}")
                return True'''

new_mqtt = '''            elif device.protocol == "mqtt":
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
                    return False'''

if old_mqtt in content:
    content = content.replace(old_mqtt, new_mqtt)
    with open('app/services/access_service.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("MQTT интеграция добавлена!")
else:
    print("ERROR: Не найден блок MQTT")
