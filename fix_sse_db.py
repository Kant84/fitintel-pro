# fix_sse_db.py
with open('app/api/v1/sse.py', 'r', encoding='utf-8') as f:
    content = f.read()

old = '''    return StreamingResponse(
        event_generator(club_id, db),'''

new = '''    return StreamingResponse(
        event_generator(club_id),'''

if old in content:
    content = content.replace(old, new)
    with open('app/api/v1/sse.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("SSE fixed!")
else:
    print("ERROR")
