"""Add token_version to users for single-login enforcement

Revision ID: 20250921_171900
Revises: 20250921_163500
Create Date: 2025-09-21 17:19:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '20250921_171900'
down_revision: Union[str, Sequence[str], None] = '20250921_163500'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add token_version with default 0
    op.add_column('users', sa.Column('token_version', sa.Integer(), nullable=False, server_default='0'))


def downgrade() -> None:
    op.drop_column('users', 'token_version')
