# scripts/run_visits_test.ps1
# Скрипт для запуска теста Visits с сохранением результата в файл

param(
    [string]$OutputFile = "test_visits_result.txt"
)

# Получаем текущую дату и время
$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"

# Создаём файл с заголовком
"============================================================" | Out-File -FilePath $OutputFile -Encoding utf8
"FitNexus AI - Visits Module Test Results" | Out-File -FilePath $OutputFile -Encoding utf8 -Append
"Run at: $timestamp" | Out-File -FilePath $OutputFile -Encoding utf8 -Append
"============================================================" | Out-File -FilePath $OutputFile -Encoding utf8 -Append
"" | Out-File -FilePath $OutputFile -Encoding utf8 -Append

# Запускаем тест и сохраняем вывод
Write-Host "Running visits module test..." -ForegroundColor Yellow
Write-Host "Saving results to: $OutputFile" -ForegroundColor Cyan

# Отключаем SQL логи на время теста (временное изменение)
$env:SQLALCHEMY_ECHO = "false"

# Запускаем тест и захватываем вывод
python scripts/test_visits_module.py 2>&1 | Tee-Object -FilePath $OutputFile -Append

Write-Host ""
Write-Host "Test completed!" -ForegroundColor Green
Write-Host "Results saved to: $OutputFile" -ForegroundColor Green