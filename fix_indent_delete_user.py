# fix_indent_delete_user.py
with open('app/services/user_service.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Исправляем отступ delete_user
content = content.replace(
    '    def delete_user(self, user):\n        """Удаление пользователя"""\n        self.db.delete(user)',
    '    def delete_user(self, user):\n        """Удаление пользователя"""\n        self.db.delete(user)\n        self.db.commit()'
)

with open('app/services/user_service.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("Исправлено!")
