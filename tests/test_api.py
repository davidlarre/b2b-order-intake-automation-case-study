"""Tests de la puerta de la automatización: el esquema api.

Se llaman como service_role, que es como entrará n8n. Solo se ejecutan funciones con permiso;
los permisos que faltan se comprueban en el catálogo (ver tests/test_entorno_supautils.py).
"""

import json
import re
from decimal import Decimal

import psycopg
import pytest
from psycopg.types.json import Jsonb

HORA = "2026-11-10 09:30+01"


def json_exacto(obj):
    """Serializa Decimal como número JSON con su texto exacto (0.0921), sin pasar por float."""
    texto = json.dumps(obj, default=lambda d: f"@@{d}@@")
    return re.sub(r'"@@(-?[0-9.]+)@@"', r"\1", texto)


def recibir(cur, message_id, remitente="compras@talleresferran.example", autenticacion="dmarc=pass"):
    cur.execute("select api.recibir_correo(%s, %s, %s, %s, %s, 'pruebas')",
                (message_id, remitente, "Pedido", autenticacion, HORA))
    return cur.fetchone()[0]


def registrar(cur, caso, lineas, prompt_hash):
    extraccion = Jsonb({"num_pedido_cliente": None, "lineas": lineas}, dumps=json_exacto)
    cur.execute("select api.registrar_extraccion(%s, %s, %s, 'modelo-prueba', 'solo_ia', 100, 50)",
                (caso, extraccion, prompt_hash))
    return cur.fetchone()[0]


@pytest.fixture
def automatizacion(cur, prompt_hash):
    # La versión del prompt se carga antes de cambiar de rol: service_role no toca tablas.
    cur.execute("set local role service_role")
    return cur


def test_recibir_correo_crea_el_caso_en_recibido(automatizacion, cur):
    resultado = recibir(automatizacion, "<a1@pruebas.example>")
    assert resultado["duplicado"] is False
    cur.execute("reset role")
    cur.execute("select estado, origen from intake.casos where id = %s", (resultado["caso"],))
    assert cur.fetchone() == ("recibido", "pruebas")
    cur.execute("select tipo from intake.eventos where caso = %s", (resultado["caso"],))
    assert cur.fetchall() == [("recibido",)]


def test_el_mismo_message_id_no_crea_otro_caso(automatizacion):
    primero = recibir(automatizacion, "<a2@pruebas.example>")
    segundo = recibir(automatizacion, "<a2@pruebas.example>")
    assert segundo == {"caso": primero["caso"], "duplicado": True}


def test_de_punta_a_punta_un_pedido_limpio_sale_automatico(automatizacion, cur, prompt_hash):
    caso = recibir(automatizacion, "<a3@pruebas.example>")["caso"]
    resultado = registrar(automatizacion, caso, [
        {"texto": "TOR-M8X30-ZN 500 uds", "referencia": "TOR-M8X30-ZN", "cantidad": 500, "unidad": "uds", "precio": None},
        {"texto": "arandela ARAND 8 x500", "referencia": "ARAND 8", "cantidad": 500, "unidad": None, "precio": None},
    ], prompt_hash)
    assert resultado["salida"] == "automatico" and resultado["pedido"] is not None
    cur.execute("reset role")
    cur.execute("select sum(cantidad * precio_unitario) from erp.lineas_pedido where pedido = %s",
                (resultado["pedido"],))
    assert cur.fetchone()[0] == 500 * Decimal("0.0820") + 500 * Decimal("0.0100")
    cur.execute("select tipo from intake.eventos where caso = %s order by id", (caso,))
    assert [t for (t,) in cur.fetchall()] == ["recibido", "extraido", "reglas_evaluadas"]


def test_el_precio_de_la_extraccion_llega_exacto(automatizacion, cur, prompt_hash):
    caso = recibir(automatizacion, "<a4@pruebas.example>")["caso"]
    resultado = registrar(automatizacion, caso, [
        {"texto": "TOR-M8X30-ZN 500 a 0,0921", "referencia": "TOR-M8X30-ZN", "cantidad": 500,
         "unidad": "uds", "precio": Decimal("0.0921")},
    ], prompt_hash)
    assert resultado["salida"] == "revision"
    cur.execute("reset role")
    cur.execute("select precio from intake.lineas_caso where caso = %s", (caso,))
    assert cur.fetchone()[0] == Decimal("0.0921")


@pytest.mark.parametrize("lineas", [
    [],
    [{"texto": "algo", "cantidad": 5}],                           # sin referencia
    [{"texto": "algo", "referencia": "X", "cantidad": "cinco"}],  # cantidad que no es un número
])
def test_una_extraccion_no_valida_no_deja_nada_a_medias(automatizacion, cur, lineas, prompt_hash):
    caso = recibir(automatizacion, "<a5@pruebas.example>")["caso"]
    automatizacion.execute("savepoint antes")
    with pytest.raises(psycopg.errors.RaiseException, match="Extracción no válida"):
        registrar(automatizacion, caso, lineas, prompt_hash)
    automatizacion.execute("rollback to savepoint antes")
    cur.execute("reset role")
    cur.execute("select estado, (select count(*) from intake.extracciones where caso = c.id)"
                " from intake.casos c where id = %s", (caso,))
    assert cur.fetchone() == ("recibido", 0)


def test_api_expone_solo_sus_funciones_y_solo_a_la_automatizacion(cur):
    cur.execute("select p.oid::regprocedure::text from pg_proc p join pg_namespace n on n.oid = p.pronamespace"
                " where n.nspname = 'api' order by 1")
    funciones = [f for (f,) in cur.fetchall()]
    assert [f.split("(")[0] for f in funciones] == ["api.enviar_a_revision", "api.prompt_activo", "api.recibir_correo", "api.registrar_extraccion"]
    for rol, esperado in (("service_role", True), ("anon", False), ("authenticated", False)):
        cur.execute("select has_schema_privilege(%s, 'api', 'usage')", (rol,))
        assert cur.fetchone()[0] is esperado
        for f in funciones:
            cur.execute("select has_function_privilege(%s, %s, 'execute')", (rol, f))
            assert cur.fetchone()[0] is esperado, (rol, f)
