from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20260617_224832'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Clean installations need the core schema before later raw-SQL migrations.
    # Existing installations already stamped at head do not rerun this revision.
    from app.db.base import Base
    import app.models  # noqa: F401 — register every ORM model

    Base.metadata.create_all(bind=op.get_bind())

def downgrade():
    op.drop_table('service_bookings')
    op.drop_table('services')
    op.drop_table('dynamic_qr_codes')
    op.drop_table('video_alerts')
    op.drop_table('feature_flags')
