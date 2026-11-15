"""Autoverificação e linha de comando (dados SINTÉTICOS em diretório temporário)."""

import json

import pytest

import dungeon_drop_analyzer
from dungeon_drop_analyzer import selfcheck
from dungeon_drop_analyzer.main import build_parser, main


def test_versao_na_linha_de_comando(capsys):
    assert main(["--version"]) == 0
    assert dungeon_drop_analyzer.__version__ in capsys.readouterr().out


def test_parser_ignora_argumentos_do_qt():
    args, restantes = build_parser().parse_known_args(["--self-check", "-platform", "offscreen"])
    assert args.self_check is True and restantes == ["-platform", "offscreen"]


def test_autoverificacao_completa_passa_e_grava_relatorio(tmp_path, monkeypatch):
    monkeypatch.setenv("DDA_DATA_DIR", str(tmp_path / "nao_deve_ser_usado"))
    saida = tmp_path / "resultado" / "check.json"
    assert main(["--self-check", "--output", str(saida)]) == 0
    relatorio = json.loads(saida.read_text(encoding="utf-8"))
    assert relatorio["ok"] is True and relatorio["frozen"] is False
    assert [passo["name"] for passo in relatorio["steps"]] == [n for n, _ in selfcheck.STEPS]
    assert all(passo["ok"] for passo in relatorio["steps"])
    assert not (tmp_path / "nao_deve_ser_usado").exists()


def test_autoverificacao_falha_com_codigo_um_e_detalhe(tmp_path, monkeypatch):
    def quebrado(context):
        raise RuntimeError("falha simulada")

    monkeypatch.setattr(
        selfcheck, "STEPS", (selfcheck.STEPS[0], ("quebrado", quebrado), selfcheck.STEPS[1])
    )
    saida = tmp_path / "falha.json"
    assert selfcheck.run_self_check(saida) == 1
    relatorio = json.loads(saida.read_text(encoding="utf-8"))
    assert relatorio["ok"] is False
    assert [p["name"] for p in relatorio["steps"]] == ["bibliotecas", "quebrado"]
    assert "falha simulada" in relatorio["steps"][-1]["detail"]
    assert "traceback" in relatorio["steps"][-1]


@pytest.mark.parametrize("modulo", selfcheck.REQUIRED_MODULES)
def test_bibliotecas_obrigatorias_importam(modulo):
    __import__(modulo)
