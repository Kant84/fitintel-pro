# FitIntel Pro Desktop

Десктопное приложение для управления фитнес-клубом.

## Требования
- Windows 10/11
- Python 3.11+
- Запущенный бэкенд FitIntel Pro (localhost:8001)

## Установка

```bash
# 1. Создайте виртуальное окружение
python -m venv .venv-desktop
.venv-desktop\Scripts\activate

# 2. Установите зависимости
pip install -r requirements-desktop.txt

# 3. Запустите
python main.py
```

## Сборка .exe

```bash
pip install pyinstaller
python build.py
```

Готовый файл: `dist/FitIntelPro.exe`

## Возможности
- 🔐 Авторизация через API
- 👥 Управление клиентами
- 📋 Абонементы и заморозки
- 🚪 Журнал входов/выходов
- 🎭 Face ID (симуляция + интеграция с API)
- 🔐 Проверка лицензии
- ⚙️ Настройки подключения

## Архитектура
```
desktop/
├── main.py              # Точка входа
├── api/
│   ├── __init__.py
│   └── client.py        # HTTP клиент для FastAPI
├── windows/
│   ├── __init__.py
│   ├── login_window.py  # Окно авторизации
│   ├── main_window.py   # Главное окно (вкладки)
│   ├── clients_tab.py
│   ├── subscriptions_tab.py
│   ├── visits_tab.py
│   ├── face_id_tab.py
│   ├── license_tab.py
│   └── settings_tab.py
├── requirements-desktop.txt
└── build.py             # Скрипт сборки .exe
```

## Лицензия
© 2026 ИП Санакин А.В. | FitIntel Pro v1.3.0
