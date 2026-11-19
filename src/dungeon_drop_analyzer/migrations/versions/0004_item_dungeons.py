"""Masmorras em que cada item pode ser obtido (tabela de associação item_dungeons).

Itens existentes ficam sem masmorras definidas até serem editados manualmente.

Revision ID: 0004
Revises: 0003
Create Date: 2026-11-19
"""

import sqlalchemy as sa
from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "item_dungeons",
        sa.Column("item_id", sa.Integer(), nullable=False),
        sa.Column("dungeon_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["dungeon_id"],
            ["dungeons.id"],
            name=op.f("fk_item_dungeons_dungeon_id_dungeons"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["item_id"],
            ["items.id"],
            name=op.f("fk_item_dungeons_item_id_items"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("item_id", "dungeon_id", name=op.f("pk_item_dungeons")),
    )
    op.create_index("ix_item_dungeons_dungeon_id", "item_dungeons", ["dungeon_id"])


def downgrade() -> None:
    op.drop_index("ix_item_dungeons_dungeon_id", table_name="item_dungeons")
    op.drop_table("item_dungeons")
