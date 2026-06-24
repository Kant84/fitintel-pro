file = r'C:\Users\PC\Desktop\2026\FitNexus AI\FitIntel AI\app\schemas\enums.py'

content = '''# app/schemas/enums.py

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
    MALE = "МУЖСКОЙ"      # алиас для БД
    FEMALE = "ЖЕНСКИЙ"    # алиас для БД


# категория клиента
class ClientCategoryEnum(str, Enum):
    ВЗРОСЛЫЙ = "ВЗРОСЛЫЙ"
    РЕБЁНОК = "РЕБЁНОК"
    ПЕНСИОНЕР = "ПЕНСИОНЕР"
    ИНВАЛИД = "ИНВАЛИД"
    КОРПОРАТИВНЫЙ = "КОРПОРАТИВНЫЙ"
    VIP = "VIP"
    НЕ_УКАЗАНА = "НЕ_УКАЗАНА"
    ADULT = "ВЗРОСЛЫЙ"     # алиас для БД
    CHILD = "РЕБЁНОК"      # алиас для БД


class SubscriptionStatus(str, Enum):
    ACTIVE = "ACTIVE"
    EXPIRED = "EXPIRED"
    FROZEN = "FROZEN"
    CANCELLED = "CANCELLED"


class SubscriptionStatusEnum(str, Enum):
    ACTIVE = "ACTIVE"
    EXPIRED = "EXPIRED"
    FROZEN = "FROZEN"
    CANCELLED = "CANCELLED"
    PENDING = "PENDING"


class PaymentStatus(str, Enum):
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    REFUNDED = "REFUNDED"


class VisitStatus(str, Enum):
    ENTERED = "ENTERED"
    EXITED = "EXITED"
    ACTIVE = "ACTIVE"


class TariffType(str, Enum):
    MONTHLY = "MONTHLY"
    QUARTERLY = "QUARTERLY"
    YEARLY = "YEARLY"
    SINGLE = "SINGLE"
    GROUP = "GROUP"
    PERSONAL = "PERSONAL"


class TariffStatus(str, Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    ARCHIVED = "ARCHIVED"


class RoleCode(str, Enum):
    ADMIN = "ADMIN"
    MANAGER = "MANAGER"
    TRAINER = "TRAINER"
    RECEPTIONIST = "RECEPTIONIST"
    ACCOUNTANT = "ACCOUNTANT"
    CLIENT = "CLIENT"


class PermissionCode(str, Enum):
    USERS_READ = "users.read"
    USERS_CREATE = "users.create"
    USERS_UPDATE = "users.update"
    USERS_DELETE = "users.delete"
    CLIENTS_READ = "clients.read"
    CLIENTS_CREATE = "clients.create"
    CLIENTS_UPDATE = "clients.update"
    CLIENTS_DELETE = "clients.delete"
    TARIFFS_READ = "tariffs.read"
    TARIFFS_CREATE = "tariffs.create"
    TARIFFS_UPDATE = "tariffs.update"
    TARIFFS_DELETE = "tariffs.delete"
    SUBSCRIPTIONS_READ = "subscriptions.read"
    SUBSCRIPTIONS_CREATE = "subscriptions.create"
    SUBSCRIPTIONS_UPDATE = "subscriptions.update"
    SUBSCRIPTIONS_DELETE = "subscriptions.delete"
    VISITS_READ = "visits.read"
    VISITS_CREATE = "visits.create"
    VISITS_UPDATE = "visits.update"
    VISITS_DELETE = "visits.delete"
    REPORTS_READ = "reports.read"
    REPORTS_CREATE = "reports.create"
    SETTINGS_READ = "settings.read"
    SETTINGS_UPDATE = "settings.update"
    DEVICES_READ = "devices.read"
    DEVICES_CREATE = "devices.create"
    DEVICES_UPDATE = "devices.update"
    DEVICES_DELETE = "devices.delete"
    LOCKERS_READ = "lockers.read"
    LOCKERS_CREATE = "lockers.create"
    LOCKERS_UPDATE = "lockers.update"
    LOCKERS_DELETE = "lockers.delete"
    FACE_ID_READ = "face-id.read"
    FACE_ID_CREATE = "face-id.create"
    FACE_ID_UPDATE = "face-id.update"
    FACE_ID_DELETE = "face-id.delete"
    PAYMENTS_READ = "payments.read"
    PAYMENTS_CREATE = "payments.create"
    PAYMENTS_UPDATE = "payments.update"
    PAYMENTS_DELETE = "payments.delete"
    NOTIFICATIONS_READ = "notifications.read"
    NOTIFICATIONS_CREATE = "notifications.create"
    NOTIFICATIONS_UPDATE = "notifications.update"
    NOTIFICATIONS_DELETE = "notifications.delete"
    ANALYTICS_READ = "analytics.read"
    ANALYTICS_CREATE = "analytics.create"
    ANALYTICS_UPDATE = "analytics.update"
    ANALYTICS_DELETE = "analytics.delete"
    BACKUP_READ = "backup.read"
    BACKUP_CREATE = "backup.create"
    BACKUP_UPDATE = "backup.update"
    BACKUP_DELETE = "backup.delete"
    INTEGRATIONS_READ = "integrations.read"
    INTEGRATIONS_CREATE = "integrations.create"
    INTEGRATIONS_UPDATE = "integrations.update"
    INTEGRATIONS_DELETE = "integrations.delete"
    LICENSE_READ = "license.read"
    LICENSE_CREATE = "license.create"
    LICENSE_UPDATE = "license.update"
    LICENSE_DELETE = "license.delete"
    SETUP_READ = "setup.read"
    SETUP_CREATE = "setup.create"
    SETUP_UPDATE = "setup.update"
    SETUP_DELETE = "setup.delete"
    FISCAL_READ = "fiscal.read"
    FISCAL_CREATE = "fiscal.create"
    FISCAL_UPDATE = "fiscal.update"
    FISCAL_DELETE = "fiscal.delete"
    ACCOUNTING_READ = "accounting.read"
    ACCOUNTING_CREATE = "accounting.create"
    ACCOUNTING_UPDATE = "accounting.update"
    ACCOUNTING_DELETE = "accounting.delete"


class CurrencyCodeEnum(str, Enum):
    RUB = "RUB"
    USD = "USD"
    EUR = "EUR"
    GBP = "GBP"
    CNY = "CNY"
    JPY = "JPY"
    KZT = "KZT"
    BYN = "BYN"
    UAH = "UAH"


class PaymentMethod(str, Enum):
    CASH = "CASH"
    CARD = "CARD"
    SBP = "SBP"
    TRANSFER = "TRANSFER"
    ONLINE = "ONLINE"
    SUBSCRIPTION = "SUBSCRIPTION"
    QR = "QR"
    CRYPTOCURRENCY = "CRYPTOCURRENCY"
    OTHER = "OTHER"


class PaymentType(str, Enum):
    INCOME = "INCOME"
    EXPENSE = "EXPENSE"
    TRANSFER = "TRANSFER"
    REFUND = "REFUND"
    ADJUSTMENT = "ADJUSTMENT"
    OTHER = "OTHER"


class DocumentType(str, Enum):
    PKO = "PKO"
    RKO = "RKO"
    REALIZATION = "REALIZATION"
    POSTUPLENIE = "POSTUPLENIE"
    SCF = "SCF"
    ACT = "ACT"
    REPORT = "REPORT"
    OTHER = "OTHER"


class CashDeskStatus(str, Enum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"


class PaymentSystem(str, Enum):
    ALFA_BANK = "ALFA_BANK"
    VTB = "VTB"
    PSB = "PSB"
    T_BANK = "T_BANK"
    SBERBANK = "SBERBANK"
    YOOMONEY = "YOOMONEY"
    CLOUD_PAYMENTS = "CLOUD_PAYMENTS"
    STRIPE = "STRIPE"
    GAZPROMBANK = "GAZPROMBANK"
    RAIFFEISEN = "RAIFFEISEN"
    SBP = "SBP"
'''

with open(file, 'w', encoding='utf-8') as f:
    f.write(content)

print('OK: enums.py created successfully')
print('Size:', len(content))
