# fix_trainer_models.py
with open('app/models/trainer.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Убираем hall relationship из TrainerSchedule
old_hall = '''    hall = relationship("Hall")'''
content = content.replace(old_hall, '''    # hall relationship removed — use hall_id only''')

# Убираем product relationship из TrainerSale
old_product = '''    product = relationship("Product")'''
content = content.replace(old_product, '''    # product relationship removed — use product_id only''')

with open('app/models/trainer.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Trainer models fixed!")
