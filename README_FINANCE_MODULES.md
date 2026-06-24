# Универсальные финансовые модули FitIntel Pro

## Куда копировать файлы

```
fitintel-pro/
├── app/
│   ├── services/
│   │   ├── fiscal/
│   │   │   ├── __init__.py
│   │   │   └── universal_fiscal.py      ← Кассы: АТОЛ, Штрих-М, Эвотор, Меркурий
│   │   ├── bank/
│   │   │   ├── __init__.py
│   │   │   └── universal_bank.py        ← Банки: Сбер, Тинькофф, Райффайзен
│   │   ├── accounting/
│   │   │   ├── __init__.py
│   │   │   ├── internal_accounting.py   ← Внутренняя бухгалтерия (аналог 1С)
│   │   │   └── onec_integration.py      ← Интеграция с 1С:Предприятие
│   │   └── sbp_service.py               ← СБП + рекурренты (уже есть в проекте)
│   └── api/v1/endpoints/
│       ├── fiscal.py                    ← API кассы / банки / СБП
│       └── accounting.py                ← API бухгалтерия / 1С
├── desktop/
│   └── fiscal_settings_dialog.py        ← PyQt окно настроек
└── ...
```

## Подключение роутов в FastAPI

В `app/api/v1/router.py` добавьте:

```python
from app.api.v1.endpoints.fiscal import fiscal_router
from app.api.v1.endpoints.accounting import accounting_router

router.include_router(fiscal_router)
router.include_router(accounting_router)
```

## Как это работает

### Кассы (universal_fiscal.py)
- `FiscalManager` хранит конфиг и выбирает активный адаптер (`atol`, `shtrih`, `evotor`, `mercury`).
- Все адаптеры реализуют `BaseFiscalPrinter` — одинаковые методы: `open_shift`, `print_sale_check`, `print_return_check`, `close_shift`, `cancel_last_document`, `get_status`, `send_correction`.
- Добавить новую кассу = написать класс от `BaseFiscalPrinter` + зарегистрировать в `FiscalManager._registry`.

### Банки (universal_bank.py)
- `BankManager` аналогично переключает между `sber`, `tinkoff`, `raiff`.
- Все адаптеры реализуют `BaseBankTerminal` — методы: `pay`, `cancel_last`, `settlement`, `get_status`, `preauth`, `complete_preauth`.
- Сбер поддерживает 3 режима: `mock`, `json` (REST API эквайринга), `dll` (ctypes + sbrf.dll).
- Тинькофф реализует настоящий Token (SHA-256) для API.

### Внутренняя бухгалтерия (internal_accounting.py)
- Полноценный аналог 1С для клубов, которые не хотят покупать 1С.
- План счетов: 50, 51, 57, 60, 62, 66, 90, 91, 99.
- Двойная бухгалтерская запись (проводки Дт/Кт).
- Документы: ПКО, РКО, Реализация, Поступление, ручная корректировка.
- Отчеты: ОСВ, оборотка по счету, P&L (прибыли/убытки), баланс, ДДС, акт сверки.

### Интеграция с 1С (onec_integration.py)
- Режимы: `file` (CommerceML 2.0 через XML), `http` (OData / Web-сервисы), `mock`.
- Выгрузка: номенклатура, контрагенты, документы (реализация, поступление, ПКО, РКО).
- Импорт: остатки и цены (offers.xml), заказы из 1С.
- Кодировка выгрузки: `windows-1251` (стандарт 1С).

### PyQt окно (fiscal_settings_dialog.py)
- 4 вкладки: Кассы, Банки, СБП, Бухгалтерия/1С.
- Выбор активного устройства, ввод настроек, тест соединения.
- Работает с бэкендом по API (`localhost:8001`).

## Тестовые эндпоинты (после запуска uvicorn)

```bash
# Кассы
curl http://localhost:8001/api/v1/fiscal/printers
curl -X POST http://localhost:8001/api/v1/fiscal/printers/open-shift
curl -X POST http://localhost:8001/api/v1/fiscal/printers/sale-check   -H "Content-Type: application/json"   -d '{"items":[{"name":"Абонемент","price":3000,"quantity":1}],"payment_type":"electronic","slip":"Тест"}'

# Банки
curl http://localhost:8001/api/v1/fiscal/banks
curl -X POST "http://localhost:8001/api/v1/fiscal/banks/pay?amount=3000"

# СБП
curl -X POST http://localhost:8001/api/v1/fiscal/sbp/qr   -H "Content-Type: application/json"   -d '{"amount":1500}'

# Бухгалтерия
curl -X POST http://localhost:8001/api/v1/accounting/pko   -H "Content-Type: application/json"   -d '{"amount":5000,"description":"Оплата наличными"}'
curl http://localhost:8001/api/v1/accounting/osv/2026-06
curl http://localhost:8001/api/v1/accounting/profit-loss/2026-06
```
