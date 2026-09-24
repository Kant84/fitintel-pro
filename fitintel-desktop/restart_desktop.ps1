Set-Location $PSScriptRoot
Get-Process python -ErrorAction SilentlyContinue | Where-Object { $_.MainWindowTitle -like "*FitIntel*" } | Stop-Process -Force
Start-Sleep -Milliseconds 500
& "C:\Users\PC\Desktop\2026\FitNexus AI\FitIntel AI\.venv\Scripts\python.exe" -B main.py
