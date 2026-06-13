# app/schemas/enums.py

from enum import Enum


class UserStatus(str, Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    BLOCKED = "BLOCKED"


class ClientStatus(str, Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    BLOCKED = "BLOCKED"


# пол клиента
class GenderEnum(str, Enum):
    МУЖСКОЙ = "МУЖСКОЙ"
    ЖЕНСКИЙ = "ЖЕНСКИЙ"
    НЕ_УКАЗАН = "НЕ_УКАЗАН"


# категория клиента
class ClientCategoryEnum(str, Enum):
    ВЗРОСЛЫЙ = "ВЗРОСЛЫЙ"
    РЕБЁНОК = "РЕБЁНОК"
    ПЕНСИОНЕР = "ПЕНСИОНЕР"
    ИНВАЛИД = "ИНВАЛИД"
    КОРПОРАТИВНЫЙ = "КОРПОРАТИВНЫЙ"
    VIP = "VIP"
    НЕ_УКАЗАНА = "НЕ_УКАЗАНА"


class SubscriptionStatus(str, Enum):
    ACTIVE = "ACTIVE"
    EXPIRED = "EXPIRED"
    FROZEN = "FROZEN"
    CANCELLED = "CANCELLED"


class PaymentStatus(str, Enum):
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    REFUNDED = "REFUNDED"


class VisitStatus(str, Enum):
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    
class CurrencyCodeEnum(str, Enum):
    """Коды валют"""
    RUB = "RUB"
    USD = "USD"
    EUR = "EUR"  
# Алиасы для обратной совместимости
SubscriptionStatusEnum = SubscriptionStatus
PaymentStatusEnum = PaymentStatus
VisitStatusEnum = VisitStatus 



# ============================================================
# ПРИЧИНЫ ЗАМОРОЗКИ АБОНЕМЕНТА
# ============================================================

class FreezeReason(str, Enum):
    """Причины заморозки абонемента"""
    VACATION = "VACATION"               # Отпуск
    ILLNESS = "ILLNESS"                 # Болезнь
    INJURY = "INJURY"                   # Травма
    BUSINESS_TRIP = "BUSINESS_TRIP"     # Командировка
    OTHER = "OTHER"                     # Другое


# ============================================================
# ПРИЧИНЫ ОТМЕНЫ АБОНЕМЕНТА
# ============================================================

class CancellationReason(str, Enum):
    """Причины отмены абонемента"""
    EXPIRED = "EXPIRED"                     # Истёк срок
    USER_REQUEST = "USER_REQUEST"           # Запрос пользователя
    NON_PAYMENT = "NON_PAYMENT"             # Неоплата
    POLICY_VIOLATION = "POLICY_VIOLATION"   # Нарушение правил
    OTHER = "OTHER"                         # Другое
    

# ============================================================
# СТАТУСЫ ПОСЕЩЕНИЙ
# ============================================================

class VisitStatus(str, Enum):
    """Статусы посещения"""
    ACTIVE = "ACTIVE"           # Клиент внутри клуба (есть вход, нет выхода)
    COMPLETED = "COMPLETED"     # Посещение завершено (есть вход и выход)
    CANCELLED = "CANCELLED"     # Отменено (ручная отмена)


class AccessMethod(str, Enum):
    """Способы доступа"""
    QR = "QR"                   # QR-код
    RFID = "RFID"               # RFID-метка/браслет
    MANUAL = "MANUAL"           # Ручной ввод менеджером
    OVERRIDE = "OVERRIDE"       # Принудительное открытие


class AccessDecision(str, Enum):
    """Решение о доступе"""
    ALLOW = "ALLOW"             # Доступ разрешён
    DENY = "DENY"               # Доступ запрещён  
    

# ============================================================
# ТИПЫ УСТРОЙСТВ
# ============================================================

class DeviceType(str, Enum):
    """Типы устройств"""
    TURNSTILE = "turnstile"      # Турникет
    TERMINAL = "terminal"        # Терминал (планшет с ПО)
    CONTROLLER = "controller"    # Контроллер (Сигур, Эра, Wirenboard)
    READER = "reader"            # Считыватель (RFID, QR)
    GATEWAY = "gateway"          # Шлюз
    SENSOR = "sensor"            # Датчик


class DeviceProtocol(str, Enum):
    """Протоколы связи с устройствами"""
    NONE = "none"                # Нет устройства (ручной ввод)
    HTTP = "http"                # HTTP API
    MQTT = "mqtt"                # MQTT
    MODBUS = "modbus"            # Modbus
    SERIAL = "serial"            # RS-232 / RS-485
    GPIO = "gpio"                # Прямое управление GPIO
    SIGUR = "sigur"              # Специфичный протокол Сигур
    ERA = "era"                  # Специфичный протокол Эра


class DeviceManufacturer(str, Enum):
    """Производители устройств"""
    GENERIC = "generic"          # Универсальный/неизвестный
    SIGUR = "sigur"              # Сигур
    ERA = "era"                  # Эра
    WIRENBOARD = "wirenboard"    # Wirenboard
    PERCo = "perco"              # PERCo
    NONE = "none"                # Нет производителя (ручной ввод) 

# ============================================================
# ТИПЫ УЧЁТНЫХ ДАННЫХ
# ============================================================

class CredentialType(str, Enum):
    """Типы учётных данных"""
    QR = "QR"
    RFID = "RFID"


class CredentialStatus(str, Enum):
    """Статусы учётных данных"""
    ACTIVE = "ACTIVE"
    BLOCKED = "BLOCKED"
    EXPIRED = "EXPIRED"


# ============================================================
# ДОСТУП
# ============================================================

class AccessDecision(str, Enum):
    """Решение о доступе"""
    ALLOW = "ALLOW"
    DENY = "DENY"
    ERROR = "ERROR"


class AccessMode(str, Enum):
    """Режим работы"""
    ONLINE = "online"
    OFFLINE = "offline"


# ============================================================
# ШКАФЧИКИ
# ============================================================

class LockType(str, Enum):
    """Типы замков"""
    OFFLINE = "OFFLINE"    # Керонг офлайн
    ONLINE = "ONLINE"      # Керонг онлайн
    KEY = "KEY"            # Обычный ключ


class LockerStatus(str, Enum):
    """Статусы шкафчика"""
    FREE = "FREE"
    OCCUPIED = "OCCUPIED"
    BROKEN = "BROKEN"
    MAINTENANCE = "MAINTENANCE"


class LockerSessionStatus(str, Enum):
    """Статусы сессии шкафчика"""
    ACTIVE = "ACTIVE"
    CLOSED = "CLOSED"
    CANCELLED = "CANCELLED"


class LockerPrivilegeType(str, Enum):
    """Типы привилегий на шкафчики"""
    VIP = "VIP"
    RENTAL = "RENTAL"


# ============================================================
# ВНЕШНИЕ СИСТЕМЫ
# ============================================================

class ExternalSystemType(str, Enum):
    """Типы внешних систем"""
    ONEC = "ONEC"           # 1С
    SKUD = "SKUD"           # СКУД
    FILE_SERVER = "FILE_SERVER"


class SyncStatus(str, Enum):
    """Статусы синхронизации"""
    PENDING = "PENDING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"   
    

# ============================================================
# ФИНАНСОВЫЕ ENUM
# ============================================================

class TransactionType(str, Enum):
    """Типы транзакций кошелька"""
    DEPOSIT = "DEPOSIT"         # Пополнение
    WITHDRAW = "WITHDRAW"       # Списание
    FREEZE = "FREEZE"           # Заморозка
    UNFREEZE = "UNFREEZE"       # Разморозка


class PaymentMethod(str, Enum):
    """Способы оплаты"""
    CASH = "CASH"               # Наличные
    CARD = "CARD"               # Банковская карта
    ONLINE = "ONLINE"           # Онлайн-платёж
    BALANCE = "BALANCE"         # С баланса кошелька
    SBP = "SBP"                 # Система быстрых платежей (СБП)

class PaymentStatus(str, Enum):
    """Статусы платежа"""
    PENDING = "PENDING"         # Ожидает обработки
    COMPLETED = "COMPLETED"     # Успешно выполнен
    FAILED = "FAILED"           # Ошибка
    REFUNDED = "REFUNDED"       # Возвращён
    CANCELLED = "CANCELLED"     # Отменён


class ReceiptType(str, Enum):
    """Типы чеков"""
    SALE = "SALE"               # Чек продажи
    REFUND = "REFUND"           # Чек возврата


class CashOperationType(str, Enum):
    """Типы кассовых операций"""
    INCOME = "INCOME"           # Поступление
    OUTCOME = "OUTCOME"         # Выдача


class CashDeskStatus(str, Enum):
    """Статусы кассовой смены"""
    OPEN = "OPEN"               # Открыта
    CLOSED = "CLOSED"           # Закрыта


class PaymentSystem(str, Enum):
    """Платёжные системы"""
    ALFA_BANK = "ALFA_BANK"         # Альфа-Банк
    VTB = "VTB"                     # ВТБ
    PSB = "PSB"                     # ПСБ (Промсвязьбанк)
    T_BANK = "T_BANK"               # Т-Банк (бывший Тинькофф)
    SBERBANK = "SBERBANK"           # Сбербанк
    YOOMONEY = "YOOMONEY"           # ЮMoney
    CLOUD_PAYMENTS = "CLOUD_PAYMENTS"  # CloudPayments
    STRIPE = "STRIPE"               # Stripe
    GAZPROMBANK = "GAZPROMBANK"     # Газпромбанк
    RAIFFEISEN = "RAIFFEISEN"       # Райффайзенбанк
    SBP = "SBP"                     # Система быстрых платежей (через агрегатора)