"""Provider passwords, expiring sessions and persistent login throttling."""
from alembic import op
import sqlalchemy as sa

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("provider_logins",
        sa.Column("username", sa.String(32), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(256), nullable=False))
    op.create_table("provider_sessions",
        sa.Column("token_hash", sa.String(64), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("device_id", sa.String(64), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False))
    op.create_index("ix_provider_sessions_user_id", "provider_sessions", ["user_id"])
    op.create_index("ix_provider_sessions_expires_at", "provider_sessions", ["expires_at"])
    op.create_table("auth_throttles",
        sa.Column("scope_hash", sa.String(64), primary_key=True),
        sa.Column("window_start", sa.DateTime(), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False))


def downgrade():
    op.drop_table("auth_throttles")
    op.drop_table("provider_sessions")
    op.drop_table("provider_logins")
