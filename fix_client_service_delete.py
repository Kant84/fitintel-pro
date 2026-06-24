# fix_client_service_delete.py
with open('app/services/client_service.py', 'r', encoding='utf-8') as f:
    content = f.read()

if 'def delete_client' not in content:
    # Находим последний метод и добавляем после него
    insert_point = content.find('def build_client_response')
    if insert_point == -1:
        insert_point = len(content)
    
    new_method = '''

    def delete_client(self, client):
        """Удаление клиента"""
        self.db.delete(client)
        self.db.commit()

'''
    content = content[:insert_point] + new_method + content[insert_point:]
    
    with open('app/services/client_service.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("delete_client добавлен в ClientService!")
else:
    print("delete_client уже существует")
