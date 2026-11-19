"""Tests de api.enviar_a_revision: motivos M01–M03, que n8n detecta antes de las reglas (04, sección 3.1)."""

import json

import psycopg
import pytest
from psycopg.types.json import Jsonb


def recibir(cur, message_id):
    cur.execute("select api.recibir_correo(%s, 'compras@talleresferran.example', 'Pedido', 'dmarc=pass',"
                " '2026-11-10 09:30+01', 'pruebas')", (message_id,))
    return cur.fetchone()[0]["caso"]


@pytest.fixture
def automatizacion(cur):
    cur.execute("set local role service_role")
    return cur


def test_un_xls_va_a_revision_con_m02(automatizacion, cur):
    caso = recibir(automatizacion, "<r1@pruebas.example>")
    automatizacion.execute("select api.enviar_a_revision(%s, 'M02', %s)",
                           (caso, Jsonb({"formatos": ["xls"], "adjuntos": ["pedido_ferran.xls"]})))
    resultado = automatizacion.fetchone()[0]
    assert resultado == {"caso": caso, "salida": "revision", "pedido": None,
                         "motivos": [{"codigo": "M02", "linea": None, "salida": "revision"}]}
    cur.execute("reset role")
    cur.execute("select estado from intake.casos where id = %s", (caso,))
    assert cur.fetchone()[0] == "en_revision"
    cur.execute("select codigo, salida, detalle from intake.motivos where caso = %s", (caso,))
    assert cur.fetchall() == [("M02", "revision", {"formatos": ["xls"], "adjuntos": ["pedido_ferran.xls"]})]


def test_el_evento_no_lleva_los_nombres_de_los_ficheros(automatizacion, cur):
    caso = recibir(automatizacion, "<r2@pruebas.example>")
    automatizacion.execute("select api.enviar_a_revision(%s, 'M02', %s)",
                           (caso, Jsonb({"adjuntos": ["pedido_ferran.xls"]})))
    cur.execute("reset role")
    cur.execute("select tipo, carga from intake.eventos where caso = %s order by id", (caso,))
    eventos = cur.fetchall()
    assert [t for t, _ in eventos] == ["recibido", "enviado_a_revision"]
    assert eventos[1][1] == {"codigo": "M02"} and "ferran" not in json.dumps(eventos[1][1])


@pytest.mark.parametrize("codigo", ["M01", "M03"])
def test_admite_m01_y_m03(automatizacion, codigo):
    caso = recibir(automatizacion, f"<r3-{codigo}@pruebas.example>")
    automatizacion.execute("select api.enviar_a_revision(%s, %s)", (caso, codigo))
    assert automatizacion.fetchone()[0]["motivos"][0]["codigo"] == codigo


@pytest.mark.parametrize("codigo", ["R11", "M04", "M05", "otro"])
def test_rechaza_los_motivos_que_no_son_suyos(automatizacion, codigo):
    caso = recibir(automatizacion, f"<r4-{codigo}@pruebas.example>")
    with pytest.raises(psycopg.errors.RaiseException, match="solo admite M01, M02 y M03"):
        automatizacion.execute("select api.enviar_a_revision(%s, %s)", (caso, codigo))


def test_no_toca_un_caso_en_estado_final(automatizacion, cur):
    caso = recibir(automatizacion, "<r5@pruebas.example>")
    cur.execute("reset role")
    cur.execute("update intake.casos set estado = 'pedido_creado' where id = %s", (caso,))
    with pytest.raises(psycopg.errors.RaiseException, match="estado final"):
        cur.execute("select intake.enviar_a_revision(%s, 'M03')", (caso,))


def test_un_caso_que_no_existe_se_rechaza(automatizacion):
    with pytest.raises(psycopg.errors.RaiseException, match="no existe"):
        automatizacion.execute("select api.enviar_a_revision(-1, 'M03')")
