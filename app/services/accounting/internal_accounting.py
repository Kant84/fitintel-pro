"""
Путь в проекте: app/services/accounting/internal_accounting.py
Внутренний аналог 1С для фитнес-клубов, которые НЕ используют 1С.
Реализует:
- Упрощенный план счетов (активы, пассивы, доходы, расходы)
- Двойная бухгалтерская запись (проводки Дт/Кт)
- Регистры остатков и оборотов
- Основные документы: ПКО, РКО, Реализация, Поступление, Акт сверки
- Отчеты: ОСВ (оборотно-сальдовая ведомость), оборотка по счету, баланс
- Контрагенты, Номенклатура, Статьи ДДС
"""
import sqlite3
import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from decimal import Decimal, ROUND_HALF_UP


class InternalAccounting:
    """
    Упрощенная бухгалтерия внутри FitIntel Pro.
    План счетов (упрощенный, аналог 1С):
    50   - Касса (деньги в кассе клуба)
    51   - Расчетные счета (банк)
    57   - Переводы в пути (эквайринг, СБП)
    62   - Расчеты с покупателями (клиенты, долги)
    60   - Расчеты с поставщиками
    66   - Кредиты и займы
    90.1 - Выручка (доходы от абонементов)
    90.2 - Себестоимость продаж
    90.3 - НДС (если применимо)
    91.1 - Прочие доходы
    91.2 - Прочие расходы (аренда, зарплата, коммуналка)
    99   - Прибыли и убытки
    """

    def __init__(self, db_path: str = "fitintel_accounting.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()

            # План счетов
            c.execute("""CREATE TABLE IF NOT EXISTS accounts (
                code TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                type TEXT NOT NULL,  -- active, passive, active_passive, income, expense
                parent_code TEXT,
                is_active INTEGER DEFAULT 1
            )""")

            # Журнал проводок (двойная запись)
            c.execute("""CREATE TABLE IF NOT EXISTS entries (
                id TEXT PRIMARY KEY,
                date TEXT NOT NULL,
                doc_type TEXT NOT NULL,  -- PKO, RKO, SALE, PURCHASE, CORRECTION, MANUAL
                doc_number TEXT NOT NULL,
                debit TEXT NOT NULL,
                credit TEXT NOT NULL,
                amount REAL NOT NULL,
                description TEXT,
                contragent_id TEXT,
                item_id TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )""")

            # Контрагенты (клиенты + поставщики)
            c.execute("""CREATE TABLE IF NOT EXISTS contragents (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                full_name TEXT,
                inn TEXT,
                kpp TEXT,
                type TEXT,  -- client, supplier, employee, bank
                phone TEXT,
                email TEXT,
                balance REAL DEFAULT 0  -- 62 счет: + нам должны, - мы должны
            )""")

            # Номенклатура (услуги, товары)
            c.execute("""CREATE TABLE IF NOT EXISTS items (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                type TEXT,  -- service, goods, subscription
                price REAL DEFAULT 0,
                cost_price REAL DEFAULT 0,
                unit TEXT DEFAULT 'шт',
                vat_rate REAL DEFAULT 0
            )""")

            # Сальдо по счетам (остатки на начало периода)
            c.execute("""CREATE TABLE IF NOT EXISTS balances (
                account_code TEXT NOT NULL,
                period TEXT NOT NULL,  -- YYYY-MM
                start_debit REAL DEFAULT 0,
                start_credit REAL DEFAULT 0,
                end_debit REAL DEFAULT 0,
                end_credit REAL DEFAULT 0,
                PRIMARY KEY (account_code, period)
            )""")

            conn.commit()

        self._seed_accounts()

    def _seed_accounts(self):
        """Заполняет план счетов, если пусто."""
        accounts = [
            ("50", "Касса", "active", None),
            ("51", "Расчетные счета", "active", None),
            ("57.01", "Эквайринг (в пути)", "active", "57"),
            ("57.02", "СБП (в пути)", "active", "57"),
            ("60", "Расчеты с поставщиками", "passive", None),
            ("62", "Расчеты с покупателями", "active_passive", None),
            ("66", "Кредиты и займы", "passive", None),
            ("90.1", "Выручка", "income", "90"),
            ("90.2", "Себестоимость", "expense", "90"),
            ("90.3", "НДС", "expense", "90"),
            ("91.1", "Прочие доходы", "income", "91"),
            ("91.2", "Прочие расходы", "expense", "91"),
            ("99", "Прибыли и убытки", "active_passive", None),
        ]
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.executemany("INSERT OR IGNORE INTO accounts (code, name, type, parent_code) VALUES (?,?,?,?)", accounts)
            conn.commit()

    # =====================================================================
    # ДОКУМЕНТЫ / ПРОВОДКИ
    # =====================================================================
    def create_pko(self, amount: float, contragent_id: Optional[str] = None,
                   description: str = "", doc_number: Optional[str] = None) -> str:
        """ПКО - Приходный кассовый ордер (деньги в кассу)."""
        doc_num = doc_number or f"ПКО-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        entry_id = str(uuid.uuid4())
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute("""INSERT INTO entries (id, date, doc_type, doc_number, debit, credit, amount, description, contragent_id)
                VALUES (?, ?, 'PKO', ?, '50', ?, ?, ?, ?)""",
                (entry_id, datetime.now().isoformat(), doc_num,
                 '62' if contragent_id else '90.1', amount, description, contragent_id))
            conn.commit()
        return entry_id

    def create_rko(self, amount: float, expense_account: str = "91.2",
                   description: str = "", doc_number: Optional[str] = None) -> str:
        """РКО - Расходный кассовый ордер (деньги из кассы)."""
        doc_num = doc_number or f"РКО-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        entry_id = str(uuid.uuid4())
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute("""INSERT INTO entries (id, date, doc_type, doc_number, debit, credit, amount, description)
                VALUES (?, ?, 'RKO', ?, ?, '50', ?, ?)""",
                (entry_id, datetime.now().isoformat(), doc_num, expense_account, amount, description))
            conn.commit()
        return entry_id

    def create_sale(self, amount: float, contragent_id: Optional[str] = None,
                    item_id: Optional[str] = None, description: str = "",
                    doc_number: Optional[str] = None, payment_type: str = "cash") -> str:
        """
        Реализация услуги (абонемента).
        Для безнала: Дт 51 (или 57) - Кт 90.1
        Для наличных: Дт 50 - Кт 90.1
        Для предоплаты: Дт 62 - Кт 90.1 (если долг)
        """
        doc_num = doc_number or f"РЕАЛ-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        date = datetime.now().isoformat()

        debit_acc = {"cash": "50", "bank": "51", "sbp": "57.02", "card": "57.01", "debt": "62"}.get(payment_type, "50")

        entry_id = str(uuid.uuid4())
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute("""INSERT INTO entries (id, date, doc_type, doc_number, debit, credit, amount, description, contragent_id, item_id)
                VALUES (?, ?, 'SALE', ?, ?, '90.1', ?, ?, ?, ?)""",
                (entry_id, date, doc_num, debit_acc, amount, description, contragent_id, item_id))

            # Себестоимость (упрощенно: 0 для услуг, или из items.cost_price)
            if item_id:
                c.execute("SELECT cost_price FROM items WHERE id=?", (item_id,))
                row = c.fetchone()
                cost = row[0] if row and row[0] else 0
                if cost > 0:
                    cost_id = str(uuid.uuid4())
                    c.execute("""INSERT INTO entries (id, date, doc_type, doc_number, debit, credit, amount, description, item_id)
                        VALUES (?, ?, 'SALE_COST', ?, '90.2', ?, ?, 'Себестоимость', ?)""",
                        (cost_id, date, doc_num, cost, cost, item_id))
            conn.commit()
        return entry_id

    def create_purchase(self, amount: float, supplier_id: str,
                      description: str = "", doc_number: Optional[str] = None) -> str:
        """Поступление товаров/услуг от поставщика. Дт 91.2 (или 10) - Кт 60."""
        doc_num = doc_number or f"ПОСТ-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        entry_id = str(uuid.uuid4())
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute("""INSERT INTO entries (id, date, doc_type, doc_number, debit, credit, amount, description, contragent_id)
                VALUES (?, ?, 'PURCHASE', ?, '91.2', '60', ?, ?, ?)""",
                (entry_id, datetime.now().isoformat(), doc_num, amount, description, supplier_id))
            conn.commit()
        return entry_id

    def create_manual_entry(self, debit: str, credit: str, amount: float,
                            description: str = "", doc_number: Optional[str] = None) -> str:
        """Ручная операция (бухгалтерская корректировка)."""
        doc_num = doc_number or f"КОРР-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        entry_id = str(uuid.uuid4())
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute("""INSERT INTO entries (id, date, doc_type, doc_number, debit, credit, amount, description)
                VALUES (?, ?, 'MANUAL', ?, ?, ?, ?, ?)""",
                (entry_id, datetime.now().isoformat(), doc_num, debit, credit, amount, description))
            conn.commit()
        return entry_id

    # =====================================================================
    # СПРАВОЧНИКИ
    # =====================================================================
    def add_contragent(self, name: str, type_: str = "client", inn: str = "",
                       full_name: str = "", phone: str = "", email: str = "") -> str:
        cid = str(uuid.uuid4())
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute("""INSERT INTO contragents (id, name, type, inn, full_name, phone, email)
                VALUES (?, ?, ?, ?, ?, ?, ?)""", (cid, name, type_, inn, full_name, phone, email))
            conn.commit()
        return cid

    def add_item(self, name: str, type_: str = "service", price: float = 0,
                 cost_price: float = 0, unit: str = "шт", vat_rate: float = 0) -> str:
        iid = str(uuid.uuid4())
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute("""INSERT INTO items (id, name, type, price, cost_price, unit, vat_rate)
                VALUES (?, ?, ?, ?, ?, ?, ?)""", (iid, name, type_, price, cost_price, unit, vat_rate))
            conn.commit()
        return iid

    # =====================================================================
    # ОТЧЕТЫ
    # =====================================================================
    def osv(self, period: str, account_code: Optional[str] = None) -> List[Dict]:
        """
        Оборотно-сальдовая ведомость (ОСВ) за период YYYY-MM.
        Возвращает по каждому счету: СнДт, СнКт, ОборотДт, ОборотКт, СкДт, СкКт.
        """
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            if account_code:
                c.execute("""SELECT debit, credit, amount FROM entries
                    WHERE date LIKE ? ORDER BY date""", (f"{period}%",))
            else:
                c.execute("""SELECT debit, credit, amount FROM entries
                    WHERE date LIKE ? ORDER BY date""", (f"{period}%",))
            rows = c.fetchall()

            # Считаем обороты по счетам
            accs = {}
            c.execute("SELECT code, type FROM accounts WHERE is_active=1")
            for code, typ in c.fetchall():
                accs[code] = {"type": typ, "debit_turnover": 0.0, "credit_turnover": 0.0}

            for debit, credit, amount in rows:
                if debit in accs:
                    accs[debit]["debit_turnover"] += amount
                if credit in accs:
                    accs[credit]["credit_turnover"] += amount

            result = []
            for code, data in accs.items():
                # Упрощенно: сальдо на начало = 0 (в MVP). В проде читать из balances.
                sn = 0.0
                if data["type"] == "active":
                    sk = sn + data["debit_turnover"] - data["credit_turnover"]
                    result.append({
                        "account": code, "sn_debit": sn, "sn_credit": 0.0,
                        "turnover_debit": data["debit_turnover"], "turnover_credit": data["credit_turnover"],
                        "sk_debit": sk, "sk_credit": 0.0
                    })
                elif data["type"] == "passive":
                    sk = sn + data["credit_turnover"] - data["debit_turnover"]
                    result.append({
                        "account": code, "sn_debit": 0.0, "sn_credit": sn,
                        "turnover_debit": data["debit_turnover"], "turnover_credit": data["credit_turnover"],
                        "sk_debit": 0.0, "sk_credit": sk
                    })
                else:
                    sk_debit = max(0, sn + data["debit_turnover"] - data["credit_turnover"])
                    sk_credit = max(0, sn + data["credit_turnover"] - data["debit_turnover"])
                    result.append({
                        "account": code, "sn_debit": sn, "sn_credit": sn,
                        "turnover_debit": data["debit_turnover"], "turnover_credit": data["credit_turnover"],
                        "sk_debit": sk_debit, "sk_credit": sk_credit
                    })
            return result

    def turnover_by_account(self, account_code: str, period: str) -> Dict:
        """Оборотка по одному счету с детализацией."""
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute("""SELECT date, doc_type, doc_number, debit, credit, amount, description
                FROM entries WHERE (debit=? OR credit=?) AND date LIKE ? ORDER BY date""",
                (account_code, account_code, f"{period}%"))
            rows = c.fetchall()
            total_debit = sum(r[5] for r in rows if r[3] == account_code)
            total_credit = sum(r[5] for r in rows if r[4] == account_code)
            return {
                "account": account_code,
                "period": period,
                "lines": rows,
                "turnover_debit": total_debit,
                "turnover_credit": total_credit
            }

    def profit_loss(self, period: str) -> Dict:
        """Отчет о прибылях и убытках (90 - доходы, 91 - расходы)."""
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute("""SELECT SUM(amount) FROM entries WHERE credit LIKE '90.%' AND date LIKE ?""", (f"{period}%",))
            income = c.fetchone()[0] or 0.0
            c.execute("""SELECT SUM(amount) FROM entries WHERE debit LIKE '90.%' AND date LIKE ?""", (f"{period}%",))
            cost = c.fetchone()[0] or 0.0
            c.execute("""SELECT SUM(amount) FROM entries WHERE debit LIKE '91.2' AND date LIKE ?""", (f"{period}%",))
            expenses = c.fetchone()[0] or 0.0
            c.execute("""SELECT SUM(amount) FROM entries WHERE credit LIKE '91.1' AND date LIKE ?""", (f"{period}%",))
            other_income = c.fetchone()[0] or 0.0
            profit = income + other_income - cost - expenses
            return {
                "period": period,
                "income": income,
                "cost": cost,
                "expenses": expenses,
                "other_income": other_income,
                "profit": profit
            }

    def balance_sheet(self, period: str) -> Dict:
        """Упрощенный баланс: Актив = Пассив + Капитал."""
        osv_data = self.osv(period)
        assets = sum(r["sk_debit"] for r in osv_data if r["sk_debit"] > 0)
        liabilities = sum(r["sk_credit"] for r in osv_data if r["sk_credit"] > 0)
        return {
            "period": period,
            "assets": round(assets, 2),
            "liabilities": round(liabilities, 2),
            "balance_ok": abs(assets - liabilities) < 0.01
        }

    def cash_flow(self, period: str) -> Dict:
        """Движение денежных средств (ДДС) по счетам 50, 51, 57."""
        accounts = ["50", "51", "57.01", "57.02"]
        result = {}
        for acc in accounts:
            t = self.turnover_by_account(acc, period)
            result[acc] = {
                "in": t["turnover_debit"],
                "out": t["turnover_credit"],
                "net": t["turnover_debit"] - t["turnover_credit"]
            }
        return result

    def contragent_balance(self, contragent_id: str) -> float:
        """Текущий баланс по контрагенту (счет 62)."""
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute("""SELECT SUM(amount) FROM entries WHERE debit='62' AND contragent_id=?""", (contragent_id,))
            debit = c.fetchone()[0] or 0.0
            c.execute("""SELECT SUM(amount) FROM entries WHERE credit='62' AND contragent_id=?""", (contragent_id,))
            credit = c.fetchone()[0] or 0.0
            return debit - credit

    def reconciliation_act(self, contragent_id: str, period: str) -> Dict:
        """Акт сверки взаиморасчетов с контрагентом."""
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute("""SELECT date, doc_type, doc_number, debit, credit, amount, description
                FROM entries WHERE contragent_id=? AND date LIKE ? ORDER BY date""",
                (contragent_id, f"{period}%"))
            rows = c.fetchall()
            c.execute("SELECT name, inn FROM contragents WHERE id=?", (contragent_id,))
            contr = c.fetchone()
            return {
                "contragent": contr[0] if contr else "",
                "inn": contr[1] if contr else "",
                "period": period,
                "operations": rows,
                "balance": self.contragent_balance(contragent_id)
            }
