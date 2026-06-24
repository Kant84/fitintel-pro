# fix_user_service_delete.py
with open('app/services/user_service.py', 'r', encoding='utf-8') as f:
    content = f.read()

if 'def delete_user' not in content:
    insert_point = content.find('def build_user_response')
    new_method = '''
    def delete_user(self, user):
        """Удаление пользователя"""
        self.db.delete(user)
        self.db.commit()

'''
    content = content[:insert_point] + new_method + content[insert_point:]
    with open('app/services/user_service.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("delete_user добавлен!")
else:
    print("delete_user уже существует")
