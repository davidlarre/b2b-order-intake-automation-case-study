"""Clasificación y R01 (04, secciones 2.2, 3.1 y 6.1). Se llaman como service_role, que es como entra n8n."""

import json

import psycopg
import pytest
from psycopg.types.json import Jsonb

from cargar_prompts import EXTRACTION, cargar, leer_prompt

ADV = {"sub": "00000000-0000-0000-0000-0000000000aa", "role": "authenticated", "app_metadata": {"rol": "adv"}}


@pytest.fixture
def hash_clasificacion(cur):
    return cargar(cur, EXTRACTION / "clasificacion", activar=True)["hash"]


def recibir(cur, message_id, remitente="compras@talleresferran.example"):
    cur.execute("select api.recibir_correo(%s, %s, 'Asunto', 'dmarc=pass', '2026-11-10 09:30+01', 'pruebas')",
                (message_id, remitente))
    return cur.fetchone()[0]["caso"]


def clasificar(cur, caso, h, tipo, destino="ninguno", configuracion="hibrido"):
    cur.execute("select api.registrar_clasificacion(%s, %s, %s, %s, 'modelo-prueba', 200, 10)",
                (caso, configuracion, Jsonb({"tipo": tipo, "destino": destino}), h))
    return cur.fetchone()[0]


def estado(cur, caso):
    cur.execute("reset role")
    cur.execute("select estado, tipo, cliente from intake.casos where id = %s", (caso,))
    return cur.fetchone()


def motivos(cur, caso):
    cur.execute("reset role")
    cur.execute("select codigo, detalle from intake.motivos where caso = %s and estado = 'abierto'", (caso,))
    return cur.fetchall()


@pytest.fixture
def automatizacion(cur, hash_clasificacion):
    cur.execute("set local role service_role")
    return cur


def test_el_esquema_tiene_los_cinco_tipos_y_dudoso():
    esquema = leer_prompt(EXTRACTION / "clasificacion")["esquema"]
    assert esquema["properties"]["tipo"]["enum"] == [
        "pedido_nuevo", "consulta", "reclamacion", "modificacion_anulacion", "otros", "dudoso"]


def test_un_pedido_sigue_hacia_la_extraccion(automatizacion, cur, hash_clasificacion):
    caso = recibir(automatizacion, "<c1@pruebas.example>")
    assert clasificar(automatizacion, caso, hash_clasificacion, "pedido_nuevo") == {
        "caso": caso, "tipo": "pedido_nuevo", "sigue": True}
    assert estado(cur, caso) == ("clasificado", "pedido_nuevo", None)
    cur.execute("select prompt, resultado ->> 'tipo', tokens_entrada from intake.extracciones where caso = %s", (caso,))
    assert cur.fetchall() == [("clasificacion", "pedido_nuevo", 200)]


@pytest.mark.parametrize("tipo", ["consulta", "reclamacion", "modificacion_anulacion"])
def test_lo_que_no_es_pedido_va_a_revision_con_r01(automatizacion, cur, hash_clasificacion, tipo):
    caso = recibir(automatizacion, "<c2@pruebas.example>")
    r = clasificar(automatizacion, caso, hash_clasificacion, tipo)
    assert r["sigue"] is False and r["salida"] == "revision" and r["pedido"] is None
    assert motivos(cur, caso) == [("R01", {"tipo": tipo})]
    assert estado(cur, caso)[:2] == ("en_revision", tipo)


def test_r01_corta_antes_que_r02(automatizacion, cur, hash_clasificacion):
    caso = recibir(automatizacion, "<c3@pruebas.example>", remitente="nadie@desconocido.example")
    clasificar(automatizacion, caso, hash_clasificacion, "consulta")
    assert [c for c, _ in motivos(cur, caso)] == ["R01"]


@pytest.mark.parametrize("destino", ["contabilidad", "archivo"])
def test_otros_se_deriva_y_queda_registrado(automatizacion, cur, hash_clasificacion, destino):
    caso = recibir(automatizacion, "<c4@pruebas.example>")
    r = clasificar(automatizacion, caso, hash_clasificacion, "otros", destino)
    assert r["salida"] == "derivado" and r["motivos"] == [] and r["sigue"] is False
    assert estado(cur, caso)[:2] == ("derivado", "otros")
    cur.execute("select tipo, carga from intake.eventos where caso = %s order by id", (caso,))
    eventos = cur.fetchall()
    assert [t for t, _ in eventos] == ["recibido", "clasificado", "derivado"] and eventos[2][1] == {"destino": destino}


@pytest.mark.parametrize("tipo, destino", [("dudoso", "ninguno"), ("dudoso", "archivo"), ("otros", "ninguno")])
def test_la_duda_va_a_una_persona_nunca_a_spam(automatizacion, cur, hash_clasificacion, tipo, destino):
    caso = recibir(automatizacion, "<c5@pruebas.example>")
    r = clasificar(automatizacion, caso, hash_clasificacion, tipo, destino)
    assert r["salida"] == "revision" and r["sigue"] is False
    assert motivos(cur, caso) == [("M01", {"tipo": "clasificacion_dudosa"})]
    assert estado(cur, caso)[0] == "en_revision"


@pytest.mark.parametrize("clasificacion", [
    {"tipo": "pedido", "destino": "ninguno"}, {"tipo": "pedido_nuevo"}, {"tipo": "otros", "destino": "papelera"}])
def test_una_clasificacion_que_no_cumple_el_esquema_se_rechaza(automatizacion, hash_clasificacion, clasificacion):
    caso = recibir(automatizacion, "<c6@pruebas.example>")
    with pytest.raises(psycopg.errors.RaiseException, match="no cumple el esquema"):
        automatizacion.execute("select api.registrar_clasificacion(%s, 'hibrido', %s, %s, 'm')",
                               (caso, Jsonb(clasificacion), hash_clasificacion))


def test_solo_reglas_no_clasifica(automatizacion, hash_clasificacion):
    caso = recibir(automatizacion, "<c7@pruebas.example>")
    with pytest.raises(psycopg.errors.RaiseException, match="no se usa en la configuración solo_reglas"):
        clasificar(automatizacion, caso, hash_clasificacion, "pedido_nuevo", configuracion="solo_reglas")


def test_el_hash_tiene_que_ser_del_prompt_de_clasificacion(automatizacion, cur, hash_clasificacion):
    cur.execute("reset role")
    otro = cargar(cur, EXTRACTION / "extraccion", activar=True)["hash"]
    caso = recibir(cur, "<c8@pruebas.example>")
    with pytest.raises(psycopg.errors.RaiseException, match="prompt de clasificación"):
        clasificar(cur, caso, otro, "pedido_nuevo")


def test_un_caso_no_se_clasifica_dos_veces(automatizacion, hash_clasificacion):
    caso = recibir(automatizacion, "<c9@pruebas.example>")
    clasificar(automatizacion, caso, hash_clasificacion, "pedido_nuevo")
    with pytest.raises(psycopg.errors.RaiseException, match="ya se ha clasificado"):
        clasificar(automatizacion, caso, hash_clasificacion, "consulta")


# ---------------------------------------------------------------- la app de revisión

def como_adv(cur):
    cur.execute("reset role")
    cur.execute("select set_config('request.jwt.claims', %s, true)", (json.dumps(ADV),))
    cur.execute("set local role authenticated")


def test_una_reclamacion_va_la_primera_de_la_cola(automatizacion, cur, hash_clasificacion):
    caso = recibir(automatizacion, "<c10@pruebas.example>")
    clasificar(automatizacion, caso, hash_clasificacion, "reclamacion")
    como_adv(cur)
    cur.execute("select adv.cola()")
    assert cur.fetchone()[0][0]["caso"] == caso


def test_r01_no_se_puede_forzar_ni_reevaluar_hasta_crear_un_pedido_vacio(automatizacion, cur, hash_clasificacion):
    caso = recibir(automatizacion, "<c11@pruebas.example>")
    clasificar(automatizacion, caso, hash_clasificacion, "consulta")
    como_adv(cur)
    cur.execute("select adv.reevaluar(%s)", (caso,))
    assert cur.fetchone()[0]["salida"] == "revision"
    with pytest.raises(psycopg.errors.RaiseException, match="R01 no se puede forzar"):
        cur.execute("select adv.crear_pedido(%s, %s)", (caso, Jsonb([{"codigo": "R01", "linea": None, "razon": "otra"}])))


def test_cierre_segun_el_tipo(automatizacion, cur, hash_clasificacion):
    caso = recibir(automatizacion, "<c12@pruebas.example>")
    clasificar(automatizacion, caso, hash_clasificacion, "consulta")
    como_adv(cur)
    cur.execute("savepoint s")
    with pytest.raises(psycopg.errors.RaiseException, match="no corresponde al tipo"):
        cur.execute("select adv.cerrar_caso(%s, 'reclamación atendida')", (caso,))
    cur.execute("rollback to savepoint s")
    cur.execute("select adv.cerrar_caso(%s, 'consulta atendida')", (caso,))
    assert cur.fetchone()[0]["resultado"] == "consulta atendida"
