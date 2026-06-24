# fix_trainer_fk.py
with open('app/models/trainer.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Убираем ForeignKey на halls
old = '    hall_id = Column(UUID(as_uuid=True), ForeignKey("halls.id", ondelete="SET NULL"))'
new = '    hall_id = Column(UUID(as_uuid=True))  # FK to halls.id — removed for compatibility'
content = content.replace(old, new)

# Убираем ForeignKey на products
old2 = '    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="SET NULL"))'
new2 = '    product_id = Column(UUID(as_uuid=True))  # FK to products.id — removed for compatibility'
content = content.replace(old2, new2)

with open('app/models/trainer.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("FK constraints removed!")
