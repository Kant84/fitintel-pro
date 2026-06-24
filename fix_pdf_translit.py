# fix_pdf_translit.py
with open('app/services/report_service.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Добавляем функцию транслитерации
old_pdf = '    def export_payments_pdf('

new_pdf = '''    def _translit(self, text):
        """Транслитерация русских символов для PDF"""
        if not text:
            return ''
        translit_map = {
            'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'yo',
            'ж': 'zh', 'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm',
            'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u',
            'ф': 'f', 'х': 'h', 'ц': 'ts', 'ч': 'ch', 'ш': 'sh', 'щ': 'sch', 'ъ': '',
            'ы': 'y', 'ь': '', 'э': 'e', 'ю': 'yu', 'я': 'ya',
            'А': 'A', 'Б': 'B', 'В': 'V', 'Г': 'G', 'Д': 'D', 'Е': 'E', 'Ё': 'Yo',
            'Ж': 'Zh', 'З': 'Z', 'И': 'I', 'Й': 'Y', 'К': 'K', 'Л': 'L', 'М': 'M',
            'Н': 'N', 'О': 'O', 'П': 'P', 'Р': 'R', 'С': 'S', 'Т': 'T', 'У': 'U',
            'Ф': 'F', 'Х': 'H', 'Ц': 'Ts', 'Ч': 'Ch', 'Ш': 'Sh', 'Щ': 'Sch', 'Ъ': '',
            'Ы': 'Y', 'Ь': '', 'Э': 'E', 'Ю': 'Yu', 'Я': 'Ya',
        }
        result = ''
        for char in text:
            result += translit_map.get(char, char)
        return result
    
    def export_payments_pdf('''

if old_pdf in content:
    content = content.replace(old_pdf, new_pdf)
    
    # Транслитерируем данные в PDF
    old_client = "client_name = ' '.join(parts)"
    new_client = "client_name = self._translit(' '.join(parts))"
    
    content = content.replace(old_client, new_client)
    
    # Транслитерируем notes
    old_notes = "(payment.notes or '')[:30]"
    new_notes = "self._translit((payment.notes or '')[:30])"
    
    content = content.replace(old_notes, new_notes)
    
    with open('app/services/report_service.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("PDF транслитерация добавлена!")
else:
    print("ERROR: Не найден export_payments_pdf")
