"""Enforce unique active game session per user wish

Revision ID: 20250928_uniqsess
Revises: 20250924_story_metadata
Create Date: 2025-09-28 20:45:00
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
    op.execute(
        """
        WITH ranked AS (
            SELECT id,
                   FIRST_VALUE(id) OVER (PARTITION BY user_id, wish ORDER BY id DESC) AS keep_id,
                   ROW_NUMBER() OVER (PARTITION BY user_id, wish ORDER BY id DESC) AS rn
            FROM game_sessions
        )
        UPDATE story_nodes sn
        SET session_id = ranked.keep_id
        FROM ranked
        WHERE sn.session_id = ranked.id
          AND ranked.rn > 1
          AND sn.session_id <> ranked.keep_id;
        """
    )
    op.execute(
        """
        WITH ranked AS (
            SELECT id,
                   FIRST_VALUE(id) OVER (PARTITION BY user_id, wish ORDER BY id DESC) AS keep_id,
                   ROW_NUMBER() OVER (PARTITION BY user_id, wish ORDER BY id DESC) AS rn
            FROM game_sessions
        )
        UPDATE story_saves ss
        SET session_id = ranked.keep_id
        FROM ranked
        WHERE ss.session_id = ranked.id
          AND ranked.rn > 1
          AND ss.session_id <> ranked.keep_id;
        """
    )
    op.execute(
        """
        DELETE FROM game_sessions gs
        USING (
            SELECT id
            FROM (
                SELECT id,
                       ROW_NUMBER() OVER (PARTITION BY user_id, wish ORDER BY id DESC) AS rn
                FROM game_sessions
            ) ranked
            WHERE ranked.rn > 1
        ) dup
        WHERE gs.id = dup.id
        """
    )
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
