# fix_email_validation.py
with open('app/schemas/auth.py', 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace(
    'from pydantic import BaseModel, Field',
    'from pydantic import BaseModel, Field, EmailStr'
)

content = content.replace(
    '    email: str | None = None',
    '    email: EmailStr | None = None'
)

with open('app/schemas/auth.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("EmailStr добавлен!")
