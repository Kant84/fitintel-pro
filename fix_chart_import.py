# fix_chart_import.py
with open('app/api/v1/analytics_chart.py', 'r', encoding='utf-8') as f:
    content = f.read()

if 'import json' not in content:
    content = 'import json\\n' + content
    with open('app/api/v1/analytics_chart.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("import json added!")
else:
    print("Already has import json")
