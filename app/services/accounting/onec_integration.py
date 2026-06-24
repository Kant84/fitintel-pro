"""
Путь в проекте: app/services/accounting/onec_integration.py
Интеграция с 1С:Предприятие через стандарт CommerceML 2.0.
Поддерживает обмен:
- Номенклатура (товары/услуги фитнес-клуба)
- Контрагенты (клиенты, поставщики)
- Документы: Заказы, Реализация товаров/услуг, Поступление, ПКО, РКО
- Остатки и цены

Режимы:
- 'file': обмен через XML-файлы в папке (типично для 1С УТ/Розница).
- 'http': прямой HTTP-запрос к 1С (OData / Web-сервисы / HTTP-сервис 1С).
- 'mock': эмуляция для тестов.
"""
import os
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import List, Dict, Optional
import requests
import json


class OneCIntegration:
    """Мост между FitIntel Pro и 1С."""

    def __init__(self, mode: str = "mock", exchange_path: str = "./1c_exchange",
                 onec_url: str = "", user: str = "", password: str = ""):
        self.mode = mode
        self.exchange_path = exchange_path
        self.onec_url = onec_url.rstrip("/")
        self.auth = (user, password) if user and password else None
        self.ns = {
            "cml": "urn:1C.ru:commerceml_2",
            "xsi": "http://www.w3.org/2001/XMLSchema-instance"
        }
        if mode == "file":
            os.makedirs(exchange_path, exist_ok=True)

    # =========================================================================
    # ГЕНЕРАЦИЯ CommerceML (выгрузка ИЗ FitIntel В 1С)
    # =========================================================================
    def export_catalog(self, items: List[Dict]) -> str:
        """Выгрузка номенклатуры (услуги/абонементы) в 1С."""
        root = ET.Element("КоммерческаяИнформация")
        root.set("ВерсияСхемы", "2.10")
        root.set("ДатаФормирования", datetime.now().isoformat())

        catalog = ET.SubElement(root, "Каталог")
        ET.SubElement(catalog, "Ид").text = "fitintel-catalog"
        ET.SubElement(catalog, "Наименование").text = "Услуги FitIntel Pro"

        goods = ET.SubElement(catalog, "Товары")
        for item in items:
            good = ET.SubElement(goods, "Товар")
            ET.SubElement(good, "Ид").text = item.get("id", str(uuid.uuid4()))
            ET.SubElement(good, "Наименование").text = item.get("name", "Услуга")
            ET.SubElement(good, "БазоваяЕдиница", {"Код": "796", "НаименованиеПолное": "Услуга"})
            ET.SubElement(good, "Цены")
            price = ET.SubElement(ET.SubElement(good, "Цены"), "Цена")
            ET.SubElement(price, "Представление").text = f"{item.get('price', 0)} RUB"
            ET.SubElement(price, "ЦенаЗаЕдиницу").text = str(item.get("price", 0))
            ET.SubElement(price, "Валюта").text = "RUB"
            ET.SubElement(price, "Единица").text = "шт"
            ET.SubElement(price, "Коэффициент").text = "1"

        tree = ET.ElementTree(root)
        filename = os.path.join(self.exchange_path, f"import_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xml")
        tree.write(filename, encoding="windows-1251", xml_declaration=True)
        return filename

    def export_contragents(self, clients: List[Dict]) -> str:
        """Выгрузка контрагентов (клиентов) в 1С."""
        root = ET.Element("КоммерческаяИнформация")
        root.set("ВерсияСхемы", "2.10")

        classifier = ET.SubElement(root, "Классификатор")
        contragents = ET.SubElement(classifier, "Контрагенты")
        for c in clients:
            ca = ET.SubElement(contragents, "Контрагент")
            ET.SubElement(ca, "Ид").text = c.get("id", "")
            ET.SubElement(ca, "Наименование").text = c.get("name", "")
            ET.SubElement(ca, "ПолноеНаименование").text = c.get("full_name", "")
            ET.SubElement(ca, "ИНН").text = c.get("inn", "")
            ET.SubElement(ca, "КПП").text = c.get("kpp", "")
            ET.SubElement(ca, "Роль", {"Покупатель": "1", "Поставщик": "0"})

        tree = ET.ElementTree(root)
        filename = os.path.join(self.exchange_path, f"contragents_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xml")
        tree.write(filename, encoding="windows-1251", xml_declaration=True)
        return filename

    def export_documents(self, docs: List[Dict]) -> str:
        """Выгрузка документов: реализация услуг, поступления, ПКО, РКО."""
        root = ET.Element("КоммерческаяИнформация")
        root.set("ВерсияСхемы", "2.10")

        documents = ET.SubElement(root, "Документы")
        for d in docs:
            doc = ET.SubElement(documents, "Документ")
            ET.SubElement(doc, "Ид").text = d.get("id", "")
            ET.SubElement(doc, "Номер").text = d.get("number", "")
            ET.SubElement(doc, "Дата").text = d.get("date", datetime.now().strftime("%Y-%m-%d"))
            ET.SubElement(doc, "ХозОперация").text = d.get("type", "Реализация товаров")  # или Поступление, ПКО, РКО
            ET.SubElement(doc, "Роль").text = "Продавец"
            ET.SubElement(doc, "Валюта").text = "RUB"
            ET.SubElement(doc, "Курс").text = "1"
            ET.SubElement(doc, "Сумма").text = str(d.get("total", 0))

            contr = ET.SubElement(doc, "Контрагенты")
            buyer = ET.SubElement(contr, "Контрагент")
            ET.SubElement(buyer, "Ид").text = d.get("client_id", "")
            ET.SubElement(buyer, "Наименование").text = d.get("client_name", "")
            ET.SubElement(buyer, "Роль").text = "Покупатель"

            products = ET.SubElement(doc, "Товары")
            for line in d.get("lines", []):
                product = ET.SubElement(products, "Товар")
                ET.SubElement(product, "Ид").text = line.get("item_id", "")
                ET.SubElement(product, "Наименование").text = line.get("item_name", "")
                ET.SubElement(product, "БазоваяЕдиница", {"Код": "796"})
                ET.SubElement(product, "ЦенаЗаЕдиницу").text = str(line.get("price", 0))
                ET.SubElement(product, "Количество").text = str(line.get("quantity", 1))
                ET.SubElement(product, "Сумма").text = str(line.get("sum", 0))

        tree = ET.ElementTree(root)
        filename = os.path.join(self.exchange_path, f"documents_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xml")
        tree.write(filename, encoding="windows-1251", xml_declaration=True)
        return filename

    # =========================================================================
    # ИМПОРТ из 1С (чтение XML, который 1С выгрузила)
    # =========================================================================
    def import_offers(self, xml_path: str) -> List[Dict]:
        """Импорт цен и остатков из 1С (файл offers.xml)."""
        if not os.path.exists(xml_path):
            return []
        tree = ET.parse(xml_path)
        root = tree.getroot()
        offers = []
        for offer in root.findall(".//cml:Предложение", self.ns):
            oid = offer.find("cml:Ид", self.ns)
            price_el = offer.find(".//cml:ЦенаЗаЕдиницу", self.ns)
            qty_el = offer.find("cml:Количество", self.ns)
            offers.append({
                "id": oid.text if oid is not None else "",
                "price": float(price_el.text) if price_el is not None else 0.0,
                "quantity": float(qty_el.text) if qty_el is not None else 0.0
            })
        return offers

    def import_orders_from_1c(self, xml_path: str) -> List[Dict]:
        """Импорт заказов, созданных в 1С (если менеджер 1С оформил корп. абонемент)."""
        if not os.path.exists(xml_path):
            return []
        tree = ET.parse(xml_path)
        root = tree.getroot()
        orders = []
        for doc in root.findall(".//cml:Документ", self.ns):
            num = doc.find("cml:Номер", self.ns)
            date = doc.find("cml:Дата", self.ns)
            total = doc.find("cml:Сумма", self.ns)
            client_id = doc.find(".//cml:Контрагент/cml:Ид", self.ns)
            orders.append({
                "number": num.text if num is not None else "",
                "date": date.text if date is not None else "",
                "total": float(total.text) if total is not None else 0.0,
                "client_id": client_id.text if client_id is not None else ""
            })
        return orders

    # =========================================================================
    # HTTP-режим (OData / Web-сервисы 1С)
    # =========================================================================
    def odata_query(self, entity: str, top: int = 100) -> List[Dict]:
        """Прямое чтение из 1С через OData (например, Catalog_Номенклатура)."""
        if self.mode != "http":
            return []
        url = f"{self.onec_url}/odata/standard.odata/{entity}?$top={top}&$format=json"
        try:
            r = requests.get(url, auth=self.auth, timeout=30)
            r.raise_for_status()
            return r.json().get("value", [])
        except Exception as e:
            return [{"error": str(e)}]

    def odata_create_document(self, doc_type: str, payload: dict) -> dict:
        """Создание документа в 1С через OData."""
        if self.mode != "http":
            return {"success": False, "error": "Режим не http"}
        url = f"{self.onec_url}/odata/standard.odata/{doc_type}?$format=json"
        try:
            r = requests.post(url, json=payload, auth=self.auth, timeout=30)
            r.raise_for_status()
            return {"success": True, "data": r.json()}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # =========================================================================
    # УТИЛИТЫ
    # =========================================================================
    def list_exchange_files(self) -> List[str]:
        if self.mode != "file":
            return []
        return [f for f in os.listdir(self.exchange_path) if f.endswith(".xml")]

    def read_file_content(self, filename: str) -> str:
        path = os.path.join(self.exchange_path, filename)
        if not os.path.exists(path):
            return ""
        with open(path, "r", encoding="windows-1251", errors="ignore") as f:
            return f.read()


import uuid
