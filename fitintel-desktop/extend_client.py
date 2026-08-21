import io

path = "api/client.py"
with io.open(path, encoding="utf-8") as f:
    src = f.read()

# расширяем ключи нормализации списков
src = src.replace(
    '"subscriptions", "logs", "records"):',
    '"subscriptions", "logs", "records", "entries", "users",\n                      "devices", "drivers"):')

addition = '''
    # --- Dashboard / AI Analytics ---
    def get_churn(self) -> Dict[str, Any]:
        resp = self.session.get(self._url("/analytics/ai/churn"))
        resp.raise_for_status()
        return resp.json()

    def get_risk_segments(self) -> Dict[str, Any]:
        resp = self.session.get(self._url("/analytics/ai/risk-segments"))
        resp.raise_for_status()
        return resp.json()

    # --- Users ---
    def get_users(self) -> List[Dict[str, Any]]:
        resp = self.session.get(self._url("/users/"))
        resp.raise_for_status()
        return self._as_list(resp.json())

    # --- Devices (DAL) ---
    def get_devices(self) -> List[Dict[str, Any]]:
        resp = self.session.get(self._url("/dal/devices"))
        resp.raise_for_status()
        return self._as_list(resp.json())

    def get_drivers(self) -> List[Dict[str, Any]]:
        resp = self.session.get(self._url("/dal/drivers"))
        resp.raise_for_status()
        return self._as_list(resp.json())

    # --- Payments / Accounting ---
    def get_accounting_entries(self) -> List[Dict[str, Any]]:
        resp = self.session.get(self._url("/accounting/entries"))
        resp.raise_for_status()
        return self._as_list(resp.json())

    def get_sales_report(self) -> Dict[str, Any]:
        resp = self.session.get(self._url("/sales/report"))
        resp.raise_for_status()
        return resp.json()

    # --- UI-Config (E51) ---
    def get_ui_my(self) -> Dict[str, Any]:
        resp = self.session.get(self._url("/ui-config/my"))
        resp.raise_for_status()
        return resp.json()

    def get_ui_screens(self) -> List[Dict[str, Any]]:
        resp = self.session.get(self._url("/ui-config/screens"))
        resp.raise_for_status()
        return resp.json().get("screens", [])

    def get_ui_roles(self) -> Dict[str, Any]:
        resp = self.session.get(self._url("/ui-config/roles"))
        resp.raise_for_status()
        return resp.json()

    def set_ui_role_screens(self, role: str, screens: List[str]) -> Dict[str, Any]:
        resp = self.session.put(self._url(f"/ui-config/roles/{role}/screens"),
                                json={"screens": screens})
        resp.raise_for_status()
        return resp.json()

    def reset_ui_role(self, role: str) -> Dict[str, Any]:
        resp = self.session.post(self._url(f"/ui-config/roles/{role}/reset"))
        resp.raise_for_status()
        return resp.json()
'''
src = src.rstrip() + "\n" + addition
with io.open(path, "w", encoding="utf-8") as f:
    f.write(src)
print("client.py extended")
