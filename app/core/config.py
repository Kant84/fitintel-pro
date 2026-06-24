# app\core\config.py
from functools import lru_cache
from typing import Literal

from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Главный класс конфигурации проекта.

    Он читает переменные окружения из .env файла,
    приводит их к нужным типам,
    валидирует и предоставляет их всему приложению
    через единый объект settings.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # ==========================================================
    # 1. Общие настройки приложения
    # ==========================================================

    APP_NAME: str = Field(
        default="FitIntel Pro",
        description="Имя приложения, отображается в документации и логах.",
    )

    APP_VERSION: str = Field(
        default="1.3.1",
        description="Версия приложения.",
    )

    APP_ENV: Literal["dev", "test", "prod"] = Field(
        default="dev",
        description="Текущая среда запуска приложения.",
    )

    APP_DEBUG: bool = Field(
        default=True,
        description="Флаг режима отладки.",
    )

    APP_HOST: str = Field(
        default="0.0.0.0",
        description="Хост, на котором запускается приложение.",
    )

    APP_PORT: int = Field(
        default=8000,
        description="Порт запуска приложения.",
    )

    API_V1_PREFIX: str = Field(
        default="/api/v1",
        description="Префикс для всех маршрутов API первой версии.",
    )

    API_DOMAIN: str = Field(
        default="http://localhost:8000",
        description="Внешний адрес API.",
    )

    DOCS_ENABLED: bool = Field(
        default=True,
        description="Включать ли Swagger и ReDoc.",
    )

    # ==========================================================
    # 2. Безопасность и JWT
    # ==========================================================

    SECRET_KEY: str = Field(
        default="change_me_super_secret_key",
        description="Секретный ключ для подписи токенов и других чувствительных операций.",
    )

    JWT_ALGORITHM: str = Field(
        default="HS256",
        description="Алгоритм подписи JWT.",
    )

    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        default=30,
        description="Время жизни access token в минутах.",
    )

    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(
        default=7,
        description="Время жизни refresh token в днях.",
    )

    # ==========================================================
    # 3. PostgreSQL
    # ==========================================================

    POSTGRES_HOST: str = Field(
        default="127.0.0.1",
        description="Хост PostgreSQL.",
    )

    POSTGRES_PORT: int = Field(
        default=5433,
        description="Порт PostgreSQL.",
    )

    POSTGRES_DB: str = Field(
        default="fitnexus_ai",
        description="Имя базы данных PostgreSQL.",
    )

    POSTGRES_USER: str = Field(
        default="fitnexus_user",
        description="Имя пользователя PostgreSQL.",
    )

    POSTGRES_PASSWORD: str = Field(
        default="FitNexus_User_2026!",
        description="Пароль пользователя PostgreSQL.",
    )

    # ==========================================================
    # 4. Redis
    # ==========================================================

    REDIS_HOST: str = Field(
        default="localhost",
        description="Хост Redis.",
    )

    REDIS_PORT: int = Field(
        default=6380,
        description="Порт Redis.",
    )

    REDIS_DB: int = Field(
        default=0,
        description="Номер базы Redis.",
    )

    REDIS_PASSWORD: str | None = Field(
        default=None,
        description="Пароль Redis, если включена защита.",
    )

    # ==========================================================
    # 5. SMTP Email
    # ==========================================================
    SMTP_HOST: str = Field(
        default="",
        description="SMTP хост (например, mail.fixintel.ru)",
    )
    SMTP_PORT: int = Field(
        default=587,
        description="SMTP порт (обычно 587)",
    )
    SMTP_USER: str = Field(
        default="",
        description="SMTP пользователь (email)",
    )
    SMTP_PASSWORD: str = Field(
        default="",
        description="SMTP пароль",
    )
    SMTP_TLS: bool = Field(
        default=True,
        description="Использовать TLS",
    )
    SMTP_FROM_NAME: str = Field(
        default="FitIntel PRO",
        description="Имя отправителя",
    )
    SMTP_FROM_EMAIL: str = Field(
        default="",
        description="Email отправителя",
    )

    # ==========================================================
    # 6. CORS
    # ==========================================================

    BACKEND_CORS_ORIGINS: str = Field(
        default="http://localhost:3000,http://127.0.0.1:3000",
        description="Разрешенные источники CORS, перечисленные через запятую.",
    )

    # ==========================================================
    # 6. Логи и базовые системные настройки
    # ==========================================================

    LOG_LEVEL: str = Field(
        default="INFO",
        description="Уровень логирования приложения.",
    )

    DEFAULT_TIMEZONE: str = Field(
        default="Europe/Berlin",
        description="Часовой пояс по умолчанию.",
    )

    DEFAULT_CURRENCY: str = Field(
        default="RUB",
        description="Валюта по умолчанию.",
    )

    MAINTENANCE_MODE: bool = Field(
        default=False,
        description="Флаг режима технического обслуживания.",
    )

    # ==========================================================
    # 7. Будущие интеграции и фоновые задачи
    # ==========================================================

    CELERY_BROKER_URL: str = Field(
        default="redis://localhost:6380/0",
        description="Адрес брокера очередей Celery.",
    )

    CELERY_RESULT_BACKEND: str = Field(
        default="redis://localhost:6380/1",
        description="Адрес хранилища результатов Celery.",
    )

    SENTRY_DSN: str | None = Field(
        default=None,
        description="DSN для отправки ошибок в Sentry.",
    )

    

    # ==========================================================
    # 8. Внешние интеграции (1C, Mobifitness и др.)
    # ==========================================================

    ONE_C_API_URL: str | None = Field(
        default=None,
        description="URL API 1С для синхронизации",
    )
    ONE_C_API_KEY: str | None = Field(
        default=None,
        description="Ключ API 1С",
    )

    MOBIFITNESS_API_URL: str | None = Field(
        default=None,
        description="URL API Mobifitness",
    )
    MOBIFITNESS_API_KEY: str | None = Field(
        default=None,
        description="Ключ API Mobifitness",
    )

    WEBHOOK_URL: str | None = Field(
        default=None,
        description="URL для отправки вебхуков",
    )

    # Telegram для уведомлений
    TELEGRAM_BOT_TOKEN: str | None = Field(
        default=None,
        description="Токен Telegram бота для уведомлений",
    )

    # MAX Messenger для push-уведомлений
    MAX_BOT_TOKEN: str | None = Field(
        default=None,
        description="Токен MAX Messenger бота",
    )
    MAX_API_URL: str = Field(
        default="https://api.max.ru",
        description="Базовый URL MAX Messenger API",
    )

    # SMS провайдер
    SMS_PROVIDER: str | None = Field(
        default=None,
        description="SMS провайдер (smsc, smsru, twilio)",
    )
    SMS_API_KEY: str | None = Field(
        default=None,
        description="Ключ API SMS провайдера",
    )
    

    # ==========================================================
    # QR-КОДЫ
    # ==========================================================

    QR_CODE_SIZE: int = Field(
        default=250,
        description="Размер QR-кода в пикселях"
    )
    QR_ERROR_CORRECTION: str = Field(
        default="M",
        description="Уровень коррекции ошибок: L, M, Q, H"
    )
    
    @computed_field
    @property
    def DATABASE_URL(self) -> str:
        """
        Готовая строка подключения к PostgreSQL через psycopg.
        Она будет использоваться SQLAlchemy для синхронной работы с базой.

        """
        return (
        f"postgresql+psycopg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
        f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @computed_field
    @property
    def REDIS_URL(self) -> str:
        """
        Готовая строка подключения к Redis.

        Если пароль указан, включаем его в URL.
        Если пароля нет, используем обычную строку подключения.
        """
        if self.REDIS_PASSWORD:
            return (
                f"redis://:{self.REDIS_PASSWORD}@"
                f"{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
            )
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    @computed_field
    @property
    def cors_origins_list(self) -> list[str]:
        """
        Преобразуем строку CORS origins в список.

        Было:
            "http://localhost:3000,http://127.0.0.1:3000"

        Станет:
            ["http://localhost:3000", "http://127.0.0.1:3000"]
        """
        return [item.strip() for item in self.BACKEND_CORS_ORIGINS.split(",") if item.strip()]

    @computed_field
    @property
    def is_dev(self) -> bool:
        """
        Удобный флаг для проверки, что приложение запущено в dev-среде.
        """
        return self.APP_ENV == "dev"

    @computed_field
    @property
    def is_test(self) -> bool:
        """
        Удобный флаг для проверки, что приложение запущено в test-среде.
        """
        return self.APP_ENV == "test"

    @computed_field
    @property
    def is_prod(self) -> bool:
        """
        Удобный флаг для проверки, что приложение запущено в prod-среде.
        """
        return self.APP_ENV == "prod"


@lru_cache
def get_settings() -> Settings:
    """
    Возвращает один кэшированный экземпляр настроек.

    Это важно, чтобы:
    - не перечитывать .env много раз,
    - не создавать объект настроек повторно,
    - использовать единый объект по всему приложению.
    """
    return Settings()


settings = get_settings()