"""Categorias padrão de itens: converte valores existentes e adiciona a restrição.

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-14
"""

import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

CATEGORY_CHECK = (
    "category IS NULL OR category IN ('weapons', 'armor', 'accessories', 'relics', "
    "'amplification_resources', 'crafting_resources', 'consumables', 'precious_bars')"
)

LEGACY_LABELS = {
    "weapons": ("armas", "arma"),
    "armor": ("armaduras", "armadura"),
    "accessories": ("acessórios", "acessorios", "acessório", "acessorio"),
    "relics": ("relíquias", "reliquias", "relíquia", "reliquia"),
    "amplification_resources": ("recursos de amplificação", "recursos de amplificacao"),
    "crafting_resources": ("recursos de artesanato",),
    "consumables": ("consumíveis", "consumiveis", "consumível", "consumivel"),
    "precious_bars": ("barras preciosas", "barra preciosa"),
}

NAME_COLUMN = sa.Column("name", sa.String(length=100, collation="NOCASE"), nullable=False)


def _items_batch():
    return op.batch_alter_table("items", recreate="always", reflect_args=[NAME_COLUMN])


def upgrade() -> None:
    items = sa.table("items", sa.column("category", sa.String))
    for slug, labels in LEGACY_LABELS.items():
        op.execute(
            items.update()
            .where(sa.func.lower(sa.func.trim(items.c.category)).in_(labels))
            .values(category=slug)
        )
    op.execute(
        items.update().where(items.c.category.not_in(list(LEGACY_LABELS))).values(category=None)
    )
    with _items_batch() as batch:
        batch.create_check_constraint(op.f("ck_items_category"), CATEGORY_CHECK)


def downgrade() -> None:
    with _items_batch() as batch:
        batch.drop_constraint(op.f("ck_items_category"), type_="check")
