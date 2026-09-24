# -*- coding: utf-8 -*-
"""Авто-патч: добавляет таймаут 10 сек всем запросам ApiClient (идемпотентно)."""
import sys

P = r"C:\Users\PC\Desktop\2026\FitNexus AI\FitIntel AI\fitintel-desktop\api\client.py"

MARKER = "# Таймаут по умолчанию (10 сек)"
ANCHOR = '            self.session.hooks["response"].append(_resp_hook)\n        except Exception:\n            pass\n'
BLOCK = '''
        # Таймаут по умолчанию (10 сек) для ВСЕХ запросов сессии.
        # Без этого зависшие запросы висят вечно и копятся в фоновых потоках.
        _orig_request = self.session.request
        def _request_with_timeout(method, url, **kwargs):
            kwargs.setdefault("timeout", 10)
            return _orig_request(method, url, **kwargs)
        self.session.request = _request_with_timeout
'''

src = open(P, encoding="utf-8").read()
if MARKER in src:
    print("Уже применено — ничего не изменено.")
elif ANCHOR in src:
    open(P, "w", encoding="utf-8").write(src.replace(ANCHOR, ANCHOR + BLOCK, 1))
    print("ГОТОВО: таймаут добавлен в api/client.py")
else:
    print("АНКОР НЕ НАЙДЕН — файл изменён вручную, патч не применён.")
    sys.exit(1)
