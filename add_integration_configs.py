# add_integration_configs.py
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import json

# Подключаемся к БД
engine = create_engine("postgresql+psycopg://postgres:FitNexus_Postgres_2026!@127.0.0.1:5432/fitnexus")
Session = sessionmaker(bind=engine)
db = Session()

configs = [
    # Платежи
    (1, 'yookassa', 'payments', False, {"shop_id": "", "secret_key": "", "test_mode": True, "return_url": "https://fixintel.ru/payment/success"}),
    (1, 'sbp', 'payments', False, {"merchant_id": "", "terminal_id": "", "test_mode": True}),
    (1, 'tinkoff', 'payments', False, {"terminal_key": "", "password": "", "test_mode": True}),
    (1, 'sberbank', 'payments', False, {"token": "", "merchant": "", "test_mode": True}),
    (1, 'atol', 'payments', False, {"group_code": "", "login": "", "password": "", "test_mode": True}),
    
    # Бухгалтерия
    (1, '1c', 'accounting', False, {"base_url": "http://1c-server:8080/erp", "username": "", "password": "", "database": "FitClub"}),
    (1, 'moysklad', 'accounting', False, {"login": "", "password": "", "api_url": "https://online.moysklad.ru/api/remap/1.2"}),
    
    # CRM
    (1, 'bitrix24', 'crm', False, {"webhook_url": "", "api_key": "", "portal": "fixintel.bitrix24.ru"}),
    (1, 'amocrm', 'crm', False, {"subdomain": "", "client_id": "", "client_secret": "", "redirect_uri": ""}),
    (1, 'retailcrm', 'crm', False, {"api_url": "", "api_key": "", "site_code": ""}),
    
    # Мессенджеры
    (1, 'telegram', 'messaging', False, {"bot_token": "", "webhook_url": ""}),
    (1, 'max', 'messaging', False, {"bot_token": "", "api_url": "https://api.max.com/v1"}),
    (1, 'whatsapp', 'messaging', False, {"api_key": "", "phone_number_id": "", "business_id": ""}),
    
    # Телефония
    (1, 'mango', 'telephony', False, {"api_key": "", "api_salt": "", "vpbx_api_key": ""}),
    (1, 'zadarma', 'telephony', False, {"user_key": "", "secret": ""}),
    
    # Доставка
    (1, 'yandex_eda', 'delivery', False, {"api_key": "", "restaurant_id": ""}),
    (1, 'sbermarket', 'delivery', False, {"api_key": "", "store_id": ""}),
    
    # СКУД
    (1, 'era', 'access_control', False, {"ip": "", "port": 37777, "login": "", "password": ""}),
    
    # Видео
    (1, 'hikvision', 'video', False, {"ip": "", "port": 80, "login": "", "password": ""}),
    
    # Аналитика
    (1, 'yandex_metrika', 'analytics', False, {"counter_id": "", "token": ""}),
    (1, 'google_analytics', 'analytics', False, {"tracking_id": "", "property_id": ""}),
    
    # HR
    (1, '1c_zup', 'hr', False, {"base_url": "", "username": "", "password": ""}),
]

for club_id, provider, category, is_active, config in configs:
    db.execute(text("""
        INSERT INTO integration_configs (club_id, provider, category, is_active, config)
        VALUES (:club_id, :provider, :category, :is_active, :config)
        ON CONFLICT (club_id, provider) DO NOTHING
    """), {
        "club_id": club_id,
        "provider": provider,
        "category": category,
        "is_active": is_active,
        "config": json.dumps(config)
    })

db.commit()

# Проверяем
result = db.execute(text("""
    SELECT category, provider, is_active, sync_status 
    FROM integration_configs 
    WHERE club_id = 1
    ORDER BY category, provider
""")).fetchall()

print(f"Total configs: {len(result)}")
for row in result:
    print(f"  {row[0]} | {row[1]} | active={row[2]} | {row[3]}")

db.close()
print("Done!")
