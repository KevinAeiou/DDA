"""Esquema inicial: masmorras, itens, incursões e auditoria.

Revision ID: 0001
Revises:
Create Date: 2026-11-14
"""

import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "dungeons",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100, collation="NOCASE"), nullable=False),
        sa.Column("difficulty", sa.Integer(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("1"), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint("difficulty BETWEEN 1 AND 5", name=op.f("ck_dungeons_difficulty")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_dungeons")),
        sa.UniqueConstraint("name", name=op.f("uq_dungeons_name")),
    )
    op.create_table(
        "items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100, collation="NOCASE"), nullable=False),
        sa.Column("category", sa.String(length=100), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("1"), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_items")),
        sa.UniqueConstraint("name", name=op.f("uq_items_name")),
    )
    op.create_table(
        "runs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("dungeon_id", sa.Integer(), nullable=False),
        sa.Column("item_id", sa.Integer(), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=False),
        sa.Column("duration_seconds", sa.Integer(), nullable=True),
        sa.Column("game_version", sa.String(length=100), nullable=True),
        sa.Column("bonus_status", sa.String(length=10), server_default="unknown", nullable=False),
        sa.Column("event_status", sa.String(length=10), server_default="unknown", nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "duration_seconds IS NULL OR duration_seconds >= 0", name=op.f("ck_runs_duration")
        ),
        sa.CheckConstraint(
            "bonus_status IN ('yes', 'no', 'unknown')", name=op.f("ck_runs_bonus_status")
        ),
        sa.CheckConstraint(
            "event_status IN ('yes', 'no', 'unknown')", name=op.f("ck_runs_event_status")
        ),
        sa.ForeignKeyConstraint(
            ["dungeon_id"],
            ["dungeons.id"],
            name=op.f("fk_runs_dungeon_id_dungeons"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["item_id"], ["items.id"], name=op.f("fk_runs_item_id_items"), ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_runs")),
    )
    op.create_index(op.f("ix_runs_completed_at"), "runs", ["completed_at"])
    op.create_index(op.f("ix_runs_dungeon_id"), "runs", ["dungeon_id"])
    op.create_index(op.f("ix_runs_item_id"), "runs", ["item_id"])
    op.create_table(
        "audit_log",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("entity_type", sa.String(length=30), nullable=False),
        sa.Column("entity_id", sa.Integer(), nullable=False),
        sa.Column("action", sa.String(length=10), nullable=False),
        sa.Column("old_data", sa.Text(), nullable=True),
        sa.Column("new_data", sa.Text(), nullable=True),
        sa.Column("changed_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "action IN ('create', 'update', 'delete')", name=op.f("ck_audit_log_action")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_audit_log")),
    )
    op.create_index("ix_audit_log_entity", "audit_log", ["entity_type", "entity_id"])


def downgrade() -> None:
    op.drop_index("ix_audit_log_entity", table_name="audit_log")
    op.drop_table("audit_log")
    op.drop_index(op.f("ix_runs_item_id"), table_name="runs")
    op.drop_index(op.f("ix_runs_dungeon_id"), table_name="runs")
    op.drop_index(op.f("ix_runs_completed_at"), table_name="runs")
    op.drop_table("runs")
    op.drop_table("items")
    op.drop_table("dungeons")
