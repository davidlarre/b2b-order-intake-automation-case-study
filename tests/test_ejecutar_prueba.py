"""ejecutar_prueba.py e informe_prueba.py sin ejecutar la prueba: con filas inventadas a partir de las etiquetas."""

import json

import pytest

import ejecutar_prueba as ep
import informe_prueba as ip

ET = ip.etiquetas()
EN_ALCANCE = [c for c, e in ET.items() if not e["depende_de"]]


@pytest.mark.parametrize("error, infra", [
    ('503 - "{\\"error\\":{\\"message\\":\\"gemini-3.5-flash-lite is currently experiencing high demand"', True),
    ("429 - limit: 500 requests per day", True),
    ("Try spacing your requests out using the batching settings under 'Options'", True),
    ("respuesta no válida: falta tipo", False),
    (None, False),
])
def test_solo_429_y_503_son_de_infraestructura(error, infra):
    assert ep.es_de_infraestructura(error) is infra


def fila(eml, salida="revision", motivos=(), tipo="pedido_nuevo", lineas=(), pedido=None, error=None):
    return {"eml": eml, "caso": 1, "salida": salida, "pedido": pedido, "motivos": list(motivos), "tipo": tipo,
            "destino": None, "lineas": [list(l) for l in lineas], "error": error, "extracciones": []}


def como_la_etiqueta(eml):
    """La fila que daría un sistema perfecto con ese .eml (solo cuenta el primero de cada caso)."""
    e = next(x for x in ET.values() if f"{eml}.eml" in x["eml"])
    salida = e["salida"]["inicial"]
    lineas = [(l["producto"], l["cantidad_uv"]) for l in e["lineas"]] if salida == "automatico" else []
    motivos = sorted({m["codigo"] for m in e["motivos"] if m["momento"] == "inicial"})
    return fila(eml, salida, motivos, e["tipo"], lineas, pedido=1 if salida == "automatico" else None)


def escribir_pasada(carpeta, configuracion, intento, filas, estado="completa"):
    ruta = carpeta / f"{ep.TAG}-{configuracion}-intento{intento}.jsonl"
    cabecera = {"cabecera": {"intento": intento, "commit": "0" * 40, "inicio": "x", "prompts": {"clasificacion": "a" * 64}}}
    ruta.write_text("".join(json.dumps(x) + "\n" for x in [cabecera, *filas, {"estado": estado}]))
    return ruta


@pytest.fixture
def perfecta():
    return {e.removesuffix(".eml"): como_la_etiqueta(e.removesuffix(".eml")) for x in ET.values() for e in x["eml"]}


def test_una_pasada_sin_cierre_o_vacia_cuenta_como_cortada(tmp_path):
    ruta = escribir_pasada(tmp_path, "hibrido", 1, [fila("P01")])
    ruta.write_text("\n".join(ruta.read_text().splitlines()[:-1]) + "\n")
    assert ep.estado(ruta) == "cortada"
    ruta.write_text("")
    assert ep.estado(ruta) == "cortada"


def test_los_intentos_se_ordenan_por_numero(tmp_path):
    for n in (1, 2, 10):
        escribir_pasada(tmp_path, "hibrido", n, [], estado="cortada")
    assert [ep.numero(p) for p in ep.intentos("hibrido", tmp_path)] == [1, 2, 10]


def test_solo_se_admiten_cambios_sin_commitear_en_las_ejecuciones():
    # La primera línea empieza por espacio: no se puede recortar la salida entera.
    porcelana = " M eval/ejecuciones/prueba-v2.1-hibrido-intento1.jsonl\n?? eval/ejecuciones/x.jsonl\n M scripts/a.py"
    assert ep.sin_commitear(porcelana) == [" M scripts/a.py"]
    assert ep.sin_commitear(" M scripts/a.py") == [" M scripts/a.py"]


def test_el_informe_solo_lee_la_pasada_completa(tmp_path, perfecta):
    escribir_pasada(tmp_path, "hibrido", 1, [fila("P01")], estado="cortada")
    escribir_pasada(tmp_path, "hibrido", 2, perfecta.values())
    _, filas = ip.pasada("hibrido", tmp_path)
    assert len(filas) == 66
    assert ip.pasada("solo_ia", tmp_path) is None


def test_un_sistema_perfecto_da_cero_automaticos_malos(perfecta):
    texto = ip.informe({"hibrido": ({"intento": 1, "commit": "0" * 40, "inicio": "x", "prompts": {}}, perfecta)}, ET)
    n = sum(ET[c]["salida"]["inicial"] == "automatico" for c in EN_ALCANCE)
    assert f"| hibrido | 0 de {n} automáticos; límite superior 3/{n}" in texto


def test_una_cantidad_mal_leida_es_un_automatico_erroneo(perfecta):
    caso = next(c for c in EN_ALCANCE if ET[c]["salida"]["inicial"] == "automatico")
    mal = perfecta[caso]
    mal["lineas"][0][1] += 1
    m = ip.medir(ET[caso], mal)
    assert (m["erroneo"], m["indebido"], m["nota_salida"]) == (True, False, "FALLO")


def test_un_automatico_donde_tocaba_revision_es_indebido():
    caso = next(c for c in EN_ALCANCE if ET[c]["salida"]["inicial"] == "revision" and ET[c]["lineas"])
    lineas = [(l["producto"], l["cantidad_uv"]) for l in ET[caso]["lineas"]]
    m = ip.medir(ET[caso], fila(caso, "automatico", lineas=lineas, pedido=1))
    assert (m["erroneo"], m["indebido"]) == (False, True)


def test_un_m03_no_es_un_automatico():
    caso = EN_ALCANCE[0]
    m = ip.medir(ET[caso], fila(caso, "revision", ["M03"], tipo=None, error="503 - high demand"))
    assert (m["nota_salida"], m["automatico"]) == ("M03", False)
