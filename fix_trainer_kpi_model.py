# fix_trainer_kpi_model.py
with open('app/models/trainer.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Находим TrainerKpiMonthly и добавляем новые поля
old_fields = '''    rating_avg = Column(Numeric(3, 2), default=0)
    created_at = Column(TIMESTAMP, default="now()")
    updated_at = Column(TIMESTAMP, default="now()")'''

new_fields = '''    rate_applied = Column(Numeric(10, 2), default=0)
    bonus_new_clients = Column(Numeric(10, 2), default=0)
    bonus_retention = Column(Numeric(10, 2), default=0)
    bonus_sales = Column(Numeric(10, 2), default=0)
    penalty_no_show = Column(Numeric(10, 2), default=0)
    penalty_late_cancel = Column(Numeric(10, 2), default=0)
    base_salary = Column(Numeric(12, 2), default=0)
    total_bonus = Column(Numeric(12, 2), default=0)
    total_penalty = Column(Numeric(12, 2), default=0)
    net_salary = Column(Numeric(12, 2), default=0)
    rating_avg = Column(Numeric(3, 2), default=0)
    created_at = Column(TIMESTAMP, default="now()")
    updated_at = Column(TIMESTAMP, default="now()")'''

if old_fields in content:
    content = content.replace(old_fields, new_fields)
    print("TrainerKpiMonthly updated!")
else:
    print("Pattern not found")

with open('app/models/trainer.py', 'w', encoding='utf-8') as f:
    f.write(content)
