# fix_recalc_text.py
with open('app/services/analytics_service.py', 'r', encoding='utf-8') as f:
    content = f.read()

old = '''        # Вызываем SQL-функцию
        self.db.execute(
            "SELECT recalc_analytics_daily(:club_id, :date)",
            {"club_id": club_id, "date": target_date},
        )
        self.db.commit()'''

new = '''        from sqlalchemy import text
        # Вызываем SQL-функцию
        self.db.execute(
            text("SELECT recalc_analytics_daily(:club_id, :date)"),
            {"club_id": club_id, "date": target_date},
        )
        self.db.commit()'''

if old in content:
    content = content.replace(old, new)
    with open('app/services/analytics_service.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("recalc fixed!")
else:
    print("ERROR: Не найден блок")
