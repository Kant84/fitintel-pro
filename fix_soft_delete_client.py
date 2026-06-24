# fix_soft_delete_client.py
with open('app/services/client_service.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_delete = '''    def delete_client(self, client):
        """Удаление клиента"""
        self.db.delete(client)
        self.db.commit()'''

new_delete = '''    def delete_client(self, client):
        """Мягкое удаление клиента (деактивация)"""
        client.is_active = False
        client.status = 'INACTIVE'
        self.db.commit()'''

if old_delete in content:
    content = content.replace(old_delete, new_delete)
    with open('app/services/client_service.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Мягкое удаление клиента добавлено!")
else:
    print("Не найден метод delete_client")
