import io

path = "windows/main_window.py"
with io.open(path, encoding="utf-8") as f:
    src = f.read()

src = src.replace(
    "from windows.ui_config_tab import UiConfigTab",
    "from windows.ui_config_tab import UiConfigTab\n"
    "from windows.schedule_tab import ScheduleTab\n"
    "from windows.reports_tab import ReportsTab\n"
    "from windows.documents_tab import DocumentsTab\n"
    "from windows.roles_tab import RolesTab\n"
    "from windows.setup_tab import SetupTab\n"
    "from windows.tariffs_tab import TariffsTab")

src = src.replace(
    '    "settings":      ("Настройки", SettingsTab),\n}',
    '    "schedule":      ("Расписание", ScheduleTab),\n'
    '    "reports":       ("Отчёты", ReportsTab),\n'
    '    "documents":     ("Документы", DocumentsTab),\n'
    '    "roles":         ("Роли", RolesTab),\n'
    '    "tariffs":       ("Тарифы", TariffsTab),\n'
    '    "setup":         ("Установка", SetupTab),\n'
    '    "settings":      ("Настройки", SettingsTab),\n}')

src = src.replace(
    'DEFAULT_TABS = ["dashboard", "clients", "subscriptions", "visits", "payments",\n'
    '                "users", "devices", "face_id", "license", "ui_config", "settings"]',
    'DEFAULT_TABS = ["dashboard", "clients", "subscriptions", "tariffs", "visits",\n'
    '                "schedule", "payments", "reports", "documents", "users", "roles",\n'
    '                "devices", "face_id", "license", "ui_config", "setup", "settings"]')

with io.open(path, "w", encoding="utf-8") as f:
    f.write(src)
print("main_window PATCHED")
