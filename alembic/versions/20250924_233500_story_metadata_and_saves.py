"""add story metadata, speculative nodes, saves, and wish moderation log

Revision ID: 20250924_233500_story_metadata_and_saves
Revises: 20250921_214000_convert_user_ids_to_uuid
Create Date: 2025-09-24 23:35:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20250924_233500_story_metadata_and_saves"
down_revision: Union[str, None] = "20250921_214000"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "story_nodes",
        sa.Column(
            "metadata",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )
    op.add_column(
        "story_nodes",
        sa.Column("success_rate", sa.Integer(), nullable=True),
    )
    op.add_column(
        "story_nodes",
        sa.Column(
            "is_speculative",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.add_column(
        "story_nodes",
        sa.Column("speculative_depth", sa.Integer(), nullable=True),
    )
    op.add_column(
        "story_nodes",
        sa.Column("speculative_expires_at", sa.DateTime(), nullable=True),
    )

    op.create_table(
        "story_saves",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("session_id", sa.Integer(), nullable=False),
        sa.Column("node_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=100), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["game_sessions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["node_id"], ["story_nodes.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_story_saves_session_id", "story_saves", ["session_id"])
    op.create_index("ix_story_saves_node_id", "story_saves", ["node_id"])

    op.create_table(
        "wish_moderation_records",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("user_id", sa.String(length=36), nullable=True, index=True),
        sa.Column("wish_text", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_wish_moderation_records_user_id", "wish_moderation_records", ["user_id"])

    # Drop server defaults now that existing rows have been populated
    op.alter_column("story_nodes", "metadata", server_default=None)
    op.alter_column("story_nodes", "is_speculative", server_default=None)


def downgrade() -> None:
    op.alter_column("story_nodes", "metadata", server_default=sa.text("'{}'::jsonb"))
    op.alter_column("story_nodes", "is_speculative", server_default=sa.text("false"))

    op.drop_index("ix_wish_moderation_records_user_id", table_name="wish_moderation_records")
    op.drop_table("wish_moderation_records")

    op.drop_index("ix_story_saves_node_id", table_name="story_saves")
    op.drop_index("ix_story_saves_session_id", table_name="story_saves")
    op.drop_table("story_saves")

    op.drop_column("story_nodes", "speculative_expires_at")
    op.drop_column("story_nodes", "speculative_depth")
    op.drop_column("story_nodes", "is_speculative")
    op.drop_column("story_nodes", "success_rate")
    op.drop_column("story_nodes", "metadata")
