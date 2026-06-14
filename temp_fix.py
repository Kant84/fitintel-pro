import re
with open('app/api/v1/setup.py') as f: c=f.read()
c=c.replace('key = LicenseState.get_license_key()','is_licensed = LicenseState.is_licensed()\n    key = LicenseState.get_license_key()')
c=c.replace('if not key:','if not is_licensed or not key:')
open('app/api/v1/setup.py','w').write(c)
print('OK')
