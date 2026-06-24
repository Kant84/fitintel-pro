# fix_sse_signature.py
with open('app/api/v1/sse.py', 'r', encoding='utf-8') as f:
    content = f.read()

old = '''async def event_generator(club_id: int, db):'''

new = '''async def event_generator(club_id: int):'''

if old in content:
    content = content.replace(old, new)
    with open('app/api/v1/sse.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("SSE signature fixed!")
else:
    print("ERROR")
