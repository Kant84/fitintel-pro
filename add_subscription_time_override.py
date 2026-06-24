# add_subscription_time_override.py
with open('app/schemas/subscription.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Добавляем импорт time
old_import = '''from datetime import datetime'''
new_import = '''from datetime import datetime, time'''

if old_import in content:
    content = content.replace(old_import, new_import)

# Добавляем поля в SubscriptionCreateRequest
old_fields = '''    notes: str | None = Field(
        default=None,
        description="Комментарий к созданию абонемента",
        examples=["Первичная продажа"],
    )


# ==========================================================
# СХЕМА ОБНОВЛЕНИЯ АБОНЕМЕНТА'''

new_fields = '''    notes: str | None = Field(
        default=None,
        description="Комментарий к созданию абонемента",
        examples=["Первичная продажа"],
    )
    
    # Переопределение временных ограничений (опционально)
    time_restriction_type: str | None = Field(
        default=None,
        description="Переопределить тип ограничения: FULLDAY, DAYTIME, NIGHTTIME (если не указано — берётся из тарифа)",
        examples=["DAYTIME"],
    )
    allowed_start_time: time | None = Field(
        default=None,
        description="Переопределить время начала доступа (если не указано — берётся из тарифа)",
        examples=["10:00:00"],
    )
    allowed_end_time: time | None = Field(
        default=None,
        description="Переопределить время окончания доступа (если не указано — берётся из тарифа)",
        examples=["18:00:00"],
    )


# ==========================================================
# СХЕМА ОБНОВЛЕНИЯ АБОНЕМЕНТА'''

if old_fields in content:
    content = content.replace(old_fields, new_fields)
    with open('app/schemas/subscription.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Поля временных ограничений добавлены в SubscriptionCreateRequest!")
else:
    print("ERROR: Не найдены поля для вставки")
