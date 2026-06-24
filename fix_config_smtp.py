# fix_config_smtp.py
with open('app/core/config.py', 'r', encoding='utf-8') as f:
    content = f.read()

old = '''    REDIS_PASSWORD: str | None = Field(
        default=None,
        description="Пароль Redis, если включена защита.",
    )

    # ==========================================================
    # 5. CORS
    # =========================================================='''

new = '''    REDIS_PASSWORD: str | None = Field(
        default=None,
        description="Пароль Redis, если включена защита.",
    )

    # ==========================================================
    # 5. SMTP Email
    # ==========================================================
    SMTP_HOST: str = Field(
        default="",
        description="SMTP хост (например, mail.fixintel.ru)",
    )
    SMTP_PORT: int = Field(
        default=587,
        description="SMTP порт (обычно 587)",
    )
    SMTP_USER: str = Field(
        default="",
        description="SMTP пользователь (email)",
    )
    SMTP_PASSWORD: str = Field(
        default="",
        description="SMTP пароль",
    )
    SMTP_TLS: bool = Field(
        default=True,
        description="Использовать TLS",
    )
    SMTP_FROM_NAME: str = Field(
        default="FitIntel PRO",
        description="Имя отправителя",
    )
    SMTP_FROM_EMAIL: str = Field(
        default="",
        description="Email отправителя",
    )

    # ==========================================================
    # 6. CORS
    # =========================================================='''

if old in content:
    content = content.replace(old, new)
    with open('app/core/config.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("SMTP config added!")
else:
    print("ERROR: Не найден блок")
