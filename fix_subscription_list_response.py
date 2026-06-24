# fix_subscription_list_response.py
with open('app/services/subscription_service.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_method = '''    def build_subscription_list_response(self, subscriptions: list[Subscription]) -> dict:
        pass'''

new_method = '''    def build_subscription_list_response(self, subscriptions: list[Subscription]) -> dict:
        items = [self.build_subscription_response(sub) for sub in subscriptions]
        return {
            "items": items,
            "count": len(items),
        }'''

if old_method in content:
    content = content.replace(old_method, new_method)
    with open('app/services/subscription_service.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("build_subscription_list_response исправлен!")
else:
    print("Не найден метод для замены")
