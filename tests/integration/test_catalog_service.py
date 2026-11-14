"""Casos de uso de cadastro de masmorras e itens."""

import json

import pytest

from dungeon_drop_analyzer.models import ItemCategory
from dungeon_drop_analyzer.services import DuplicateError, NotFoundError, ValidationError


def test_cria_e_lista_masmorras_por_dificuldade(dungeons):
    dungeons.create("Difícil", 5)
    dungeons.create("Fácil", 1, description="  entrada  ")
    nomes = [d.name for d in dungeons.list()]
    assert nomes == ["Fácil", "Difícil"]
    assert dungeons.list()[0].description == "entrada"


@pytest.mark.parametrize("dificuldade", [0, 6, "3", 2.5, True, None])
def test_dificuldade_invalida(dungeons, dificuldade):
    with pytest.raises(ValidationError):
        dungeons.create("X", dificuldade)


@pytest.mark.parametrize("nome", ["", "   ", None, "a" * 101])
def test_nome_invalido(dungeons, items, nome):
    with pytest.raises(ValidationError):
        dungeons.create(nome, 1)
    with pytest.raises(ValidationError):
        items.create(nome)


def test_nome_duplicado_ignora_caixa_e_espacos(dungeons, items):
    dungeons.create("Caverna", 1)
    with pytest.raises(DuplicateError):
        dungeons.create("  caverna ", 2)
    items.create("Espada")
    with pytest.raises(DuplicateError):
        items.create("ESPADA")


def test_nome_duplicado_na_edicao_mas_nao_consigo_mesmo(dungeons):
    a = dungeons.create("A", 1)
    dungeons.create("B", 2)
    with pytest.raises(DuplicateError):
        dungeons.update(a.id, name="b")
    assert dungeons.update(a.id, name="a").name == "a"


def test_edita_e_inativa_masmorra(dungeons):
    d = dungeons.create("A", 1)
    editada = dungeons.update(d.id, name="A2", difficulty=3, description="nova")
    assert (editada.name, editada.difficulty, editada.description) == ("A2", 3, "nova")
    assert dungeons.set_active(d.id, False).is_active is False
    assert [x.name for x in dungeons.list(active_only=True)] == []
    assert len(dungeons.list()) == 1


def test_item_categoria_e_inativacao(items):
    i = items.create("Anel", category=" accessories ")
    assert i.category == "accessories"
    assert items.update(i.id, category=ItemCategory.RELICS).category == "relics"
    assert items.update(i.id, category="").category is None
    assert items.update(i.id, category=None).category is None
    items.set_active(i.id, False)
    assert items.get(i.id).is_active is False


def test_edicao_rejeita_campo_desconhecido_e_tipos_invalidos(dungeons):
    d = dungeons.create("A", 1)
    with pytest.raises(ValidationError):
        dungeons.update(d.id, id=99)
    with pytest.raises(ValidationError):
        dungeons.update(d.id, is_active="sim")
    with pytest.raises(NotFoundError):
        dungeons.update(999, name="Z")
    with pytest.raises(NotFoundError):
        dungeons.get(999)


def test_auditoria_de_criacao_e_atualizacao(dungeons, audit_trail):
    d = dungeons.create("A", 1)
    dungeons.update(d.id, difficulty=4)
    dungeons.update(d.id, difficulty=4)
    historico = audit_trail.history("dungeon", d.id)
    assert [h.action for h in historico] == ["create", "update"]
    assert json.loads(historico[0].new_data)["difficulty"] == 1
    assert json.loads(historico[1].old_data)["difficulty"] == 1
    assert json.loads(historico[1].new_data)["difficulty"] == 4
    assert historico[0].old_data is None


def test_atualizacao_sem_mudanca_nao_altera_updated_at(dungeons):
    d = dungeons.create("A", 1)
    assert dungeons.update(d.id, name="A").updated_at == d.updated_at


def test_todas_as_categorias_padrao_sao_aceitas(items):
    criados = [items.create(f"Item {c.value}", category=c) for c in ItemCategory]
    assert [i.category for i in criados] == [c.value for c in ItemCategory]
    assert [c.label for c in ItemCategory] == [
        "Armas",
        "Armaduras",
        "Acessórios",
        "Relíquias",
        "Recursos de amplificação",
        "Recursos de artesanato",
        "Consumíveis",
        "Barras preciosas",
    ]


@pytest.mark.parametrize("categoria", ["raro", "Armas", 3, ["weapons"]])
def test_categoria_fora_do_padrao_e_rejeitada(items, categoria):
    with pytest.raises(ValidationError, match="Categoria inválida"):
        items.create("X", category=categoria)
    existente = items.create("Y")
    with pytest.raises(ValidationError):
        items.update(existente.id, category=categoria)
    assert items.get(existente.id).category is None
