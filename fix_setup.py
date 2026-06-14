import re

with open('app/api/v1/setup.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Заменяем старый get_license_status на новый
old = """@router.get("/license/status", response_model=LicenseStatusResponse)
async def get_license_status() -> dict[str, Any]:
    """Check current license status (no auth required — needed for initial setup)."""
    key = LicenseState.get_license_key()
    if not key:
        return {"is_licensed": False}

    # Read from state file
    if not LicenseState.is_licensed():
        return {"is_licensed": False, "license_key": key[:8] + "..."}"""

new = """@router.get("/license/status", response_model=LicenseStatusResponse)
async def get_license_status() -> dict[str, Any]:
    """Check current license status (no auth required — needed for initial setup)."""
    is_licensed = LicenseState.is_licensed()
    key = LicenseState.get_license_key()
    
    if not is_licensed or not key:
        return {"is_licensed": False}"""

if old in content:
    content = content.replace(old, new)
    with open('app/api/v1/setup.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("FIXED!")
else:
    print("Pattern not found")