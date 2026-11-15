"""Categoria de item obrigatória (NOT NULL) e restrição sem valores nulos.

Revision ID: 0003
Revises: 0002
Create Date: 2026-11-14
"""

import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None

VALUES = (
    "'weapons', 'armor', 'accessories', 'relics', 'amplification_resources', "
    "'crafting_resources', 'consumables', 'precious_bars'"
)
REQUIRED_CHECK = f"category IN ({VALUES})"
OPTIONAL_CHECK = f"category IS NULL OR category IN ({VALUES})"

NAME_COLUMN = sa.Column("name", sa.String(length=100, collation="NOCASE"), nullable=False)


def _items_batch():
    return op.batch_alter_table("items", recreate="always", reflect_args=[NAME_COLUMN])


def upgrade() -> None:
    rows = op.get_bind().execute(
        sa.text("SELECT name FROM items WHERE category IS NULL ORDER BY name")
    )
    missing = [row[0] for row in rows]
    if missing:
        listed = ", ".join(missing)
        raise RuntimeError(
            f"Existem itens sem categoria: {listed}. Atribua uma categoria a eles e execute "
            "a atualização novamente."
        )
    with _items_batch() as batch:
        batch.drop_constraint(op.f("ck_items_category"), type_="check")
        batch.alter_column("category", existing_type=sa.String(length=100), nullable=False)
        batch.create_check_constraint(op.f("ck_items_category"), REQUIRED_CHECK)


def downgrade() -> None:
    with _items_batch() as batch:
        batch.drop_constraint(op.f("ck_items_category"), type_="check")
        batch.alter_column("category", existing_type=sa.String(length=100), nullable=True)
        batch.create_check_constraint(op.f("ck_items_category"), OPTIONAL_CHECK)
