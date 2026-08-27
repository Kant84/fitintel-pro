# 🔌 Настройка ITCService для интеграции с FitIntel Pro (E15-SKUD)

## 📋 Содержание
1. [Требования](#требования)
2. [Быстрая настройка](#быстрая-настройка)
3. [Ручная настройка реестра](#ручная-настройка-реестра)
4. [Параметры конфигурации](#параметры-конфигурации)
5. [Проверка связи](#проверка-связи)
6. [Типичные ошибки](#типичные-ошибки)
7. [Схема работы](#схема-работы)

---

## Требования

- **FitIntel Pro** запущен и доступен по сети
- **ITCService** версии 2.5+ (поддержка HTTP REST API)
- **PostgreSQL** FitIntel Pro доступна и содержит данные клиентов
- Сетевой доступ между сервером ITCService и сервером FitIntel Pro
- Порт **8001** открыт в файрволе

---

## Быстрая настройка

### Шаг 1: Определите IP сервера FitIntel Pro

```powershell
# На сервере FitIntel Pro выполните:
ipconfig
# Запишите IPv4-адрес (например, 192.168.1.50)
```

### Шаг 2: Отредактируйте файл реестра

Откройте файл `ITCService_CONFIG.reg` в блокноте и замените:
```
192.168.1.50 → ВАШ_IP_СЕРВЕРА
```

**Пример:**
```
"CheckAccessURL"="http://192.168.1.50:8001/api/v1/skud/checkaccess"
↓
"CheckAccessURL"="http://10.0.0.15:8001/api/v1/skud/checkaccess"
```

### Шаг 3: Импортируйте реестр

1. Дважды кликните по `ITCService_CONFIG.reg`
2. Нажмите **"Да"** → **"Да"** → **"OK"**
3. Перезапустите службу ITCService:

```powershell
# PowerShell (от имени администратора)
Restart-Service ITCService
# или
net stop ITCService && net start ITCService
```

### Шаг 4: Проверьте связь

```powershell
# Тест health check
curl -u itc:itc_secret_2026 http://ВАШ_IP:8001/api/v1/skud/health_check

# Ожидаемый ответ:
# {"status":"ok","service":"FitIntel-SKUD"}
```

---

## Ручная настройка реестра

Если предпочитаете ручную настройку, создайте ключи вручную:

```
HKEY_LOCAL_MACHINE\SOFTWARE\ITCService
```

| Параметр | Тип | Значение | Описание |
|----------|-----|----------|----------|
| `CheckAccessURL` | REG_SZ | `http://IP:8001/api/v1/skud/checkaccess` | Проверка доступа через турникет |
| `EventURL` | REG_SZ | `http://IP:8001/api/v1/skud/event` | Фиксация прохода |
| `HealthCheckURL` | REG_SZ | `http://IP:8001/api/v1/skud/health_check` | Проверка связи |
| `OlockCheckAccessURL` | REG_SZ | `http://IP:8001/api/v1/skud/olock_checkaccess` | Онлайн-замки (шкафчики) |
| `AquaCheckAccessURL` | REG_SZ | `http://IP:8001/api/v1/skud/aqua_checkaccess` | Аквапарк |
| `SolarCheckAccessURL` | REG_SZ | `http://IP:8001/api/v1/skud/solar/checkaccess` | Солярий |
| `BasicAuthUser` | REG_SZ | `itc` | Логин Basic Auth |
| `BasicAuthPass` | REG_SZ | `itc_secret_2026` | Пароль Basic Auth |
| `TimeoutMs` | REG_DWORD | `5000` | Таймаут запроса (мс) |
| `RetryCount` | REG_DWORD | `3` | Количество повторов |

---

## Параметры конфигурации

### CheckAccessURL

**Назначение:** Проверка доступа клиента перед открытием турникета.

**Формат запроса (ITCService → FitIntel):**
```json
{
  "device_id": "192.168.1.100",
  "client_card": "1D870731000001",
  "request_id": "uuid-запроса",
  "qr": null,
  "minutes": "0",
  "client_id": null
}
```

**Формат ответа (FitIntel → ITCService):**
```json
{
  "client_id": "1f31b312-c792-4cbe-a76b-b345f0d92479",
  "subscription_id": "6e3f6feb-8ab5-410b-a054-51f37ec27983",
  "text": "Проходите",
  "grant_access": 1,
  "text_full": "Доступ разрешен.",
  "withoutface": false
}
```

**Логика:**
- `grant_access: 1` → открыть турникет
- `grant_access: 0` → закрыть, показать `text`

---

### EventURL

**Назначение:** Фиксация физического прохода (вход/выход).

**Формат запроса:**
```json
{
  "device_id": "192.168.1.100",
  "client_card": "1D870731000001",
  "request_id": "uuid-запроса",
  "qr": null,
  "minutes": "0",
  "client_id": null
}
```

**Формат ответа:**
```json
{
  "request_id": "uuid-запроса",
  "success": true,
  "error": null
}
```

**Важно:** Запись визита появляется в таблице `visits` FitIntel Pro.

---

### OlockCheckAccessURL

**Назначение:** Проверка доступа к онлайн-замкам (шкафчики в раздевалках).

**Формат запроса:**
```json
{
  "card": "1D870731000001",
  "group": "man"
}
```

**Формат ответа:**
```json
{
  "success": true,
  "grant_access": true,
  "text_full": "Доступ есть",
  "allow_rent": true,
  "quantity": 3
}
```

---

### AquaCheckAccessURL

**Назначение:** Проверка доступа в аквапарк / на инфотерминал.

**Формат ответа:**
```json
{
  "Code": 201,
  "DataObj": {
    "FullName": "Сидоров Алексей",
    "TariffName": "Аквапарк",
    "Credit": 0,
    "Balance": 1000,
    "Limit": 5000,
    "TimeIn": "10:00",
    "TimeOut": "22:00",
    "TimeLeft": "12:00"
  }
}
```

---

### SolarCheckAccessURL

**Назначение:** Проверка доступа к солярию.

**Формат ответа:**
```json
{
  "minute_purchase": 15,
  "grant_access": 1,
  "text": "Проходите",
  "text_full": "Доступ разрешен. Осталось 15 минут.",
  "minute_price": 50,
  "credit_allow": true
}
```

---

## Проверка связи

### 1. Health Check

```bash
curl -u itc:itc_secret_2026 http://IP:8001/api/v1/skud/health_check
```

**Ожидаемый ответ:**
```json
{"status":"ok","service":"FitIntel-SKUD"}
```

### 2. Проверка карты

```bash
curl -u itc:itc_secret_2026 -X POST http://IP:8001/api/v1/skud/checkaccess   -H "Content-Type: application/json"   -d '{"device_id":"test","client_card":"1D870731000001","request_id":"test-001"}'
```

**Ожидаемый ответ (с абонементом):**
```json
{
  "client_id": "1f31b312-c792-4cbe-a76b-b345f0d92479",
  "subscription_id": "6e3f6feb-8ab5-410b-a054-51f37ec27983",
  "text": "Проходите",
  "grant_access": 1,
  "text_full": "Доступ разрешен.",
  "withoutface": false
}
```

### 3. Фиксация прохода

```bash
curl -u itc:itc_secret_2026 -X POST http://IP:8001/api/v1/skud/event   -H "Content-Type: application/json"   -d '{"device_id":"test","client_card":"1D870731000001","request_id":"test-002"}'
```

**Ожидаемый ответ:**
```json
{"request_id":"test-002","success":true,"error":null}
```

---

## Типичные ошибки

| Ошибка | Причина | Решение |
|--------|---------|---------|
| `401 Unauthorized` | Неверный Basic Auth | Проверьте логин/пароль в реестре |
| `404 Not Found` | Неверный URL | Проверьте IP и порт в реестре |
| `Internal Server Error` | Ошибка в FitIntel | Проверьте логи сервера |
| `Connection refused` | Сервер не запущен | Запустите FitIntel Pro |
| `Карта не найдена` | UID не в базе | Привяжите карту в FitIntel Pro |
| `Нет активного абонемента` | Абонемент просрочен | Продлите абонемент клиенту |
| `Timeout` | Медленная сеть | Увеличьте `TimeoutMs` в реестре |

---

## Схема работы

```
┌─────────────┐     checkaccess      ┌─────────────────┐
│  Терминал   │ ───────────────────→ │  FitIntel Pro   │
│   СКУД      │  (Basic Auth)        │   (порт 8001)   │
│  (ITC)      │ ←─────────────────── │                 │
└─────────────┘   grant_access: 1/0   └─────────────────┘
       │                                      │
       │ event (проход)                       │
       ↓                                      ↓
┌─────────────┐                        ┌─────────────┐
│  Таблица    │                        │  PostgreSQL │
│   visits    │ ←───────────────────── │   fitnexus  │
└─────────────┘                        └─────────────┘
```

### Последовательность операций

1. **Клиент подносит карту** к терминалу СКУД
2. **ITCService** отправляет `POST /skud/checkaccess`
3. **FitIntel Pro** проверяет:
   - Карта в базе?
   - Активный абонемент?
   - Не просрочен?
4. **FitIntel Pro** отвечает `grant_access: 1` (открыть) или `0` (закрыть)
5. **ITCService** открывает/закрывает турникет
6. **ITCService** отправляет `POST /skud/event` — фиксация прохода
7. **FitIntel Pro** записывает визит в таблицу `visits`

---

## 🔐 Безопасность

⚠️ **Важно:** Пароль `itc_secret_2026` — временный. Смените его:

1. Откройте `app/api/v1/skud_itconnect.py`
2. Найдите строку: `credentials.password != "itc_secret_2026"`
3. Замените на свой пароль
4. Обновите реестр ITCService
5. Перезапустите службы

---

## 📞 Поддержка

- **FitIntel Pro:** MAX Messenger / Telegram
- **ITCService:** Документация производителя
- **Логи:** `C:\ProgramData\ITCService\logs\`

---

*Версия инструкции: E15-SKUD v1.0*
*Дата: 2026-08-27*
