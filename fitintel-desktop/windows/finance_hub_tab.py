"""W5: хаб «Бухгалтерия» (ленивые подвкладки через HubTab)."""
from windows.hub_base import HubTab

_MOD2CLS = {
    "payments_tab": "PaymentsTab",
    "accounting_tab": "AccountingTab",
    "reports_tab": "ReportsTab",
    "documents_tab": "DocumentsTab",
    "tariffs_tab": "TariffsTab",
    "export_tab": "ExportTab",
}

def FinanceHubTab(api):
    import importlib

    def _build(name):
        def _f():
            mod = importlib.import_module(f"windows.{name}")
            return getattr(mod, _MOD2CLS[name])(api)
        return _f

    specs = [(_t, _build(_m)) for _t, _m in _ITEMS]
    return HubTab(api, specs)

_ITEMS = [
    ("Платежи", "payments_tab"),
    ("Бухгалтерия", "accounting_tab"),
    ("Отчёты", "reports_tab"),
    ("Документы", "documents_tab"),
    ("Тарифы", "tariffs_tab"),
    ("Экспорт", "export_tab"),
]