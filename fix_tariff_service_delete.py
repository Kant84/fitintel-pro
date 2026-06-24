# fix_tariff_service_delete.py
with open('app/services/tariff_service.py', 'r', encoding='utf-8') as f:
    content = f.read()

if 'def delete_tariff' not in content:
    insert_point = content.find('    def build_tariff_response')
    
    new_method = '''
    def delete_tariff(self, tariff):
        """Удаление тарифа"""
        self.db.delete(tariff)
        self.db.commit()

'''
    content = content[:insert_point] + new_method + content[insert_point:]
    
    with open('app/services/tariff_service.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("delete_tariff добавлен!")
else:
    print("delete_tariff уже существует")
