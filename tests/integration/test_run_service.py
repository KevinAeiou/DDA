"""Registro, histórico, correção e exclusão de incursões."""

import json
from datetime import UTC, datetime, timedelta, timezone

import pytest
from sqlalchemy import func, select

from dungeon_drop_analyzer.core.database import session_scope
from dungeon_drop_analyzer.models import AuditLog, Run
from dungeon_drop_analyzer.repositories import RunFilter
from dungeon_drop_analyzer.services import NotFoundError, ValidationError


def t(dia, hora=0):
    return datetime(2026, 3, dia, hora, tzinfo=UTC)


def total_runs(factory):
    with session_scope(factory) as s:
        return s.scalar(select(func.count(Run.id)))


def total_audit(factory):
    with session_scope(factory) as s:
        return s.scalar(select(func.count(AuditLog.id)))


def test_registra_incursao_com_valores_padrao(runs, seeded, clock):
    d, i = seeded[0][0], seeded[1][0]
    run = runs.register(d.id, i.id)
    assert run.completed_at.tzinfo is not None
    assert (run.bonus_status, run.event_status) == ("unknown", "unknown")
    assert run.dungeon.name == d.name and run.item.name == i.name
    assert runs.count() == 1


def test_registra_com_todos_os_campos(runs, seeded):
    d, i = seeded[0][2], seeded[1][1]
    run = runs.register(
        d.id,
        i.id,
        completed_at=t(5, 10),
        duration_seconds=0,
        game_version=" 1.2 ",
        bonus_status="yes",
        event_status="no",
        notes="  obs  ",
    )
    carregada = runs.get(run.id)
    assert carregada.completed_at == t(5, 10)
    assert (carregada.duration_seconds, carregada.game_version, carregada.notes) == (
        0,
        "1.2",
        "obs",
    )
    assert (carregada.bonus_status, carregada.event_status) == ("yes", "no")


def test_data_sem_fuso_e_convertida_de_local_para_utc(runs, seeded):
    d, i = seeded[0][0], seeded[1][0]
    ingenua = datetime(2026, 3, 5, 10, 0)
    run = runs.register(d.id, i.id, completed_at=ingenua)
    assert run.completed_at == ingenua.astimezone().astimezone(UTC)


def test_data_com_fuso_e_normalizada_para_utc(runs, seeded):
    d, i = seeded[0][0], seeded[1][0]
    br = timezone(timedelta(hours=-3))
    run = runs.register(d.id, i.id, completed_at=datetime(2026, 3, 5, 10, tzinfo=br))
    assert runs.get(run.id).completed_at == t(5, 13)


@pytest.mark.parametrize(
    "extra",
    [
        {"duration_seconds": -1},
        {"duration_seconds": 1.5},
        {"duration_seconds": True},
        {"bonus_status": "talvez"},
        {"event_status": None},
        {"completed_at": "2026-01-01"},
        {"game_version": "v" * 101},
    ],
)
def test_validacoes_de_registro_nao_gravam_nada(runs, seeded, factory, extra):
    d, i = seeded[0][0], seeded[1][0]
    with pytest.raises(ValidationError):
        runs.register(d.id, i.id, **extra)
    assert total_runs(factory) == 0


def test_exige_exatamente_um_item(runs, seeded, factory):
    d, items = seeded[0][0], seeded[1]
    with pytest.raises(ValidationError):
        runs.register(d.id, [items[0].id, items[1].id])
    with pytest.raises(ValidationError):
        runs.register(d.id, None)
    assert total_runs(factory) == 0


def test_masmorra_ou_item_inexistente_ou_inativo(runs, seeded, dungeons, items, factory):
    (d, *_), (i, *_) = seeded
    with pytest.raises(NotFoundError):
        runs.register(999, i.id)
    with pytest.raises(NotFoundError):
        runs.register(d.id, 999)
    dungeons.set_active(d.id, False)
    with pytest.raises(ValidationError):
        runs.register(d.id, i.id)
    dungeons.set_active(d.id, True)
    items.set_active(i.id, False)
    with pytest.raises(ValidationError):
        runs.register(d.id, i.id)
    assert total_runs(factory) == 0


def test_item_inativado_permanece_no_historico(runs, seeded, items):
    (d, *_), (i, *_) = seeded
    run = runs.register(d.id, i.id)
    items.set_active(i.id, False)
    assert runs.get(run.id).item.name == i.name
    assert runs.count() == 1


def test_transacao_atomica_falha_nao_deixa_run_nem_auditoria(runs, seeded, factory, monkeypatch):
    d, i = seeded[0][0], seeded[1][0]
    antes = total_audit(factory)
    from dungeon_drop_analyzer.services import runs as modulo

    def falha(*args, **kwargs):
        raise RuntimeError("falha simulada")

    monkeypatch.setattr(modulo.audit, "record", falha)
    with pytest.raises(RuntimeError):
        runs.register(d.id, i.id)
    assert total_runs(factory) == 0
    assert total_audit(factory) == antes


@pytest.fixture
def historico(runs, seeded):
    ds, its = seeded
    dados = [
        (ds[0], its[0], t(1), "yes", "no", "1.0"),
        (ds[0], its[1], t(2), "no", "no", "1.0"),
        (ds[1], its[0], t(3), "no", "yes", "1.1"),
        (ds[2], its[2], t(4), "unknown", "unknown", "1.1"),
        (ds[4], its[0], t(5), "no", "no", None),
    ]
    for d, i, quando, bonus, evento, versao in dados:
        runs.register(
            d.id,
            i.id,
            completed_at=quando,
            bonus_status=bonus,
            event_status=evento,
            game_version=versao,
        )
    return ds, its


def dias(lista):
    return [r.completed_at.day for r in lista]


def test_listagem_ordenada_e_paginada(runs, historico):
    assert dias(runs.list()) == [5, 4, 3, 2, 1]
    assert dias(runs.list(descending=False)) == [1, 2, 3, 4, 5]
    assert dias(runs.list(descending=False, limit=2, offset=1)) == [2, 3]
    assert runs.count() == 5


def test_filtros(runs, historico):
    ds, its = historico
    assert dias(runs.list(RunFilter(date_from=t(2), date_to=t(4)), descending=False)) == [2, 3, 4]
    assert dias(runs.list(RunFilter(dungeon_ids=[ds[0].id]), descending=False)) == [1, 2]
    assert dias(runs.list(RunFilter(item_ids=[its[0].id]), descending=False)) == [1, 3, 5]
    assert dias(runs.list(RunFilter(difficulties=[1, 5]), descending=False)) == [1, 2, 5]
    assert dias(runs.list(RunFilter(bonus_status="yes"))) == [1]
    assert dias(runs.list(RunFilter(event_status="yes"))) == [3]
    assert dias(runs.list(RunFilter(game_version="1.1"), descending=False)) == [3, 4]


def test_filtros_combinados_e_vazios(runs, historico):
    ds, its = historico
    flt = RunFilter(item_ids=[its[0].id], bonus_status="no", date_from=t(2))
    assert dias(
        runs.list(flt),
    ) == [5, 3]
    assert runs.count(flt) == 2
    assert runs.list(RunFilter(dungeon_ids=[])) == []
    assert runs.count(RunFilter(game_version="9.9")) == 0


def test_correcao_gera_auditoria_com_antes_e_depois(runs, seeded, audit_trail):
    (d1, d2, *_), (i1, i2, _) = seeded
    run = runs.register(d1.id, i1.id, completed_at=t(1), notes="a")
    corrigida = runs.update(run.id, dungeon_id=d2.id, item_id=i2.id, notes="b", duration_seconds=30)
    assert (corrigida.dungeon.id, corrigida.item.id) == (d2.id, i2.id)
    hist = audit_trail.history("run", run.id)
    assert [h.action for h in hist] == ["create", "update"]
    antigo, novo = json.loads(hist[1].old_data), json.loads(hist[1].new_data)
    assert (antigo["dungeon_id"], novo["dungeon_id"]) == (d1.id, d2.id)
    assert (antigo["notes"], novo["notes"]) == ("a", "b")
    assert novo["duration_seconds"] == 30


def test_correcao_sem_mudanca_e_invalida_nao_auditam(runs, seeded, audit_trail, items):
    (d, *_), (i1, i2, _) = seeded
    run = runs.register(d.id, i1.id)
    runs.update(run.id, notes=None)
    with pytest.raises(ValidationError):
        runs.update(run.id, duration_seconds=-5)
    with pytest.raises(ValidationError):
        runs.update(run.id, id=2)
    items.set_active(i2.id, False)
    with pytest.raises(ValidationError):
        runs.update(run.id, item_id=i2.id)
    assert runs.get(run.id).item.id == i1.id
    assert [h.action for h in audit_trail.history("run", run.id)] == ["create"]
    with pytest.raises(NotFoundError):
        runs.update(999, notes="x")


def test_correcao_mantem_item_inativo_quando_nao_alterado(runs, seeded, items):
    (d, *_), (i, *_) = seeded
    run = runs.register(d.id, i.id)
    items.set_active(i.id, False)
    assert runs.update(run.id, notes="ajuste").notes == "ajuste"


def test_exclusao_audita_e_remove(runs, seeded, audit_trail, factory):
    (d, *_), (i, *_) = seeded
    run = runs.register(d.id, i.id, notes="x")
    runs.delete(run.id)
    assert runs.count() == 0
    hist = audit_trail.history("run", run.id)
    assert [h.action for h in hist] == ["create", "delete"]
    assert json.loads(hist[1].old_data)["notes"] == "x" and hist[1].new_data is None
    with pytest.raises(NotFoundError):
        runs.delete(run.id)
    with pytest.raises(NotFoundError):
        runs.get(run.id)
