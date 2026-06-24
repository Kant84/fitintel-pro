# fix_sale_schema.py
with open('app/schemas/trainer.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Находим TrainerSaleCreate и делаем trainer_id optional
old = '''class TrainerSaleCreate(TrainerSaleBase):
    trainer_id: UUID'''

new = '''class TrainerSaleCreate(TrainerSaleBase):
    trainer_id: Optional[UUID] = None'''

if old in content:
    content = content.replace(old, new)
    print("TrainerSaleCreate fixed!")
else:
    print("Pattern not found — checking...")
    # Проверяем что есть
    import re
    match = re.search(r'class TrainerSaleCreate.*?(?=class |\Z)', content, re.DOTALL)
    if match:
        print("Found:", match.group()[:200])

with open('app/schemas/trainer.py', 'w', encoding='utf-8') as f:
    f.write(content)
