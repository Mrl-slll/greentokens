"""independent providers: worker kind, capabilities and attempt leases (additive only)"""
from alembic import op
import sqlalchemy as sa


revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("workers", sa.Column("kind", sa.String(length=16), nullable=False, server_default="ray"))
    op.add_column("workers", sa.Column("owner_user_id", sa.String(length=36), nullable=True))
    op.add_column("workers", sa.Column("gpu_count", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("workers", sa.Column("gpu_name", sa.String(length=255), nullable=True))
    op.add_column("workers", sa.Column("capabilities", sa.JSON(), nullable=True))
    op.add_column("job_attempts", sa.Column("lease_expires_at", sa.DateTime(), nullable=True))


def downgrade():
    op.drop_column("job_attempts", "lease_expires_at")
    for name in ("capabilities", "gpu_name", "gpu_count", "owner_user_id", "kind"):
        op.drop_column("workers", name)
