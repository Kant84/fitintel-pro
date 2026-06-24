# init_hardware_manager.py
with open('app/main.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Найдём startup_event и добавим инициализацию DeviceManager
old_startup = '''@app.on_event("startup")
async def startup_event():'''

new_startup = '''@app.on_event("startup")
async def startup_event():
    # Инициализация Hardware Manager с ACS ACR1252U
    from app.hardware.manager import DeviceManager
    acs_config = {
        "device_id": "acs_reader_main",
        "driver_class": "AcsAcr1252uDriver",
        "reader_name": "ACS ACR1252 1S CL Reader PICC 0",
    }
    await DeviceManager.add_device(acs_config)
    print("[HW] ACS ACR1252U initialized")'''

if old_startup in content:
    content = content.replace(old_startup, new_startup)
    with open('app/main.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("DeviceManager инициализация добавлена!")
else:
    print("ERROR: Не найден startup_event")
