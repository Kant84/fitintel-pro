import os
from typing import List, Dict


class BankStatementParser:
    """Парсер текстовых выписок (1С / ДиректБанк / Клиент-Банк)."""

    def parse_txt_file(self, file_path: str) -> List[Dict]:
        payments_found: List[Dict] = []
        current_doc: Dict = {}

        if not os.path.exists(file_path):
            return []

        try:
            with open(file_path, 'r', encoding='windows-1251', errors='ignore') as f:
                for line in f:
                    line = line.strip()

                    if line == "СекцияДокумент=Платежное поручение":
                        current_doc = {}

                    elif line.startswith("Сумма="):
                        try:
                            val = line.split("=", 1)[1].replace(" ", "").replace(",", ".")
                            current_doc["amount"] = float(val)
                        except ValueError:
                            current_doc["amount"] = 0.0

                    elif line.startswith("Плательщик1="):
                        current_doc["payer"] = line.split("=", 1)[1]

                    elif line.startswith("ПлательщикИНН="):
                        current_doc["inn"] = line.split("=", 1)[1]

                    elif line.startswith("Дата="):
                        current_doc["date"] = line.split("=", 1)[1]

                    elif line.startswith("НазначениеПлатежа="):
                        current_doc["purpose"] = line.split("=", 1)[1]

                    elif line.startswith("СуммаСписано="):
                        # Явный признак расхода
                        current_doc["_is_expense"] = True

                    elif line == "КонецДокумента":
                        if self._is_income(current_doc):
                            payments_found.append(current_doc)
                        current_doc = {}

            return payments_found

        except Exception as e:
            print(f"[PARSER ERROR] {e}")
            return []

    def _is_income(self, doc: dict) -> bool:
        """Проверка, что документ — входящий платёж (клуб получил деньги)."""
        if "amount" not in doc or doc.get("amount", 0) <= 0:
            return False
        if doc.get("_is_expense"):
            return False

        # Дополнительная проверка по назначению (опционально)
        purpose = doc.get("purpose", "").lower()
        if "возврат покупателю" in purpose:
            return False

        return True