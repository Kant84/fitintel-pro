"""FitIntel Pro — неон-иконки в стиле theme.py.

icon(code) — QIcon (код экрана ИЛИ имя глифа); кэш SVG в assets/icons-generated/<тема>/.
polish(root) — эмодзи->иконки по дереву виджетов вкладки; без иконки печатает W5 no-icon.
"""
from pathlib import Path

from PyQt6.QtGui import QIcon

from windows import theme

_SVG = {'home': '<path d="M3 11.5 12 3l9 8.5"/><path d="M5.5 10v11h13V10"/>', 'users': '<circle cx="9" cy="8" r="3.5"/><path d="M2.8 20c.4-3.6 3-5.4 6.2-5.4s5.8 1.8 6.2 5.4"/><path d="M15.5 5.2a3.5 3.5 0 0 1 0 5.9M18 14.9c1.9.7 3.1 2.2 3.4 5.1"/>', 'user': '<circle cx="12" cy="8" r="4"/><path d="M5 20.5c.5-3.8 3.4-5.7 7-5.7s6.5 1.9 7 5.7"/>', 'user-check': '<circle cx="10" cy="8" r="3.6"/><path d="M3.8 20c.5-3.5 3-5.2 6.2-5.2 1.4 0 2.7.3 3.7 1"/><path d="M15.5 18.5l2 2 3.7-3.7"/>', 'child': '<circle cx="12" cy="7" r="3.2"/><path d="M7 20.5c.5-3.4 2.5-5 5-5s4.5 1.6 5 5"/><path d="M12 11.5v3.5"/>', 'credit-card': '<rect x="2.5" y="5.5" width="19" height="13" rx="2"/><path d="M2.5 10h19M6 15h4"/>', 'banknote': '<rect x="2.5" y="6" width="19" height="12" rx="2"/><circle cx="12" cy="12" r="2.8"/><path d="M5.5 9.5h.01M18.5 14.5h.01"/>', 'wallet': '<rect x="3" y="6" width="18" height="13" rx="2"/><path d="M16 12.5h.01M3 9.5h18"/>', 'tag': '<path d="M3.5 12V4.5H11l9.5 9.5-7.5 7.5z"/><circle cx="8.2" cy="9" r="1.4"/>', 'cart': '<circle cx="9.7" cy="19.5" r="1.6"/><circle cx="16.8" cy="19.5" r="1.6"/><path d="M2.8 4.5h2.3l2.2 10.6h9.8l2-7.8H6.1"/>', 'store': '<path d="M4.5 9.5 5.8 4.5h12.4l1.3 5"/><path d="M4.5 9.5a2.3 2.3 0 0 0 4.6 0 2.3 2.3 0 0 0 4.7 0 2.3 2.3 0 0 0 4.7 0"/><path d="M5.5 11.5V20h13v-8.5M9.8 20v-5.5h4.4V20"/>', 'calendar': '<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M3 10h18M8 3v4M16 3v4"/>', 'clock': '<circle cx="12" cy="12" r="8.5"/><path d="M12 7.2V12l3.4 2"/>', 'door': '<path d="M5.5 21V4.5L17 3.5V21"/><path d="M3.5 21h17"/><circle cx="14.8" cy="12" r="1"/>', 'dumbbell': '<path d="M4 9.5v5M7.5 6.5v11M16.5 6.5v11M20 9.5v5M7.5 12h9"/>', 'qr': '<rect x="3.5" y="3.5" width="7" height="7" rx="1"/><rect x="13.5" y="3.5" width="7" height="7" rx="1"/><rect x="3.5" y="13.5" width="7" height="7" rx="1"/><path d="M13.5 13.5h3v3h-3zM20.5 13.5v.01M13.5 20.5v.01M17.5 17h3v3.5h-3z"/>', 'key': '<circle cx="8" cy="8" r="4"/><path d="M11 11l8.5 8.5M16.5 16.5l2-2M19 19l1.5-1.5"/>', 'lockers': '<rect x="4" y="3.5" width="16" height="17" rx="1.5"/><path d="M12 3.5v17M7 8h.01M17 8h.01M7 12h.01M17 12h.01"/>', 'scan': '<path d="M4 8V5.5A1.5 1.5 0 0 1 5.5 4H8M16 4h2.5A1.5 1.5 0 0 1 20 5.5V8M20 16v2.5a1.5 1.5 0 0 1-1.5 1.5H16M8 20H5.5A1.5 1.5 0 0 1 4 18.5V16"/><circle cx="12" cy="10" r="3.2"/><path d="M9.3 14.6c.8.9 4.6.9 5.4 0"/>', 'lock': '<rect x="5" y="10.5" width="14" height="10" rx="2"/><path d="M8 10.5V7.5a4 4 0 0 1 8 0v3"/>', 'unlock': '<rect x="5" y="10.5" width="14" height="10" rx="2"/><path d="M8 10.5V7.5a4 4 0 0 1 7.8-1.2"/>', 'file': '<path d="M6 3h7.5L18 7.5V21H6z"/><path d="M13.5 3v4.5H18"/>', 'folder': '<path d="M3 6.5h5.5l2 2.5H21v9.5H3z"/>', 'chart': '<path d="M4 4v16h16"/><path d="M8.5 16v-5M12.5 16V8M16.5 16v-3"/>', 'trend': '<path d="M3 17l6-6 4 4 8-8"/><path d="M15 7h6v6"/>', 'book': '<path d="M5 4.5h4.8a2 2 0 0 1 2 2V19a2 2 0 0 0-2-2H5z"/><path d="M19 4.5h-4.8a2 2 0 0 0-2 2V19a2 2 0 0 1 2-2H19z"/>', 'list': '<path d="M8 6h13M8 12h13M8 18h13"/><path d="M3.5 6l1 1 2-2M3.5 12l1 1 2-2M3.5 18l1 1 2-2"/>', 'history': '<circle cx="12" cy="12" r="8.5"/><path d="M12 7.2V12l3.4 2"/>', 'printer': '<path d="M7 8V3.5h10V8"/><rect x="3.5" y="8" width="17" height="8" rx="1.5"/><rect x="7" y="13" width="10" height="7.5"/><path d="M17.5 11h.01"/>', 'download': '<path d="M12 4v11M7.5 11 12 15.5 16.5 11M4.5 19.5h15"/>', 'upload': '<path d="M12 15V4M7.5 8 12 3.5 16.5 8M4.5 19.5h15"/>', 'share': '<circle cx="6" cy="12" r="2.4"/><circle cx="17.5" cy="6" r="2.4"/><circle cx="17.5" cy="18" r="2.4"/><path d="M8.2 10.9l7-3.4M8.2 13.1l7 3.4"/>', 'message': '<path d="M4 5.5h16v10.5H9.5L4 20z"/><path d="M8 9.5h8M8 12.5h5"/>', 'send': '<path d="M21 3.5 3 10.8l7 2.2 2.2 7z"/><path d="M10 13l5-4.5"/>', 'bell': '<path d="M6 16v-5.2a6 6 0 0 1 12 0V16l1.6 2.3H4.4z"/><path d="M10.3 20.5a1.8 1.8 0 0 0 3.4 0"/>', 'mail': '<rect x="3" y="5.5" width="18" height="13" rx="2"/><path d="M3.5 7l8.5 6 8.5-6"/>', 'phone': '<path d="M5 4h4l1.5 4-2.2 1.6a12.5 12.5 0 0 0 6.1 6.1L16 13.5l4 1.5v4a2 2 0 0 1-2 2A15 15 0 0 1 3 6a2 2 0 0 1 2-2z"/>', 'pin': '<path d="M12 21s-7-5.8-7-11a7 7 0 0 1 14 0c0 5.2-7 11-7 11z"/><circle cx="12" cy="10" r="2.6"/>', 'cpu': '<rect x="6" y="6" width="12" height="12" rx="2"/><rect x="9.6" y="9.6" width="4.8" height="4.8"/><path d="M9 3v3M15 3v3M9 18v3M15 18v3M3 9h3M3 15h3M18 9h3M18 15h3"/>', 'shield': '<path d="M12 3l7 2.8v5.7c0 4.4-2.9 7.3-7 9-4.1-1.7-7-4.6-7-9V5.8z"/><path d="M9 11.8l2.2 2.2 4-4"/>', 'layout': '<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M12 4v16M12 12h9"/>', 'sliders': '<path d="M4 7h16M4 12h16M4 17h16"/><circle cx="9" cy="7" r="1.8"/><circle cx="15" cy="12" r="1.8"/><circle cx="7" cy="17" r="1.8"/>', 'cog': '<circle cx="12" cy="12" r="3.2"/><path d="M12 3.5v2.4M12 18.1v2.4M3.5 12h2.4M18.1 12h2.4M6 6l1.7 1.7M16.3 16.3 18 18M18 6l-1.7 1.7M7.7 16.3 6 18"/>', 'link': '<path d="M9.5 14.5l5-5"/><path d="M11 6.5l1.4-1.4a4 4 0 0 1 5.6 5.6L16.7 12M13 17.5l-1.4 1.4a4 4 0 0 1-5.6-5.6L7.3 12"/>', 'database': '<ellipse cx="12" cy="5.5" rx="8" ry="2.8"/><path d="M4 5.5V12c0 1.6 3.6 2.8 8 2.8s8-1.2 8-2.8V5.5"/><path d="M4 12v6.5c0 1.6 3.6 2.8 8 2.8s8-1.2 8-2.8V12"/>', 'search': '<circle cx="11" cy="11" r="6.5"/><path d="M16 16l4.5 4.5"/>', 'eye': '<path d="M2.5 12S6 5.8 12 5.8 21.5 12 21.5 12 18 18.2 12 18.2 2.5 12 2.5 12z"/><circle cx="12" cy="12" r="2.8"/>', 'plus': '<path d="M12 5v14M5 12h14"/>', 'minus': '<path d="M5 12h14"/>', 'x': '<path d="M6 6l12 12M18 6 6 18"/>', 'check': '<path d="M4.5 12.5l5 5 10-11"/>', 'pencil': '<path d="M4 20l1-4L16.5 4.5a2.1 2.1 0 0 1 3 3L8 19z"/>', 'trash': '<path d="M4 7h16M9 7V4.5h6V7M6.5 7l1 13h9l1-13M10 11v6M14 11v6"/>', 'refresh': '<path d="M20 12a8 8 0 1 1-2.3-5.6M20 3.5V8h-4.5"/>', 'play': '<path d="M7 4.5l12 7.5-12 7.5z"/>', 'pause': '<path d="M8 5v14M16 5v14"/>', 'snowflake': '<path d="M12 3v18M4.2 7.5l15.6 9M19.8 7.5l-15.6 9M12 3l-2 2.5M12 3l2 2.5M12 21l-2-2.5M12 21l2-2.5"/>', 'star': '<path d="M12 3.5l2.7 5.6 6.1.8-4.5 4.2 1.1 6-5.4-2.9-5.4 2.9 1.1-6L3.2 9.9l6.1-.8z"/>', 'gift': '<rect x="4" y="10.5" width="16" height="10" rx="1"/><path d="M12 10.5V20.5M4 14.5h16M12 10.5C9.5 10.5 7.2 9.6 7.2 7.3 7.2 5.4 9 4.7 10 5.6c1 .9 2 3 2 4.9 0-1.9 1-4 2-4.9 1-.9 2.8-.2 2.8 1.7 0 2.3-2.3 3.2-4.8 3.2z"/>', 'camera': '<path d="M4 8h3.2L9 5.5h6L16.8 8H20v11H4z"/><circle cx="12" cy="13" r="3.4"/>', 'zap': '<path d="M13 2.5 4.5 13.5H11L9.5 21.5 18 10.5h-6.5z"/>', 'volume-x': '<path d="M4 9.5v5h3.5L13 19V5L7.5 9.5z"/><path d="M17 9l5 6M22 9l-5 6"/>', 'pulse': '<path d="M3 12h4l2.5-6 4 12 2.5-6h5"/>', 'music': '<path d="M9 18.5V6l10-2v12.5"/><circle cx="6.8" cy="18.5" r="2.2"/><circle cx="16.8" cy="16.5" r="2.2"/>', 'wand': '<path d="M5 21 16.5 9.5"/><path d="M14.5 4l.9 2.1 2.1.9-2.1.9-.9 2.1-.9-2.1-2.1-.9 2.1-.9z"/><path d="M19.5 12.5l.6 1.4 1.4.6-1.4.6-.6 1.4-.6-1.4-1.4-.6 1.4-.6z"/>', 'circle': '<circle cx="12" cy="12" r="8.5"/>'}
_MAP = {'dashboard': 'home', 'analytics': 'trend', 'clients': 'users', 'subscriptions': 'credit-card', 'tariffs': 'tag', 'services': 'dumbbell', 'visits': 'door', 'schedule': 'calendar', 'payments': 'banknote', 'music': 'music', 'reports': 'chart', 'documents': 'file', 'users': 'user', 'roles': 'shield', 'devices': 'cpu', 'face_id': 'scan', 'license': 'award', 'ui_config': 'layout', 'setup': 'wand', 'settings': 'cog', 'connections': 'database', 'integrations': 'link', 'messenger': 'message', 'notifications': 'bell', 'commerce': 'store', 'export': 'share', 'accounting': 'book', 'audit': 'list', 'ai_center': 'spark', 'credentials': 'key', 'club_params': 'sliders', 'shop': 'cart', 'trainers': 'user-check', 'children': 'child'}
_TMPL = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="{c}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">{body}</svg>'
_KEYWORDS = [('sms', 'message'), ('push', 'bell'), ('веб-пуш', 'bell'), ('обуч', 'spark'), ('дообуч', 'spark'), ('риск', 'pulse'), ('прогноз', 'trend'), ('сверить', 'check'), ('статус', 'eye'), ('папк', 'folder'), ('логов', 'history'), ('ошиб', 'list'), ('пко', 'banknote'), ('рко', 'banknote'), ('проводк', 'list'), ('1с fitness', 'dumbbell'), ('1с', 'database'), ('внешн', 'link'), ('a&a', 'share'), ('обзор', 'eye'), ('теплов', 'pulse'), ('отток', 'pulse'), ('проверить связь', 'link'), ('провер', 'check'), ('qr', 'qr'), ('pdf', 'download'), ('csv', 'download'), ('x-отчёт', 'chart'), ('x-отчет', 'chart'), ('открыть смену', 'unlock'), ('закрыть смену', 'lock'), ('снятие кассы', 'banknote'), ('инкасс', 'banknote'), ('смену', 'clock'), ('смена', 'clock'), ('снять с камер', 'camera'), ('камер', 'camera'), ('фото', 'camera'), ('печать', 'printer'), ('принтер', 'printer'), ('сменить парол', 'lock'), ('парол', 'lock'), ('бонус', 'star'), ('звёзд', 'star'), ('подар', 'gift'), ('email', 'mail'), ('e-mail', 'mail'), ('почт', 'mail'), ('телефон', 'phone'), ('адрес', 'pin'), ('mute', 'volume-x'), ('энерджи', 'zap'), ('пульс', 'pulse'), ('демо', 'spark'), ('активир', 'award'), ('лиценз', 'award'), ('забвение', 'trash'), ('анонимиз', 'trash'), ('магазин', 'cart'), ('продаж', 'cart'), ('продать', 'cart'), ('новая запись', 'plus'), ('добавить', 'plus'), ('записать', 'plus'), ('создать', 'plus'), ('новый', 'plus'), ('добав', 'plus'), ('отменить', 'x'), ('удалить', 'trash'), ('убрать', 'trash'), ('обновить', 'refresh'), ('загрузить', 'refresh'), ('синхрон', 'refresh'), ('сохранить', 'check'), ('подтверд', 'check'), ('привязать', 'link'), ('замороз', 'snowflake'), ('размороз', 'play'), ('возобнов', 'play'), ('редакт', 'pencil'), ('назнач', 'pencil'), ('изменить', 'pencil'), ('подписать', 'pencil'), ('тренер', 'user-check'), ('клиент', 'users'), ('дети', 'child'), ('ребён', 'child'), ('ребен', 'child'), ('отправ', 'send'), ('рассыл', 'send'), ('сообщен', 'message'), ('напомин', 'bell'), ('уведомл', 'bell'), ('журнал', 'history'), ('бухгалтер', 'book'), ('коммерц', 'store'), ('тенант', 'store'), ('экспорт', 'share'), ('импорт', 'download'), ('выгруз', 'download'), ('интеграц', 'link'), ('подключен', 'link'), ('браслет', 'key'), ('карты', 'key'), ('ключ', 'key'), ('музык', 'music'), ('отчёт', 'chart'), ('отчет', 'chart'), ('аналит', 'trend'), ('статист', 'chart'), ('финанс', 'banknote'), ('платеж', 'banknote'), ('оплат', 'banknote'), ('баланс', 'wallet'), ('кошел', 'wallet'), ('расписан', 'calendar'), ('заняти', 'calendar'), ('впустить', 'door'), ('выпустить', 'door'), ('вход', 'door'), ('выход', 'door'), ('посещен', 'door'), ('скуд', 'door'), ('услуг', 'dumbbell'), ('абонемент', 'credit-card'), ('тариф', 'tag'), ('параметр', 'sliders'), ('настрой', 'cog'), ('рол', 'shield'), ('прав', 'shield'), ('пользовател', 'user'), ('поиск', 'search'), ('истори', 'history'), ('документ', 'file'), ('шаблон', 'file'), ('шкафчик', 'lockers'), ('шкаф', 'lockers'), ('face', 'scan'), ('лицо', 'scan'), ('устройств', 'cpu'), ('оборудован', 'cpu'), ('поддержк', 'message'), ('помощь', 'message'), ('закрыть', 'x'), ('выйти', 'door'), ('завершить', 'check'), ('стоп', 'pause'), ("трек", "music"), ("ai центр", "spark"), ("срок хранения", "clock"),
    ("мастер установки", "wand"), ("json", "share"), ("csv", "download"),
    ("xls", "download"), ("тенанты", "users"), ("применить", "sliders"), ("эфир", "play"), ("energize", "zap"),
    ("фон", "play"), ("записи", "calendar"), ("возврат", "refresh"),
    ("провести платёж", "banknote"), ("касса", "banknote"),
    ("прибыль", "trend"), ("осв", "book"), ("сформировать", "chart"),
    ("сгенерировать", "file"), ("white-label", "store"),
    ("вкл/выкл", "refresh"), ("скачать", "download"), ("webhook", "link"),
    ("тест связи", "link"), ("чаты", "message"), ("привязки", "link"),
    ("показать удалённых", "eye"), ("лейблы", "message"), ("найти", "search"),
    ("симуляция", "scan"), ("сбросить к умолчаниям", "refresh"),
    ("программирование замков", "key"), ("онлайн-замки", "unlock"),
    ("сброс к заводским", "trash"), ("очистить носитель", "trash"),
    ("очистить замок", "trash"), ("сменить сектор", "refresh"),
    ("клонировать", "copy"), ("режим личный", "lock"),
    ("мастер-карта", "key"), ("карта доступа", "key"), ("прочитать карту", "eye"),
    ("sms", "message"), ("push", "bell"),]

_cache_dir = Path(__file__).parents[1] / "assets" / "icons-generated"


def icon(code: str) -> QIcon:
    name = _MAP.get(code) or (code if code in _SVG else "circle")
    body = _SVG.get(name, _SVG["circle"])
    color = "#00f0ff" if getattr(theme, "DARK", True) else "#4338ca"
    sub = _cache_dir / ("dark" if color == "#00f0ff" else "light")
    sub.mkdir(parents=True, exist_ok=True)
    p = sub / f"{name}.svg"
    if not p.exists():
        p.write_text(_TMPL.format(c=color, body=body), encoding="utf-8")
    return QIcon(str(p))


import re as _re

_EMOJI_PREFIX = _re.compile(r"^[^\wА-Яа-я0-9]+\s*", _re.UNICODE)
_noicon_seen = set()


def _kw_icon(text: str) -> str:
    t = (text or "").lower()
    for kw, code in _KEYWORDS:
        if kw in t:
            return code
    return "circle"


def polish(root) -> None:
    """Кнопки/вкладки: срезать эмодзи-префикс, поставить неон-иконку.
    Обход — Qt findChildren (C++-траверсал): рекурсии Python-стека нет.
    Без иконки — печатает W5 no-icon (один раз на текст)."""
    from PyQt6.QtWidgets import QAbstractButton, QTabWidget, QCheckBox
    for w in root.findChildren(QAbstractButton):
        try:
            txt = w.text()
            clean = _EMOJI_PREFIX.sub("", txt).strip()
            if clean != txt:
                w.setText(clean)
            if isinstance(w, QCheckBox) or not clean or len(clean) <= 2:
                continue
            if w.icon().isNull():
                code = _kw_icon(clean)
                if code == "circle" and clean not in _noicon_seen:
                    _noicon_seen.add(clean)
                    print(f"W5 no-icon: {clean!r}")
                w.setIcon(icon(code))
        except Exception as _e:
            print("polish btn:", str(_e)[:120])
    for w in root.findChildren(QTabWidget):
        try:
            for i in range(w.count()):
                txt = w.tabText(i)
                clean = _EMOJI_PREFIX.sub("", txt).strip()
                if clean != txt:
                    w.setTabText(i, clean)
                if clean and w.tabIcon(i).isNull():
                    code = _kw_icon(clean)
                    if code == "circle" and clean not in _noicon_seen:
                        _noicon_seen.add(clean)
                        print(f"W5 no-icon: {clean!r}")
                    w.setTabIcon(i, icon(code))
        except Exception as _e:
            print("polish tabs:", str(_e)[:120])


print(f"[icons] W5 v2.4 загружен: {len(_SVG)} глифов, {len(_KEYWORDS)} ключевых слов")