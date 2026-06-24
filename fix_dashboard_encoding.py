# fix_dashboard_encoding.py
with open('app/api/v1/analytics_dashboard.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Заменяем кракозябры на нормальный русский
content = content.replace('тАФ', '—')
content = content.replace('╨Ф╨░╤И╨▒╨╛╤А╨┤', 'Дашборд')
content = content.replace('╨Р╨╜╨░╨╗╨╕╤В╨╕╤З╨╡╤Б╨║╨╕╨╣', 'Аналитический')
content = content.replace('╨Я╨╡╤А╨╕╨╛╨┤', 'Период')
content = content.replace('╨Ъ╨╗╤Г╨▒', 'Клуб')

with open('app/api/v1/analytics_dashboard.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Encoding fixed!")
