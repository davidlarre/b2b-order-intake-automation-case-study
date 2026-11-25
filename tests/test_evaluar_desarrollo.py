"""La nota de evaluar_desarrollo.py, y las etiquetas de desarrollo contra las reglas SQL construidas (05, sección 7).

Solo desarrollo: con la prueba no se ejecuta nada, ni siquiera las reglas.
"""

import email
import email.policy
from collections import Counter

import pytest
import yaml
from psycopg.types.json import Jsonb

import generar_correos as g
from evaluar_desarrollo import DESARROLLO, nota

ETIQUETAS = {p.stem: yaml.safe_load(p.read_text()) for p in sorted((DESARROLLO / "etiquetas").glob("*.yaml"))}
FICHAS = g.leer_fichas("desarrollo")


def resultado(salida, *codigos, pedido=None):
    return {"salida": salida, "motivos": [{"codigo": c} for c in codigos], "pedido": pedido}


def test_todo_correcto():
    lineas = Counter({("TOR-M6X20-ZN", 1500): 1, ("TUE-M6-ZN", 1500): 1, ("ARA-M6-ZN", 2000): 1})
    assert nota(ETIQUETAS["D01"], resultado("automatico", pedido=1), "pedido_nuevo", lineas) == ("OK", "OK", [])


def test_un_pedido_automatico_con_otra_cantidad_es_fallo():
    lineas = Counter({("TOR-M6X20-ZN", 1): 1, ("TUE-M6-ZN", 1500): 1, ("ARA-M6-ZN", 2000): 1})
    assert nota(ETIQUETAS["D01"], resultado("automatico", pedido=1), "pedido_nuevo", lineas)[1] == "FALLO"


def test_dudoso_es_aceptable_en_una_consulta_y_no_en_una_reclamacion():
    r = resultado("revision", "M01")
    assert nota(ETIQUETAS["D17"], r, "dudoso", Counter())[:2] == ("ACEPTABLE", "ACEPTABLE")
    assert nota(ETIQUETAS["D19"], r, "dudoso", Counter())[:2] == ("FALLO", "FALLO")


def test_m03_va_aparte():
    assert nota(ETIQUETAS["D17"], resultado("revision", "M03"), None, Counter()) == ("M03", "M03", [])


def test_sin_codigo_no_compara_motivos():
    assert nota(ETIQUETAS["D05"], resultado("revision", "R12"), "pedido_nuevo", Counter())[1] == "OK"


@pytest.mark.parametrize("caso", [i for i, e in ETIQUETAS.items() if e["lineas"] and FICHAS[i]["formato"] != "reenvio"])
def test_las_reglas_sql_dan_lo_etiquetado(cur, prompt_hash, caso):
    """Las líneas correctas, pasadas por las reglas construidas, dan los motivos etiquetados de esas reglas."""
    e, f = ETIQUETAS[caso], FICHAS[caso]
    mensaje = email.message_from_bytes((DESARROLLO / "correos" / e["eml"][0]).read_bytes(), policy=email.policy.default)
    lineas = [{"texto": l["texto"], "referencia": x.get("ref", x["producto"]), "cantidad": l["cantidad"], "unidad": l["unidad"],
               "precio": l["precio_pedido"]} for l, x in zip(e["lineas"], f["lineas"])]
    cur.execute("select api.recibir_correo(%s, %s, 'x', %s, %s, 'pruebas')",
                (f"<sql-{caso}@pruebas.example>", mensaje["From"].addresses[0].addr_spec,
                 mensaje["Authentication-Results"], mensaje["Date"].datetime))
    n = cur.fetchone()[0]["caso"]
    cur.execute("select api.registrar_extraccion(caso => %s, configuracion => 'solo_ia', extraccion_ia => %s,"
                " prompt_hash => %s, modelo => 'm')",
                (n, Jsonb({"num_pedido_cliente": None, "lineas": lineas}), prompt_hash))
    r = cur.fetchone()[0]
    construidas = {"R02", "R08", "R11"}
    assert {(m["codigo"], m["linea"]) for m in r["motivos"]} == {
        (m["codigo"], m["linea"]) for m in e["motivos"] if m["codigo"] in construidas}
