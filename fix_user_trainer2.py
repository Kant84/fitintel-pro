# fix_user_trainer2.py
with open('app/models/user.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Убираем дублирующий import
content = content.replace(
    'from sqlalchemy.orm import relationship, Mapped, mapped_column, relationship',
    'from sqlalchemy.orm import Mapped, mapped_column, relationship'
)

# Добавляем trainer_profile перед shifts
old = '''    shifts: Mapped[list["EmployeeShift"]] = relationship(
        "EmployeeShift",
        back_populates="employee",
        foreign_keys="EmployeeShift.employee_id",
    )'''

new = '''    # Trainer profile (E17)
    trainer_profile: Mapped["TrainerProfile"] = relationship(
        "TrainerProfile",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )

    shifts: Mapped[list["EmployeeShift"]] = relationship(
        "EmployeeShift",
        back_populates="employee",
        foreign_keys="EmployeeShift.employee_id",
    )'''

if 'trainer_profile' not in content:
    content = content.replace(old, new)
    print("trainer_profile added!")
else:
    print("trainer_profile already exists")

with open('app/models/user.py', 'w', encoding='utf-8') as f:
    f.write(content)
