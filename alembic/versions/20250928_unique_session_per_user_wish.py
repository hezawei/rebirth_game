"""Ensure unique game session per user wish

Revision ID: 20250928_uniqsess
Revises: 20250924_story_metadata
Create Date: 2025-09-28 13:30:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "20250928_uniqsess"
down_revision: Union[str, None] = "20250924_story_metadata"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 清理潜在的重复会话，仅保留最早的一条记录
    conn = op.get_bind()
    conn.execute(sa.text(
        """
        WITH ranked_sessions AS (
            SELECT id,
                   ROW_NUMBER() OVER (PARTITION BY user_id, wish ORDER BY id) AS rn
            FROM game_sessions
        )
        DELETE FROM game_sessions
        WHERE id IN (
            SELECT id FROM ranked_sessions WHERE rn > 1
        )
        """
    ))

    op.create_unique_constraint(
        "uq_game_sessions_user_wish",
        "game_sessions",
        ["user_id", "wish"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_game_sessions_user_wish",
        "game_sessions",
        type_="unique",
    )
