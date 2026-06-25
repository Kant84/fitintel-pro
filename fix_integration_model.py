# fix_integration_model.py
with open('app/models/integration.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Исправляем Decimal на Numeric
content = content.replace(
    'from sqlalchemy import Column, String, Integer, Boolean, Text, ForeignKey, TIMESTAMP, JSON',
    'from sqlalchemy import Column, String, Integer, Numeric, Boolean, Text, ForeignKey, TIMESTAMP, JSON'
)

content = content.replace(
    '    amount = Column(Base.Decimal(10, 2), nullable=False)',
    '    amount = Column(Numeric(10, 2), nullable=False)'
)

with open('app/models/integration.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Fixed!")
