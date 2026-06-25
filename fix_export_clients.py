# fix_export_clients.py
with open('app/services/export_service.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Исправляем запрос clients — убираем club_id
old = '''        if entity == 'clients':
            query = text("""
                SELECT id, first_name, last_name, phone, email, birth_date, status, created_at
                FROM clients
                WHERE club_id = :club_id
                ORDER BY created_at DESC
            """)
            result = self.db.execute(query, {"club_id": club_id}).mappings().all()'''

new = '''        if entity == 'clients':
            query = text("""
                SELECT id, first_name, last_name, phone, email, birth_date, status, created_at
                FROM clients
                ORDER BY created_at DESC
                LIMIT 1000
            """)
            result = self.db.execute(query).mappings().all()'''

if old in content:
    content = content.replace(old, new)
    print("Clients query fixed!")
else:
    print("Pattern not found")

with open('app/services/export_service.py', 'w', encoding='utf-8') as f:
    f.write(content)
