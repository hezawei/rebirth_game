"""Add unique index on (session_id, parent_id, user_choice) for story_nodes

Revision ID: 20250921_163500
Revises: 37691daea28a
Create Date: 2025-09-21 16:35:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '20250921_163500'
down_revision: Union[str, Sequence[str], None] = '37691daea28a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Use a unique index for portability across SQLite and PostgreSQL
    op.create_index(
        'uq_storynode_parent_choice_idx',
        'story_nodes',
        ['session_id', 'parent_id', 'user_choice'],
        unique=True
    )


def downgrade() -> None:
    op.drop_index('uq_storynode_parent_choice_idx', table_name='story_nodes')
