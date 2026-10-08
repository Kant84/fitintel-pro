"""W5: хаб «AI центр» (ленивые подвкладки через HubTab)."""
from windows.hub_base import HubTab

_MOD2CLS = {
    "ai_center_tab": "AICenterTab",
    "analytics_tab": "AnalyticsTab",
}

def AIHubTab(api):
    import importlib

    def _build(name):
        def _f():
            mod = importlib.import_module(f"windows.{name}")
            return getattr(mod, _MOD2CLS[name])(api)
        return _f

    specs = [(_t, _build(_m)) for _t, _m in _ITEMS]
    return HubTab(api, specs)

_ITEMS = [
    ("AI Центр", "ai_center_tab"),
    ("Аналитика", "analytics_tab"),
]