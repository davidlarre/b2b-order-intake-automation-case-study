"""Tests de las tres configuraciones (04, sección 6.3) y de R12 (sección 3.2).

Se llaman como service_role con api.registrar_extraccion, como lo hará n8n.
"""

import psycopg
import pytest
from psycopg.types.json import Jsonb


def linea(referencia, cantidad, texto=None, precio=None):
    return {"texto": texto or f"{referencia} {cantidad} uds", "referencia": referencia, "cantidad": cantidad,
            "unidad": "uds", "precio": precio}


@pytest.fixture
def automatizacion(cur, prompt_hash):
    cur.execute("set local role service_role")
    return cur


def registrar(cur, prompt_hash, configuracion, ia=None, det=None, mid="<c@pruebas.example>"):
    cur.execute("select api.recibir_correo(%s, 'compras@talleresferran.example', 'Pedido', 'dmarc=pass',"
                " '2026-11-10 09:30+01', 'pruebas')", (mid,))
    caso = cur.fetchone()[0]["caso"]
    cur.execute(
        "select api.registrar_extraccion(caso => %s, configuracion => %s,"
        " extraccion_ia => %s, prompt_hash => %s, modelo => %s,"
        " extraccion_determinista => %s, version_determinista => %s)",
        (caso, configuracion,
         Jsonb({"num_pedido_cliente": None, "lineas": ia}) if ia is not None else None,
         prompt_hash if ia is not None else None, "modelo-prueba" if ia is not None else None,
         Jsonb({"lineas": det}) if det is not None else None, "0.1.0" if det is not None else None),
    )
    return caso, cur.fetchone()[0]


def lineas_caso(cur, caso):
    cur.execute("reset role")
    cur.execute("select referencia, cantidad::int, fuente, referencia_determinista, cantidad_determinista::int"
                " from intake.lineas_caso where caso = %s order by linea", (caso,))
    return cur.fetchall()


def motivos(cur, caso):
    cur.execute("reset role")
    cur.execute("select codigo, linea, detalle from intake.motivos where caso = %s and estado = 'abierto'"
                " order by codigo, linea", (caso,))
    return cur.fetchall()


# ---------------------------------------------------------------- solo reglas

def test_solo_reglas_usa_las_lineas_del_determinista(automatizacion, prompt_hash):
    caso, r = registrar(automatizacion, prompt_hash, "solo_reglas", det=[linea("TUE-M8-ZN", 1000)])
    assert r["salida"] == "automatico"
    assert lineas_caso(automatizacion, caso) == [("TUE-M8-ZN", 1000, "determinista", "TUE-M8-ZN", 1000)]


def test_solo_reglas_no_llama_a_la_ia_y_guarda_la_version_del_determinista(automatizacion, prompt_hash):
    caso, _ = registrar(automatizacion, prompt_hash, "solo_reglas", det=[linea("TUE-M8-ZN", 1000)])
    automatizacion.execute("reset role")
    automatizacion.execute("select prompt, version, configuracion from intake.extracciones where caso = %s", (caso,))
    assert automatizacion.fetchall() == [("determinista", "0.1.0", "solo_reglas")]


# ---------------------------------------------------------------- sin líneas (prompt v2)
# Sin ninguna línea, en las tres configuraciones: revisión con M01 mientras no haya clasificación
# (eval/registro-de-cambios.md). Antes, minItems: 1 obligaba a la IA a inventarse una línea.

@pytest.mark.parametrize("configuracion, ia, det", [
    ("solo_reglas", None, []),
    ("solo_ia", [], None),
    ("hibrido", [], []),
])
def test_sin_lineas_va_a_revision_con_m01(automatizacion, prompt_hash, configuracion, ia, det):
    caso, r = registrar(automatizacion, prompt_hash, configuracion, ia=ia, det=det)
    assert r["salida"] == "revision" and r["pedido"] is None
    assert motivos(automatizacion, caso) == [("M01", None, {"tipo": "sin_lineas", "configuracion": configuracion})]


def test_hibrido_sin_lineas_de_la_ia_pero_con_lineas_del_determinista_es_omision(automatizacion, prompt_hash):
    # No es "sin líneas": la IA se ha saltado una línea legible (R12).
    caso, r = registrar(automatizacion, prompt_hash, "hibrido", ia=[], det=[linea("TUE-M8-ZN", 1000)])
    assert r["salida"] == "revision"
    assert motivos(automatizacion, caso) == [("R12", 1, {"tipo": "omision_ia", "referencia": "TUE-M8-ZN", "cantidad": 1000})]


def test_el_esquema_v2_admite_una_lista_de_lineas_vacia(cur, prompt_hash):
    cur.execute("select extensions.jsonb_matches_schema(esquema::json, '{\"num_pedido_cliente\": null, \"lineas\": []}')"
                " from intake.prompt_versiones where hash = %s", (prompt_hash,))
    assert cur.fetchone()[0] is True


def test_solo_reglas_con_una_linea_de_menos_sale_automatico(automatizacion, prompt_hash):
    # El correo 01: "TORN 8X30" (equivalencia) no la lee el determinista. Es la línea base: sale en automático
    # con una línea de menos, y la evaluación lo cuenta como error (04, sección 7). Aquí se fija que así es.
    caso, r = registrar(automatizacion, prompt_hash, "solo_reglas", det=[linea("TUE-M8-ZN", 1000)])
    assert r["salida"] == "automatico"
    assert [l[0] for l in lineas_caso(automatizacion, caso)] == ["TUE-M8-ZN"]


# ---------------------------------------------------------------- solo IA

def test_solo_ia_usa_las_lineas_de_la_ia(automatizacion, prompt_hash):
    caso, r = registrar(automatizacion, prompt_hash, "solo_ia", ia=[linea("TORN 8X30", 1000), linea("TUE-M8-ZN", 1000)])
    assert r["salida"] == "automatico"
    assert [(l[0], l[2]) for l in lineas_caso(automatizacion, caso)] == [("TORN 8X30", "ia"), ("TUE-M8-ZN", "ia")]


# ---------------------------------------------------------------- híbrido y R12

def test_hibrido_si_coinciden_sale_automatico(automatizacion, prompt_hash):
    caso, r = registrar(automatizacion, prompt_hash, "hibrido",
                        ia=[linea("TORN 8X30", 1000), linea("TUE-M8-ZN", 1000)],
                        det=[linea("TUE-M8-ZN", 1000)])
    assert r["salida"] == "automatico" and r["motivos"] == []
    assert lineas_caso(automatizacion, caso) == [
        ("TORN 8X30", 1000, "ia", None, None),          # solo la lee la IA: no es motivo
        ("TUE-M8-ZN", 1000, "ambas", "TUE-M8-ZN", 1000),
    ]


def test_hibrido_cantidad_distinta_es_discrepancia(automatizacion, prompt_hash):
    caso, r = registrar(automatizacion, prompt_hash, "hibrido",
                        ia=[linea("TUE-M8-ZN", 1200)], det=[linea("TUE-M8-ZN", 1000)])
    assert r["salida"] == "revision"
    assert motivos(automatizacion, caso) == [("R12", 1, {
        "tipo": "discrepancia",
        "ia": {"referencia": "TUE-M8-ZN", "cantidad": 1200},
        "determinista": {"referencia": "TUE-M8-ZN", "cantidad": 1000},
    })]


def test_hibrido_misma_linea_con_otra_referencia_es_discrepancia(automatizacion, prompt_hash):
    # Los dos leen la misma fila del Excel, pero la IA "traduce" la referencia del cliente.
    texto = "ARAND 8 | Arandela M8 | 1000"
    caso, _ = registrar(automatizacion, prompt_hash, "hibrido",
                        ia=[linea("ARA-M8-ZN", 1000, texto)], det=[linea("ARAND 8", 1000, texto)])
    [(codigo, _, detalle)] = motivos(automatizacion, caso)
    assert codigo == "R12" and detalle["tipo"] == "discrepancia"
    assert (detalle["ia"]["referencia"], detalle["determinista"]["referencia"]) == ("ARA-M8-ZN", "ARAND 8")


def test_hibrido_linea_que_la_ia_omite_es_omision_y_se_anade_al_pedido(automatizacion, prompt_hash):
    caso, r = registrar(automatizacion, prompt_hash, "hibrido",
                        ia=[linea("TOR-M8X30-ZN", 500)],
                        det=[linea("TOR-M8X30-ZN", 500), linea("TUE-M8-ZN", 500)])
    assert r["salida"] == "revision"
    assert lineas_caso(automatizacion, caso)[1] == ("TUE-M8-ZN", 500, "determinista", "TUE-M8-ZN", 500)
    assert motivos(automatizacion, caso) == [("R12", 2, {"tipo": "omision_ia", "referencia": "TUE-M8-ZN", "cantidad": 500})]


def test_hibrido_empareja_sin_importar_mayusculas_ni_espacios(automatizacion, prompt_hash):
    _, r = registrar(automatizacion, prompt_hash, "hibrido",
                     ia=[linea("tue-m8-zn ", 1000)], det=[linea("TUE-M8-ZN", 1000)])
    assert r["salida"] == "automatico"


def test_r12_no_se_aplica_fuera_del_hibrido(automatizacion, prompt_hash):
    # En "solo reglas" todas las líneas son del determinista: no son omisiones de nadie.
    caso, _ = registrar(automatizacion, prompt_hash, "solo_reglas", det=[linea("TUE-M8-ZN", 1000)])
    assert [m[0] for m in motivos(automatizacion, caso)] == []


# ---------------------------------------------------------------- validación

@pytest.mark.parametrize("configuracion, ia, det, mensaje", [
    ("solo_reglas", [linea("TUE-M8-ZN", 1)], [linea("TUE-M8-ZN", 1)], "no admite extracción de la IA"),
    ("solo_reglas", None, None, "necesita extracción del determinista"),
    ("solo_ia", None, None, "necesita extracción de la IA"),
    ("solo_ia", [linea("TUE-M8-ZN", 1)], [linea("TUE-M8-ZN", 1)], "no admite extracción del determinista"),
    ("hibrido", [linea("TUE-M8-ZN", 1)], None, "necesita extracción del determinista"),
    ("todo", None, None, "Configuración desconocida"),
])
def test_cada_configuracion_exige_sus_extracciones(automatizacion, prompt_hash, configuracion, ia, det, mensaje):
    with pytest.raises(psycopg.errors.RaiseException, match=mensaje):
        registrar(automatizacion, prompt_hash, configuracion, ia=ia, det=det)


def test_una_extraccion_del_determinista_mal_formada_se_rechaza(automatizacion, prompt_hash):
    with pytest.raises(psycopg.errors.RaiseException, match="determinista no válida"):
        registrar(automatizacion, prompt_hash, "solo_reglas", det=[{**linea("TUE-M8-ZN", 1), "cantidad": 2.5}])
