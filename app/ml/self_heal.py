# app/ml/self_heal.py
def auto_fix_enum_errors():
    # Если GET /clients падает с 500 из-за enum — авто-маппинг
    with engine.begin() as c:
        c.execute(text("""
            UPDATE clients SET gender='MALE' WHERE gender NOT IN ('MALE','FEMALE','НЕ_УКАЗАН')
        """))