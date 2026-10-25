"""W5: хаб «Настройки» (ленивые подвкладки через HubTab)."""
from windows.hub_base import HubTab

_MOD2CLS = {
    "services_settings_tab": ("_Get", "Сервисы"),
    "setup_tab": "SetupTab",
    "ui_config_tab": "UiConfigTab",
    "license_tab": "LicenseTab",
    "devices_tab": "DevicesTab",
    "club_params_tab": "ClubParamsTab",
    "roles_tab": "RolesTab",
    "integrations_tab": "IntegrationsTab",
    "service_accounts_tab": "ServiceAccountsTab",
    "access_audit_tab": "AccessAuditTab",
    "commerce_tab": "CommerceTab",
    "bank_settings_tab": "BankSettingsTab",
    "bank_settings_tab": "BankSettingsTab",
}

def SettingsHubTab(api, main_window=None):
    from windows.settings_tab import SettingsTab

    def _build(name):
        def _f():
            import importlib
            mod = importlib.import_module(f"windows.{name}")
            return getattr(mod, _MOD2CLS[name])(api)
        return _f

    specs = [("Настройки", lambda: SettingsTab(api, main_window))]
    bank_specs = []
    try:
        visible = {item.get("code") for item in api.get_ui_my().get("screens", [])}
        if "banks" in visible:
            bank_specs = [("Банки", _build("bank_settings_tab"))]
    except Exception:
        bank_specs = []

    bank_specs = []
    try:
        visible = {item.get("code") for item in api.get_ui_my().get("screens", [])}
        if "banks" in visible:
            bank_specs = [("Банки", _build("bank_settings_tab"))]
    except Exception:
        bank_specs = []

    for _title, _mod in [("Мастер установки", "setup_tab"),
                           ("Экраны ролей", "ui_config_tab"),
                           ("Лицензия", "license_tab"),
                           ("Устройства", "devices_tab"),
                           ("Параметры клуба", "club_params_tab"),
                           ("Роли и права", "roles_tab"),
                           ("Интеграции", "integrations_tab"),
                           ("Коммерция", "commerce_tab"),
                           ("Service-аккаунты", "service_accounts_tab"),
                           ("Аудит доступа (152-ФЗ)", "access_audit_tab")]:
        specs.append((_title, _build(_mod)))
    specs[1:1] = bank_specs
    specs[1:1] = bank_specs
    return HubTab(api, specs, main_window)