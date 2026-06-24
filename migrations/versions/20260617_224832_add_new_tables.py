from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20260617_224832'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Feature Flags
    op.create_table('feature_flags',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=sa.text('gen_random_uuid()')),
        sa.Column('flag_key', sa.String(100), nullable=False, unique=True),
        sa.Column('flag_type', sa.String(20), nullable=False),
        sa.Column('scope', sa.String(20), nullable=False),
        sa.Column('default_value', sa.JSON(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
    )
    
    # Video Alerts
    op.create_table('video_alerts',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=sa.text('gen_random_uuid()')),
        sa.Column('camera_id', sa.String(64), nullable=False),
        sa.Column('alert_type', sa.String(32), nullable=False),
        sa.Column('confidence', sa.Integer(), nullable=True),
        sa.Column('snapshot_url', sa.String(500), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_resolved', sa.Boolean(), default=False),
        sa.Column('resolved_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
    )
    
    # Dynamic QR Codes
    op.create_table('dynamic_qr_codes',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=sa.text('gen_random_uuid()')),
        sa.Column('client_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('clients.id'), nullable=False),
        sa.Column('qr_payload', sa.String(500), nullable=False),
        sa.Column('signature', sa.String(128), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('is_used', sa.Boolean(), default=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    
    # Services
    op.create_table('services',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=sa.text('gen_random_uuid()')),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('category', sa.String(20), nullable=False),
        sa.Column('subcategory', sa.String(50), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('price', sa.Float(), nullable=False),
        sa.Column('duration_minutes', sa.Integer(), nullable=True),
        sa.Column('max_capacity', sa.Integer(), default=1),
        sa.Column('trainer_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('schedule', sa.JSON(), default=dict),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
    )
    
    # Service Bookings
    op.create_table('service_bookings',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=sa.text('gen_random_uuid()')),
        sa.Column('client_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('clients.id'), nullable=False),
        sa.Column('service_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('services.id'), nullable=False),
        sa.Column('booking_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('status', sa.String(20), default='BOOKED'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade():
    op.drop_table('service_bookings')
    op.drop_table('services')
    op.drop_table('dynamic_qr_codes')
    op.drop_table('video_alerts')
    op.drop_table('feature_flags')
