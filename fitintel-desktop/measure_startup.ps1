Set-Location $PSScriptRoot
Get-Process python -ErrorAction SilentlyContinue | Where-Object { $_.MainWindowTitle -like "*FitIntel*" } | Stop-Process -Force
Start-Sleep -Milliseconds 500
Remove-Item startup_out.txt, startup_err.txt -ErrorAction SilentlyContinue

$t0 = Get-Date
Start-Process "C:\Users\PC\Desktop\2026\FitNexus AI\FitIntel AI\.venv\Scripts\python.exe" `
    -ArgumentList "-B","-u","main.py" `
    -RedirectStandardOutput startup_out.txt -RedirectStandardError startup_err.txt | Out-Null

$loginShown = $false
while ($true) {
    $p = Get-Process python -ErrorAction SilentlyContinue |
         Where-Object { $_.MainWindowTitle -like "*FitIntel*" } |
         Select-Object -First 1
    if ($p) {
        if (-not $loginShown) {
            $loginShown = $true
            Write-Host ("Окно логина:    {0:N1} сек" -f ((Get-Date) - $t0).TotalSeconds)
            Write-Host "Войдите в систему..."
        }
        if ($p.MainWindowTitle -like "*Система управления*") {
            Write-Host ("Главное окно:   {0:N1} сек" -f ((Get-Date) - $t0).TotalSeconds)
            break
        }
    }
    if (((Get-Date) - $t0).TotalSeconds -gt 180) {
        Write-Host "Таймаут 180 сек"
        break
    }
    Start-Sleep -Milliseconds 300
}
Start-Sleep -Milliseconds 800
Write-Host "`n--- Вывод desktop (TIME-строки) ---"
Select-String -Path startup_out.txt, startup_err.txt -Pattern "TIME:" | ForEach-Object { $_.Line }
