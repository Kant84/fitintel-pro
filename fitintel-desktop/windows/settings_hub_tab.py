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
    "commerce_tab": "CommerceTab",
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
    for _title, _mod in [("Мастер установки", "setup_tab"),
                           ("Экраны ролей", "ui_config_tab"),
                           ("Лицензия", "license_tab"),
                           ("Устройства", "devices_tab"),
                           ("Параметры клуба", "club_params_tab"),
                           ("Роли и права", "roles_tab"),
                           ("Интеграции", "integrations_tab"),
                           ("Коммерция", "commerce_tab")]:
        specs.append((_title, _build(_mod)))
    return HubTab(api, specs, main_window)