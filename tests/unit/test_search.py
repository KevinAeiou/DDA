"""Busca sem acentos, maiúsculas e espaços."""

import pytest

from dungeon_drop_analyzer.ui.widgets.search import matches_search, normalize_search


@pytest.mark.parametrize(
    ("texto", "esperado"),
    [
        ("Reino da Aranha", "reinodaaranha"),
        ("  Mercenário ", "mercenario"),
        ("Poção de Proteção do Neófito", "pocaodeprotecaodoneofito"),
        ("Ação\tÇedilha\nÜ", "acaocedilhau"),
        ("", ""),
    ],
)
def test_normaliza_acentos_espacos_e_caixa(texto, esperado):
    assert normalize_search(texto) == esperado


def test_busca_encontra_por_trecho_sem_acento_ou_espaco():
    assert matches_search("reinoda", "Reino da Aranha")
    assert matches_search("Reino da", "Reino da Aranha")
    assert matches_search("mercenario", "Capa do Mercenário")
    assert matches_search("MERCENÁRIO", "capa do mercenario")
    assert matches_search("minasabandonadas", "Minas Abandonadas")
    assert not matches_search("serpente", "Reino da Aranha")


def test_busca_vazia_aceita_tudo():
    assert matches_search("", "Qualquer")
    assert matches_search("   ", "Qualquer")
