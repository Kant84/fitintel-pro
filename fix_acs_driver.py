# fix_acs_driver.py
with open('app/hardware/drivers/acs_acr1252u.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Исправляем DeviceType
content = content.replace('DeviceType.CARD_READER, DeviceType.NFC_READER', 'DeviceType.READER')

# Исправляем ConnectionProtocol
content = content.replace('ConnectionProtocol.USB, ConnectionProtocol.PCSC', 'ConnectionProtocol.SDK')

with open('app/hardware/drivers/acs_acr1252u.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("ACS драйвер исправлен!")
