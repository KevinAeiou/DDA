"""Nome de item único apenas dentro da mesma categoria (restrição nome + categoria).

Revision ID: 0005
Revises: 0004
Create Date: 2026-11-20
"""

import sqlalchemy as sa
from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None

NAME_COLUMN = sa.Column("name", sa.String(length=100, collation="NOCASE"), nullable=False)


def _items_batch():
    return op.batch_alter_table("items", recreate="always", reflect_args=[NAME_COLUMN])


def upgrade() -> None:
    with _items_batch() as batch:
        batch.drop_constraint(op.f("uq_items_name"), type_="unique")
        batch.create_unique_constraint(op.f("uq_items_name_category"), ["name", "category"])


def downgrade() -> None:
    rows = op.get_bind().execute(
        sa.text(
            "SELECT name FROM items GROUP BY name COLLATE NOCASE HAVING COUNT(*) > 1 ORDER BY name"
        )
    )
    repeated = [row[0] for row in rows]
    if repeated:
        listed = ", ".join(repeated)
        raise RuntimeError(
            f"Existem itens com o mesmo nome em categorias diferentes: {listed}. Renomeie-os "
            "antes de reverter a migração."
        )
    with _items_batch() as batch:
        batch.drop_constraint(op.f("uq_items_name_category"), type_="unique")
        batch.create_unique_constraint(op.f("uq_items_name"), ["name"])
