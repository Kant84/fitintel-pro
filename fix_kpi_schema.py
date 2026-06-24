# fix_kpi_schema.py
with open('app/schemas/trainer.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Находим TrainerKpiResponse и добавляем новые поля
old = '''class TrainerKpiResponse(BaseModel):
    id: UUID
    trainer_id: UUID
    year_month: str
    sessions_count: int
    sessions_personal: int
    sessions_group: int
    clients_total: int
    clients_new: int
    clients_retained: int
    clients_churned: int
    revenue_from_sessions: Decimal
    revenue_from_sales: Decimal
    commission_total: Decimal
    salary_total: Decimal
    rating_avg: Decimal
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True'''

new = '''class TrainerKpiResponse(BaseModel):
    id: UUID
    trainer_id: UUID
    year_month: str
    sessions_count: int
    sessions_personal: int
    sessions_group: int
    clients_total: int
    clients_new: int
    clients_retained: int
    clients_churned: int
    revenue_from_sessions: Decimal
    revenue_from_sales: Decimal
    commission_total: Decimal
    salary_total: Decimal
    # E19: Progressive salary
    rate_applied: Decimal
    bonus_new_clients: Decimal
    bonus_retention: Decimal
    bonus_sales: Decimal
    penalty_no_show: Decimal
    penalty_late_cancel: Decimal
    base_salary: Decimal
    total_bonus: Decimal
    total_penalty: Decimal
    net_salary: Decimal
    rating_avg: Decimal
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True'''

if old in content:
    content = content.replace(old, new)
    print("TrainerKpiResponse updated!")
else:
    print("Pattern not found")

with open('app/schemas/trainer.py', 'w', encoding='utf-8') as f:
    f.write(content)
