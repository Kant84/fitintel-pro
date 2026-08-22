import io
p = "windows/main_window.py"
src = io.open(p, encoding="utf-8").read()
src = src.replace('self.setWindowTitle("FitIntel Pro — Система управления")',
                  'self.setWindowTitle("FitIntel Pro — Система управления [sidebar v2]")')
io.open(p, "w", encoding="utf-8").write(src)
print("title marker OK")
