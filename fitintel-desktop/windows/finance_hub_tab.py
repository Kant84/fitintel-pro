"""W5: хаб «Бухгалтерия» (ленивые подвкладки через HubTab)."""
from windows.hub_base import HubTab

_MOD2CLS = {
    "payments_tab": "PaymentsTab",
    "accounting_tab": "AccountingTab",
    "reports_tab": "ReportsTab",
    "documents_tab": "DocumentsTab",
    "tariffs_tab": "TariffsTab",
    "export_tab": "ExportTab",
    "payroll_tab": "PayrollTab",
}

# Суб-вкладки, требующие конкретного права: без права скрываем.
_PERM_REQUIRED = {
    "Документы": "documents.read",
    "Тарифы": "tariffs.read",
    "Зарплата": "users.read",
}


def FinanceHubTab(api, perms=None):
    import importlib

    def _build(name):
        def _f():
            mod = importlib.import_module(f"windows.{name}")
            return getattr(mod, _MOD2CLS[name])(api)
        return _f

    avail = None if perms is None else set(perms)
    specs = []
    for _t, _m in _ITEMS:
        need = _PERM_REQUIRED.get(_t)
        if avail is not None and need and need not in avail:
            continue
        specs.append((_t, _build(_m)))
    return HubTab(api, specs)


_ITEMS = [
    ("Платежи", "payments_tab"),
    ("Бухгалтерия", "accounting_tab"),
    ("Отчёты", "reports_tab"),
    ("Документы", "documents_tab"),
    ("Тарифы", "tariffs_tab"),
    ("Экспорт", "export_tab"),
    ("Зарплата", "payroll_tab"),
]
