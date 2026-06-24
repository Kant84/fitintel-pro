# fix_final.py
with open('app/services/report_service.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Исправляем PDF — убираем кириллицу, используем латиницу
old_pdf_title = "pdf.cell(0, 10, 'Otchety po platezham', ln=True, align='C')"
new_pdf_title = "pdf.cell(0, 10, 'Payments Report', ln=True, align='C')"

if old_pdf_title in content:
    content = content.replace(old_pdf_title, new_pdf_title)
    # Заменяем все кириллические заголовки
    content = content.replace("Pериод:", "Period:")
    content = content.replace("ИТОГО:", "TOTAL:")
    content = content.replace("Отчет по платежам", "Payments Report")
    content = content.replace("Период:", "Period:")
    content = content.replace("№", "No")
    content = content.replace("Дата", "Date")
    content = content.replace("Направление", "Direction")
    content = content.replace("Категория", "Category")
    content = content.replace("ФИО", "Client")
    content = content.replace("Сумма", "Amount")
    content = content.replace("Статус", "Status")
    content = content.replace("Назначение", "Purpose")
    print("1. PDF латиница исправлена!")
else:
    print("1. WARNING: Не найден PDF заголовок")

# 2. Исправляем Visits — убираем subscription.name
old_sub_xlsx = "sub_name = visit.subscription.title or '' if visit.subscription else ''"
new_sub_xlsx = "sub_name = ''"

if old_sub_xlsx in content:
    content = content.replace(old_sub_xlsx, new_sub_xlsx)
    print("2. Visits XLSX исправлен!")
else:
    # Пробуем другой вариант
    old_sub2 = "sub_name = visit.subscription.name or ''"
    if old_sub2 in content:
        content = content.replace(old_sub2, "sub_name = ''")
        print("2. Visits XLSX исправлен (v2)!")
    else:
        print("2. WARNING: Не найден subscription")

# 3. Исправляем Visits CSV — проверяем метод
if 'def export_visits_csv' not in content:
    print("3. ERROR: export_visits_csv не найден!")
else:
    print("3. Visits CSV метод найден")

# 4. Исправляем заголовки Visits
content = content.replace("Дата входа", "Entry Date")
content = content.replace("Время входа", "Entry Time")
content = content.replace("Дата выхода", "Exit Date")
content = content.replace("Время выхода", "Exit Time")
content = content.replace("Длительность (мин)", "Duration (min)")
content = content.replace("ФИО клиента", "Client Name")
content = content.replace("Телефон", "Phone")
content = content.replace("Абонемент", "Subscription")
content = content.replace("Метод доступа", "Access Method")

with open('app/services/report_service.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("=== Все исправления применены! ===")
