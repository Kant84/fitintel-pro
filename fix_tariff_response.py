# fix_tariff_response.py
with open('app/services/tariff_service.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_response = '''    def build_tariff_response(self, tariff: Tariff) -> dict:
        # возвращаем словарь ответа
        return {
            "id": tariff.id,
            "code": tariff.code,
            "name": tariff.name,
            "description": tariff.description,
            "price": tariff.price,
            "currency": tariff.currency,
            "duration_days": tariff.duration_days,
            "visit_limit": tariff.visit_limit,
            "is_unlimited": tariff.is_unlimited,
            "is_active": tariff.is_active,
            "created_at": tariff.created_at,
            "updated_at": tariff.updated_at,
        }'''

new_response = '''    def build_tariff_response(self, tariff: Tariff) -> dict:
        # возвращаем словарь ответа
        return {
            "id": tariff.id,
            "code": tariff.code,
            "name": tariff.name,
            "description": tariff.description,
            "price": tariff.price,
            "currency": tariff.currency,
            "duration_days": tariff.duration_days,
            "visit_limit": tariff.visit_limit,
            "is_unlimited": tariff.is_unlimited,
            "is_active": tariff.is_active,
            "promo_code": tariff.promo_code,
            "discount_percent": tariff.discount_percent,
            "created_at": tariff.created_at,
            "updated_at": tariff.updated_at,
        }'''

if old_response in content:
    content = content.replace(old_response, new_response)
    with open('app/services/tariff_service.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("build_tariff_response обновлён!")
else:
    print("Не найден метод build_tariff_response")
