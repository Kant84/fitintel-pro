Get-Process python -ErrorAction SilentlyContinue | Where-Object { $_.MainWindowTitle -like "*FitIntel*" } | Stop-Process -Force
Start-Sleep -Milliseconds 500
python -B main.py
