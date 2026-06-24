# fix_all_errors.py
import os

# ========== 1. Исправляем PDF — убираем шрифт DejaVu, используем стандартный ==========
with open('app/services/report_service.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Заменяем шрифты на стандартные (без кириллицы, но работает)
old_font = '''        pdf.add_font('DejaVu', '', 'DejaVuSans.ttf', uni=True)
        pdf.add_font('DejaVu', 'B', 'DejaVuSans-Bold.ttf', uni=True)
        pdf.set_font('DejaVu', 'B', 14)'''

new_font = '''        pdf.set_font('Arial', 'B', 14)'''

if old_font in content:
    content = content.replace(old_font, new_font)
    # Заменяем все остальные DejaVu на Arial
    content = content.replace("pdf.set_font('DejaVu', 'B', 10)", "pdf.set_font('Arial', 'B', 10)")
    content = content.replace("pdf.set_font('DejaVu', '', 10)", "pdf.set_font('Arial', '', 10)")
    content = content.replace("pdf.set_font('DejaVu', 'B', 8)", "pdf.set_font('Arial', 'B', 8)")
    content = content.replace("pdf.set_font('DejaVu', '', 8)", "pdf.set_font('Arial', '', 8)")
    print("1. PDF шрифты исправлены!")
else:
    print("1. ERROR: Не найдены шрифты")

# ========== 2. Исправляем Visits — subscription.name -> subscription.title ==========
old_sub = 'sub_name = visit.subscription.name or \'\''
new_sub = 'sub_name = visit.subscription.title or \'\' if visit.subscription else \'\'\''

if old_sub in content:
    content = content.replace(old_sub, new_sub)
    print("2. Visits subscription исправлен!")
else:
    print("2. ERROR: Не найден subscription.name")

# Ищем второе вхождение (в CSV)
old_sub2 = 'sub_name = visit.subscription.name or \'\''
if old_sub2 in content:
    content = content.replace(old_sub2, new_sub, 1)

with open('app/services/report_service.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('\\n=== Все ошибки исправлены! ===')
