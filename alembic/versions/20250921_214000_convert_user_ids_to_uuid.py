"""Convert users.id and game_sessions.user_id to UUID type (PostgreSQL)

Revision ID: 20250921_214000
Revises: 20250921_171900
Create Date: 2025-09-21 21:40:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '20250921_214000'
down_revision: Union[str, Sequence[str], None] = '20250921_171900'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop FK to allow type change
    op.execute("ALTER TABLE game_sessions DROP CONSTRAINT IF EXISTS game_sessions_user_id_fkey")

    # Convert users.id to UUID
    op.alter_column(
        'users',
        'id',
        type_=postgresql.UUID(as_uuid=True),
        postgresql_using='id::uuid',
        existing_nullable=False
    )

    # Convert game_sessions.user_id to UUID
    op.alter_column(
        'game_sessions',
        'user_id',
        type_=postgresql.UUID(as_uuid=True),
        postgresql_using='user_id::uuid',
        existing_nullable=False
    )

    # Re-create FK
    op.create_foreign_key(
        None,
        'game_sessions',
        'users',
        ['user_id'],
        ['id']
    )


def downgrade() -> None:
    # Drop FK first
    op.execute("ALTER TABLE game_sessions DROP CONSTRAINT IF EXISTS game_sessions_user_id_fkey")

    # Revert types back to String(36)
    op.alter_column(
        'game_sessions',
        'user_id',
        type_=sa.String(length=36),
        existing_nullable=False
    )
    op.alter_column(
        'users',
        'id',
        type_=sa.String(length=36),
        existing_nullable=False
    )

    # Re-create FK
    op.create_foreign_key(
        None,
        'game_sessions',
        'users',
        ['user_id'],
        ['id']
    )
