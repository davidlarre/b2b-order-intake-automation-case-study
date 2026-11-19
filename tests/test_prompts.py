"""Tests del prompt versionado (ADR 0002): carga desde extraction/, versión activa y validación del esquema."""

import json
import shutil

import psycopg
import pytest
from psycopg.types.json import Jsonb

from cargar_prompts import EXTRACTION, cargar, hash_de, leer_prompt

CARPETA = EXTRACTION / "extraccion"


# ---------------------------------------------------------------- ficheros y hash (sin base de datos)

def test_el_prompt_del_fichero_es_el_mismo_texto_que_recibia_el_nodo():
    texto = leer_prompt(CARPETA)["texto"]
    assert texto.startswith("Eres el extractor de pedidos de Orvalle Suministros Industriales.\n")
    assert texto.endswith("\n<<<\n{correo}\n>>>")  # sin salto de línea final


def test_el_hash_cambia_con_cualquiera_de_las_cuatro_partes():
    base = leer_prompt(CARPETA)
    h = hash_de(base)
    assert hash_de(dict(base)) == h
    for campo, valor in (("texto", base["texto"] + " "), ("esquema", {**base["esquema"], "x": 1}),
                         ("ejemplos", [{"correo": "a"}]), ("modelo", "otro-modelo")):
        assert hash_de({**base, campo: valor}) != h, campo


def test_un_prompt_sin_la_marca_del_correo_no_se_carga(tmp_path):
    carpeta = tmp_path / "extraccion"
    shutil.copytree(CARPETA, carpeta)
    (carpeta / "prompt.md").write_text("Sin marca\n")
    with pytest.raises(ValueError, match="correo"):
        leer_prompt(carpeta)


# ---------------------------------------------------------------- carga y activación

def test_cargar_dos_veces_no_crea_otra_version(cur):
    primera = cargar(cur, CARPETA, activar=False)
    segunda = cargar(cur, CARPETA, activar=False)
    assert segunda["nueva"] is False and segunda["version"] == primera["version"]


def test_activar_una_version_nueva_desactiva_la_anterior(cur, tmp_path):
    anterior = cargar(cur, CARPETA, activar=True)
    carpeta = tmp_path / "extraccion"
    shutil.copytree(CARPETA, carpeta)
    (carpeta / "ejemplos.json").write_text(json.dumps([{"correo": "ejemplo"}]))
    nueva = cargar(cur, carpeta, activar=True)
    assert nueva["version"] == anterior["version"] + 1
    cur.execute("select version from intake.prompt_versiones where prompt = 'extraccion' and activa")
    assert cur.fetchall() == [(nueva["version"],)]


def test_la_automatizacion_lee_la_version_activa(cur, prompt_hash):
    cur.execute("set local role service_role")
    cur.execute("select api.prompt_activo('extraccion')")
    activa = cur.fetchone()[0]
    fichero = leer_prompt(CARPETA)
    assert activa["hash"] == prompt_hash
    assert (activa["texto"], activa["esquema"], activa["modelo"]) == (fichero["texto"], fichero["esquema"], fichero["modelo"])


# ---------------------------------------------------------------- registrar_extraccion con versión

def _caso(cur):
    cur.execute("select api.recibir_correo(%s, 'compras@talleresferran.example', 'Pedido', 'dmarc=pass',"
                " '2026-11-10 09:30+01', 'pruebas')", ("<p-%s@pruebas.example>" % id(cur),))
    return cur.fetchone()[0]["caso"]


LINEA = {"texto": "TOR-M8X30-ZN 500 uds", "referencia": "TOR-M8X30-ZN", "cantidad": 500, "unidad": "uds", "precio": None}


def test_la_extraccion_queda_enlazada_a_su_version(cur, prompt_hash):
    cur.execute("set local role service_role")
    caso = _caso(cur)
    cur.execute("select api.registrar_extraccion(caso => %s, configuracion => 'solo_ia', extraccion_ia => %s,"
                " prompt_hash => %s, modelo => 'gemini-3.5-flash-lite')",
                (caso, Jsonb({"num_pedido_cliente": None, "lineas": [LINEA]}), prompt_hash))
    cur.execute("reset role")
    cur.execute("select v.hash, x.version from intake.extracciones x"
                " join intake.prompt_versiones v on v.id = x.prompt_version_id where x.caso = %s", (caso,))
    h, version = cur.fetchone()
    assert h == prompt_hash and version.isdigit()


def test_un_hash_desconocido_se_rechaza(cur, prompt_hash):
    cur.execute("set local role service_role")
    caso = _caso(cur)
    with pytest.raises(psycopg.errors.RaiseException, match="No existe ninguna versión"):
        cur.execute("select api.registrar_extraccion(caso => %s, configuracion => 'solo_ia', extraccion_ia => %s,"
                    " prompt_hash => %s, modelo => 'm')",
                    (caso, Jsonb({"num_pedido_cliente": None, "lineas": [LINEA]}), "0" * 64))


@pytest.mark.parametrize("extraccion", [
    {"lineas": [LINEA]},                                           # falta num_pedido_cliente
    {"num_pedido_cliente": None, "lineas": [{**LINEA, "precio": "0,10"}]},  # precio como texto
    {"num_pedido_cliente": 7, "lineas": [LINEA]},                  # número de pedido que no es texto
])
def test_pg_jsonschema_rechaza_lo_que_no_cumple_el_esquema(cur, prompt_hash, extraccion):
    cur.execute("set local role service_role")
    caso = _caso(cur)
    with pytest.raises(psycopg.errors.RaiseException, match="no cumple el esquema"):
        cur.execute("select api.registrar_extraccion(caso => %s, configuracion => 'solo_ia', extraccion_ia => %s,"
                    " prompt_hash => %s, modelo => 'm')", (caso, Jsonb(extraccion), prompt_hash))
