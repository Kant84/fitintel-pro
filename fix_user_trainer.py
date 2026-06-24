# fix_user_trainer.py
with open('app/models/user.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Проверяем, есть ли уже импорт relationship
if 'from sqlalchemy.orm import relationship' not in content:
    # Добавляем импорт
    old = 'from sqlalchemy.orm import'
    if old in content:
        content = content.replace(old, old + ' relationship,')
    else:
        content = 'from sqlalchemy.orm import relationship\n' + content

# Добавляем trainer_profile relationship в класс User
old_class = 'class User(Base):'
if old_class in content and 'trainer_profile' not in content:
    # Находим конец класса или добавляем перед последним полем
    # Ищем место для добавления
    insert_marker = '    # Добавьте другие поля при необходимости'
    if insert_marker in content:
        content = content.replace(
            insert_marker,
            insert_marker + '\n    trainer_profile = relationship("TrainerProfile", back_populates="user", uselist=False)'
        )
    else:
        # Добавляем в конец класса (перед другими классами)
        # Находим последнее поле в User
        pass

with open('app/models/user.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("User model updated!")
