"""Create document template schema and seed built-in templates.

Revision: m2026_10_28_document_templates
Revises: m2026_10_28_media_audit
"""
from alembic import op
import sqlalchemy as sa

revision = "m2026_10_28_document_templates"
down_revision = "m2026_10_28_media_audit"
branch_labels = None
depends_on = None


TEMPLATES = [
    (
        "contract_standard",
        "Договор оказания услуг (стандартный)",
        "contract",
        """ДОГОВОР ОКАЗАНИЯ УСЛУГ

Дата: {{date}}
Заказчик: {{client_name}}
Телефон: {{client_phone}}
Email: {{client_email}}

1. Исполнитель предоставляет Заказчику доступ к услугам фитнес-клуба
в соответствии с выбранным тарифом.
2. Заказчик обязуется соблюдать правила клуба и оплатить выбранные услуги.
3. Срок действия, стоимость и порядок оказания услуг определяются
условиями выбранного тарифа.

Исполнитель: ____________________
Заказчик: ____________________""",
    ),
    (
        "contract_vip",
        "Договор VIP",
        "contract",
        """ДОГОВОР ОКАЗАНИЯ УСЛУГ VIP

Дата: {{date}}
Заказчик: {{client_name}}
Телефон: {{client_phone}}
Email: {{client_email}}

1. Исполнитель предоставляет Заказчику услуги фитнес-клуба
в объёме выбранного VIP-тарифа.
2. Перечень дополнительных услуг, срок действия и стоимость
определяются условиями VIP-тарифа.
3. Заказчик обязуется соблюдать правила клуба.

Исполнитель: ____________________
Заказчик: ____________________""",
    ),
    (
        "consent_personal",
        "Согласие на обработку персональных данных",
        "consent",
        """СОГЛАСИЕ НА ОБРАБОТКУ ПЕРСОНАЛЬНЫХ ДАННЫХ

Я, {{client_name}}, дата рождения: {{birth_date}},
даю согласие на обработку моих персональных данных:
фамилии, имени, отчества, даты рождения, номера телефона,
адреса электронной почты и фотографии при использовании
системы контроля доступа.

Цели обработки: заключение и исполнение договора,
предоставление услуг клуба и контроль доступа.

Согласие может быть отозвано письменным заявлением.

Дата: {{date}}
Подпись: ____________________""",
    ),
    (
        "medical_clearance",
        "Медицинская справка",
        "medical",
        """МЕДИЦИНСКАЯ СПРАВКА

Клиент: {{client_name}}
Дата рождения: {{birth_date}}

Сведения о допуске к физическим нагрузкам:
____________________________________________________
____________________________________________________

Медицинская организация: ____________________
Врач: ____________________
Дата: {{date}}
Подпись и печать: ____________________""",
    ),
    (
        "cancel_request",
        "Заявление на расторжение договора",
        "request",
        """ЗАЯВЛЕНИЕ НА РАСТОРЖЕНИЕ ДОГОВОРА

Я, {{client_name}}, прошу расторгнуть договор
на оказание услуг фитнес-клуба.

Телефон: {{client_phone}}
Email: {{client_email}}
Основание: _________________________________________

Дата: {{date}}
Подпись: ____________________""",
    ),
    (
        "receipt",
        "Квитанция об оплате",
        "receipt",
        """КВИТАНЦИЯ ОБ ОПЛАТЕ

Дата: {{date}}
Плательщик: {{client_name}}

Назначение платежа: ________________________________
Сумма: _____________________________________________
Основание: _________________________________________

Получатель: ____________________
Подпись: ____________________""",
    ),
]


def upgrade():
    bind = op.get_bind()

    op.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS document_templates (
            id SERIAL PRIMARY KEY,
            code VARCHAR(64) UNIQUE,
            name VARCHAR(255) NOT NULL,
            doc_type VARCHAR(64) DEFAULT 'contract',
            content TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT NOW()
        )
    """))

    for statement in (
        "ALTER TABLE document_templates ADD COLUMN IF NOT EXISTS "
        "doc_type VARCHAR(64) DEFAULT 'contract'",
        "ALTER TABLE document_templates ADD COLUMN IF NOT EXISTS "
        "content TEXT DEFAULT ''",
        "ALTER TABLE document_templates ADD COLUMN IF NOT EXISTS "
        "code VARCHAR(64)",
        "ALTER TABLE document_templates ADD COLUMN IF NOT EXISTS "
        "created_at TIMESTAMP DEFAULT NOW()",
        "CREATE UNIQUE INDEX IF NOT EXISTS ux_doc_templates_code "
        "ON document_templates(code)",
    ):
        op.execute(sa.text(statement))

    for code, name, doc_type, content in TEMPLATES:
        bind.execute(sa.text("""
            INSERT INTO document_templates (code, name, doc_type, content)
            VALUES (:code, :name, :doc_type, :content)
            ON CONFLICT (code) DO NOTHING
        """), {
            "code": code,
            "name": name,
            "doc_type": doc_type,
            "content": content,
        })


def downgrade():
    # Встроенные записи и таблица могли существовать до миграции.
    pass