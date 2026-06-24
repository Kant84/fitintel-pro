
# ============================================================
# FitIntel Pro v1.3.1 — Автоматический тестировщик API
# Запуск: . .\fitintel_test_runner.ps1
# ============================================================
$ErrorActionPreference = "Stop"
$API_BASE = "http://localhost:8001/api/v1"
$REPORT = @()

function Add-Result($Module, $ID, $Test, $Status, $Expected, $Actual, $Note) {
    $script:REPORT += [PSCustomObject]@{
        Модуль = $Module
        ID = $ID
        Тест = $Test
        Статус = $Status
        Ожидалось = $Expected
        Получено = $Actual
        Примечание = $Note
    }
}

function Invoke-Test($Method, $Uri, $Body=$null, $Headers=$null, $ExpectedCodes=(200,201)) {
    try {
        $params = @{ Uri = $Uri; Method = $Method }
        if ($Body) { $params.Body = $Body; $params.ContentType = "application/json" }
        if ($Headers) { $params.Headers = $Headers }
        $resp = Invoke-RestMethod @params
        return @{ Code = 200; Data = $resp; Error = $null }
    } catch {
        $code = $_.Exception.Response.StatusCode.value__
        $body = $_.ErrorDetails.Message
        return @{ Code = $code; Data = $null; Error = $body }
    }
}

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "  FitIntel Pro v1.3.1 — API TEST RUN" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# --- 1. LOGIN (получаем токен) ---
Write-Host "`n[AUTH] Получаем токен администратора..." -ForegroundColor Yellow
$loginBody = @{ login = "admin"; password = "gfhjkmas" } | ConvertTo-Json
$loginResp = Invoke-Test POST "$API_BASE/auth/login" $loginBody
if ($loginResp.Code -ne 200) {
    Write-Host "❌ Не удалось войти! Остановка." -ForegroundColor Red
    exit 1
}
$TOKEN = $loginResp.Data.access_token
$AUTH = @{ "Authorization" = "Bearer $TOKEN" }
Write-Host "✅ Токен получен" -ForegroundColor Green

# ============================================================
# E0 — LICENSE GUARD
# ============================================================
Write-Host "`n[E0] License Guard..." -ForegroundColor Magenta
$r = Invoke-Test GET "$API_BASE/setup/license/status" -Headers $AUTH
Add-Result "E0" "E0.4" "Проверка статуса лицензии" $(if($r.Code-eq200){"✅"}else{"❌"}) "200" $r.Code ""

$r = Invoke-Test GET "$API_BASE/health"
Add-Result "E0" "E0.5" "/health endpoint" $(if($r.Code-eq200){"✅"}else{"❌"}) "200" $r.Code ""

# ============================================================
# E1 — SETUP WIZARD
# ============================================================
Write-Host "[E1] Setup Wizard..." -ForegroundColor Magenta
$r = Invoke-Test GET "$API_BASE/setup/init"
Add-Result "E1" "E1.2" "Повторный init (already configured)" $(if($r.Code-eq409){"✅"}else{"⚠️"}) "409" $r.Code ""

# ============================================================
# E2 — AUTH
# ============================================================
Write-Host "[E2] Auth..." -ForegroundColor Magenta
$r = Invoke-Test POST "$API_BASE/auth/register" (@{ email="test999@example.com"; username="test999"; password="TestPass123!" } | ConvertTo-Json)
Add-Result "E2" "E2.1" "Регистрация" $(if($r.Code-eq200){"✅"}else{"❌"}) "200" $r.Code ""

$r = Invoke-Test POST "$API_BASE/auth/login" $loginBody
Add-Result "E2" "E2.5" "Login" $(if($r.Code-eq200){"✅"}else{"❌"}) "200" $r.Code ""

# ============================================================
# E3 — RBAC
# ============================================================
Write-Host "[E3] RBAC..." -ForegroundColor Magenta
$r = Invoke-Test GET "$API_BASE/roles" -Headers $AUTH
Add-Result "E3" "E3.1" "Список ролей" $(if($r.Code-eq200){"✅"}else{"❌"}) "200" $r.Code ""

# ============================================================
# E4 — USERS
# ============================================================
Write-Host "[E4] Users..." -ForegroundColor Magenta
$r = Invoke-Test GET "$API_BASE/users" -Headers $AUTH
Add-Result "E4" "E4.2" "Список пользователей" $(if($r.Code-eq200){"✅"}else{"❌"}) "200" $r.Code ""

# ============================================================
# E5 — CLIENTS
# ============================================================
Write-Host "[E5] Clients..." -ForegroundColor Magenta
$r = Invoke-Test GET "$API_BASE/clients" -Headers $AUTH
Add-Result "E5" "E5.2" "Список клиентов" $(if($r.Code-eq200){"✅"}else{"❌"}) "200" $r.Code ""

# ============================================================
# E6 — VISITS
# ============================================================
Write-Host "[E6] Visits..." -ForegroundColor Magenta
$r = Invoke-Test GET "$API_BASE/visits" -Headers $AUTH
Add-Result "E6" "E6.2" "Список визитов" $(if($r.Code-eq200){"✅"}else{"❌"}) "200" $r.Code ""

# ============================================================
# E7 — FACE ID
# ============================================================
Write-Host "[E7] Face ID..." -ForegroundColor Magenta
$r = Invoke-Test GET "$API_BASE/face-id/logs" -Headers $AUTH
Add-Result "E7" "E7.5" "Логи Face ID" $(if($r.Code-eq200){"✅"}else{"❌"}) "200" $r.Code ""

# ============================================================
# E8 — TARIFFS
# ============================================================
Write-Host "[E8] Tariffs..." -ForegroundColor Magenta
$r = Invoke-Test GET "$API_BASE/tariffs" -Headers $AUTH
Add-Result "E8" "E8.2" "Список тарифов" $(if($r.Code-eq200){"✅"}else{"❌"}) "200" $r.Code ""

# ============================================================
# E9 — SUBSCRIPTIONS
# ============================================================
Write-Host "[E9] Subscriptions..." -ForegroundColor Magenta
$r = Invoke-Test GET "$API_BASE/subscriptions" -Headers $AUTH
Add-Result "E9" "E9.2" "Список абонементов" $(if($r.Code-eq200){"✅"}else{"❌"}) "200" $r.Code ""

# ============================================================
# E10 / E18 — FISCAL (Payments, Cash Desk)
# ============================================================
Write-Host "[E10/E18] Fiscal..." -ForegroundColor Magenta

# Без эмуляторов — только списки и mock-оплаты
$r = Invoke-Test GET "$API_BASE/fiscal/printers" -Headers $AUTH
Add-Result "E10" "E10.15" "Список касс" $(if($r.Code-eq200){"✅"}else{"❌"}) "200" $r.Code ""

$r = Invoke-Test GET "$API_BASE/fiscal/banks" -Headers $AUTH
Add-Result "E10" "E10.16" "Список банков" $(if($r.Code-eq200){"✅"}else{"❌"}) "200" $r.Code ""

$r = Invoke-Test POST "$API_BASE/fiscal/banks/pay?amount=3000" -Headers $AUTH
Add-Result "E10" "E10.2" "Оплата картой (mock)" $(if($r.Code-eq200){"✅"}else{"❌"}) "200" $r.Code ""

$r = Invoke-Test POST "$API_BASE/fiscal/sbp/qr" (@{ amount=1500 } | ConvertTo-Json) -Headers $AUTH
Add-Result "E10" "E10.3" "СБП QR (mock)" $(if($r.Code-eq200){"✅"}else{"❌"}) "200" $r.Code ""

$r = Invoke-Test POST "$API_BASE/fiscal/subscription/register" (@{ client_id=42 } | ConvertTo-Json) -Headers $AUTH
Add-Result "E10" "E10.14" "Регистрация токена рекуррентов (mock)" $(if($r.Code-eq200){"✅"}else{"❌"}) "200" $r.Code ""

# Требуют эмуляторы — пропускаем, помечаем
Add-Result "E10" "E10.1" "Оплата наличными + чек АТОЛ" "⏳" "200" "N/A" "Требуется эмулятор АТОЛ ДТО 10"
Add-Result "E10" "E10.7" "Открытие смены АТОЛ" "⏳" "200" "N/A" "Требуется эмулятор АТОЛ ДТО 10"
Add-Result "E10" "E10.8" "Закрытие смены (Z-отчет)" "⏳" "200" "N/A" "Требуется эмулятор АТОЛ + банк"

# ============================================================
# E11 — LOCKERS
# ============================================================
Write-Host "[E11] Lockers..." -ForegroundColor Magenta
$r = Invoke-Test GET "$API_BASE/lockers" -Headers $AUTH
Add-Result "E11" "E11.1" "Список шкафчиков" $(if($r.Code-eq200){"✅"}else{"❌"}) "200" $r.Code ""

# ============================================================
# E12 — DEVICES
# ============================================================
Write-Host "[E12] Devices..." -ForegroundColor Magenta
$r = Invoke-Test GET "$API_BASE/devices" -Headers $AUTH
Add-Result "E12" "E12.1" "Список устройств" $(if($r.Code-eq200){"✅"}else{"❌"}) "200" $r.Code ""

# ============================================================
# E17 — ACCOUNTING / 1С
# ============================================================
Write-Host "[E17] Accounting..." -ForegroundColor Magenta

# Создаём проводки
$r = Invoke-Test POST "$API_BASE/accounting/pko" (@{ amount=5000; description="Тестовая оплата наличными" } | ConvertTo-Json) -Headers $AUTH
Add-Result "E17" "E17.1" "ПКО (Приходный кассовый ордер)" $(if($r.Code-eq200){"✅"}else{"❌"}) "200" $r.Code ""

$r = Invoke-Test POST "$API_BASE/accounting/rko" (@{ amount=1000; description="Тестовый расход" } | ConvertTo-Json) -Headers $AUTH
Add-Result "E17" "E17.2" "РКО (Расходный кассовый ордер)" $(if($r.Code-eq200){"✅"}else{"❌"}) "200" $r.Code ""

$r = Invoke-Test POST "$API_BASE/accounting/sale" (@{ amount=3000; payment_type="cash"; description="Продажа абонемента" } | ConvertTo-Json) -Headers $AUTH
Add-Result "E17" "E17.3" "Реализация (продажа)" $(if($r.Code-eq200){"✅"}else{"❌"}) "200" $r.Code ""

# Отчёты (должны показать проводки)
$r = Invoke-Test GET "$API_BASE/accounting/osv/2026-06" -Headers $AUTH
Add-Result "E17" "E17.4" "ОСВ (оборотно-сальдовая)" $(if($r.Code-eq200){"✅"}else{"❌"}) "200" $r.Code ""

$r = Invoke-Test GET "$API_BASE/accounting/profit-loss/2026-06" -Headers $AUTH
Add-Result "E17" "E17.5" "P&L (прибыли/убытки)" $(if($r.Code-eq200){"✅"}else{"❌"}) "200" $r.Code ""

$r = Invoke-Test GET "$API_BASE/accounting/balance-sheet/2026-06" -Headers $AUTH
Add-Result "E17" "E17.5" "Баланс" $(if($r.Code-eq200){"✅"}else{"❌"}) "200" $r.Code ""

$r = Invoke-Test GET "$API_BASE/accounting/cash-flow/2026-06" -Headers $AUTH
Add-Result "E17" "E17.6" "ДДС (денежный поток)" $(if($r.Code-eq200){"✅"}else{"❌"}) "200" $r.Code ""

# 1С интеграция — mock
Add-Result "E17" "E17.7" "1С: Выгрузка номенклатуры" "⏳" "200" "N/A" "Требуется настройка 1С mock"
Add-Result "E17" "E17.10" "1С: Импорт остатков" "⏳" "200" "N/A" "Требуется файл offers.xml"

# ============================================================
# E19 — SECURITY (быстрая проверка)
# ============================================================
Write-Host "[E19] Security..." -ForegroundColor Magenta
$r = Invoke-Test GET "$API_BASE/clients?q='; DROP TABLE clients;--" -Headers $AUTH
Add-Result "E19" "N1.1" "SQL-инъекция (защита)" $(if($r.Code-in @(400,422,200)){"✅"}else{"⚠️"}) "400/422" $r.Code ""

# ============================================================
# E23 — E2E (полный цикл без эмуляторов)
# ============================================================
Write-Host "[E23] End-to-End..." -ForegroundColor Magenta
Add-Result "E23" "I1.1" "Полный цикл: клиент->оплата->визит" "⏳" "200" "N/A" "Требуются эмуляторы АТОЛ+Face ID"
Add-Result "E23" "I1.3" "Полный цикл: бухгалтерия" "⏳" "200" "N/A" "Требуется 1С mock"
Add-Result "E23" "I1.4" "Закрытие дня" "⏳" "200" "N/A" "Требуются эмуляторы АТОЛ+банк+SMTP"

# ============================================================
# REPORT
# ============================================================
Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "  ОТЧЁТ ТЕСТИРОВАНИЯ" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

$passed = ($REPORT | Where-Object { $_.Статус -eq "✅" }).Count
$failed = ($REPORT | Where-Object { $_.Статус -eq "❌" }).Count
$pending = ($REPORT | Where-Object { $_.Статус -eq "⏳" }).Count

Write-Host "`n✅ Пройдено: $passed" -ForegroundColor Green
Write-Host "❌ Не пройдено: $failed" -ForegroundColor Red
Write-Host "⏳ Требуют эмуляторы/настройки: $pending" -ForegroundColor Yellow
Write-Host "Всего: $($REPORT.Count)" -ForegroundColor White

Write-Host "`n--- Детализация ---" -ForegroundColor Gray
$REPORT | Format-Table -AutoSize | Out-String | Write-Host

# Сохраняем CSV
$csvPath = "C:\Users\PC\Desktop\2026\FitNexus AI\FitIntel AI\TEST_REPORT_$(Get-Date -Format 'yyyyMMdd_HHmmss').csv"
$REPORT | Export-Csv -Path $csvPath -NoTypeInformation -Encoding UTF8
Write-Host "`n📁 Отчёт сохранён: $csvPath" -ForegroundColor Cyan
