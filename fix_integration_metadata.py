# fix_integration_metadata.py
with open('app/models/integration.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Исправляем metadata на meta_data
content = content.replace(
    '    metadata = Column(JSON)',
    '    meta_data = Column(JSON)'
)

with open('app/models/integration.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Fixed metadata -> meta_data!")

# Исправляем сервис
with open('app/services/integration_service.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Исправляем metadata на meta_data
content = content.replace(
    '            metadata=metadata or {}',
    '            meta_data=metadata or {}'
)

content = content.replace(
    '                **(metadata or {})',
    '                **(metadata or {})'
)

content = content.replace(
    '            metadata=metadata or {}',
    '            meta_data=metadata or {}'
)

with open('app/services/integration_service.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Fixed service!")
