"""Fichas, correos y etiquetas de evaluacion-v2. Todo estático: aquí no se ejecuta el sistema sobre ningún correo."""

import email
import email.policy
import json
import re
from collections import Counter
from datetime import datetime
from decimal import Decimal

import jsonschema
import pytest
import yaml

import generar_correos as g
import generar_maestros as gm

ESQUEMA = json.loads((g.EVALUACION / "esquema-etiqueta.json").read_text())
FICHAS = {c: g.leer_fichas(c) for c in g.CONJUNTOS}
EMLS = {c: g.generar(c) for c in g.CONJUNTOS}
ETIQUETAS = {c: {p.stem: yaml.safe_load(p.read_text()) for p in sorted((g.EVALUACION / c / "etiquetas").glob("*.yaml"))}
             for c in g.CONJUNTOS}
CASOS = [(c, i) for c in g.CONJUNTOS for i in FICHAS[c]]
FUERA = {"R03", "R04", "R05", "R06", "R07", "R09", "R10", "R13", "R14", "M04", "D16", "D22", "RESPUESTA"}


@pytest.fixture(scope="module")
def m():
    return gm.generar()


def test_80_casos_y_86_eml():
    assert {c: len(f) for c, f in FICHAS.items()} == {"desarrollo": 20, "prueba": 60}
    assert {c: sorted(e) for c, e in ETIQUETAS.items()} == {c: sorted(f) for c, f in FICHAS.items()}
    assert {c: len(e) for c, e in EMLS.items()} == {"desarrollo": 20, "prueba": 66}


def test_la_mezcla_es_la_de_d23():
    tipos = {c: Counter(e["tipo"] for e in ETIQUETAS[c].values()) for c in g.CONJUNTOS}
    assert tipos["prueba"] == {"pedido_nuevo": 42, "modificacion_anulacion": 6, "consulta": 4, "reclamacion": 3, "otros": 5}
    assert tipos["desarrollo"] == {"pedido_nuevo": 14, "modificacion_anulacion": 2, "consulta": 2, "reclamacion": 1, "otros": 1}
    repite = {i for i, f in FICHAS["prueba"].items() if any(t.startswith("repite") for t in f["trampas"])}
    formatos = Counter(f["formato"] for i, f in FICHAS["prueba"].items() if f["tipo"] == "pedido_nuevo" and i not in repite)
    assert formatos == {"texto": 18, "excel": 14, "reenvio": 5, "pdf": 3} and len(repite) == 2
    assert sum(e["idioma"] != "es" for e in ETIQUETAS["prueba"].values()) == 4


def test_los_cuatro_tipos_reservados_no_estan_en_desarrollo():
    reservadas = {"dominio_parecido", "numeracion_ciclica", "instrucciones_en_el_cuerpo", "reclamacion_con_pedido"}
    de = {c: {t for f in FICHAS[c].values() for t in f["trampas"]} for c in g.CONJUNTOS}
    assert reservadas <= de["prueba"] and not reservadas & de["desarrollo"]


def test_los_eml_son_los_que_salen_de_su_ficha():
    for c in g.CONJUNTOS:
        en_disco = {p.name: p.read_bytes() for p in (g.EVALUACION / c / "correos").glob("*.eml")}
        assert en_disco == EMLS[c]


def test_ningun_correo_usa_un_dominio_real():
    for c in g.CONJUNTOS:
        for nombre, eml in EMLS[c].items():
            for dominio in re.findall(rb"@([A-Za-z0-9.-]+\.[A-Za-z]{2,})", eml):
                assert dominio.endswith(b".example"), (nombre, dominio)


def test_cabeceras():
    ids = set()
    for c in g.CONJUNTOS:
        for nombre, eml in EMLS[c].items():
            mensaje = email.message_from_bytes(eml, policy=email.policy.default)
            assert mensaje["Message-ID"] not in ids
            ids.add(mensaje["Message-ID"])
            assert mensaje["To"] == "pedidos@orvalle.example" and mensaje["Date"].datetime.utcoffset().seconds == 3600
            assert ("Auto-Submitted" in mensaje) == (nombre == "P18b.eml")
            assert "dmarc=" in mensaje["Authentication-Results"]
    prueba = [f["correos"][0].get("dmarc", "pass") for f in FICHAS["prueba"].values()]
    assert 18 <= prueba.count("none") <= 24   # un tercio (05, sección 5)


@pytest.mark.parametrize("conjunto, caso", CASOS)
def test_etiqueta_valida_y_coherente(conjunto, caso, m):
    e, f = ETIQUETAS[conjunto][caso], FICHAS[conjunto][caso]
    jsonschema.validate(e, ESQUEMA)
    assert e["id"] == caso and e["conjunto"] == conjunto
    assert e["eml"] == [x["eml"] for x in f["correos"]] and e["tipo"] == f["tipo"]
    productos = {p["codigo"]: p for p in m["productos"]}

    # Las marcas son las que calcula el script, y cada una está resuelta.
    assert e["marcas"] == g.marcas(f, EMLS[conjunto], productos)
    assert bool(e["marcas"]) == bool(e["nota_marcas"])

    # Cada línea está literalmente en el correo y su producto existe.
    texto = [g.plano(t) for x in e["eml"] for t in g.texto_de(EMLS[conjunto][x]) if not t.startswith(">")]
    for l in e["lineas"]:
        assert l["texto"] is None or g.plano(l["texto"]) in texto, l["texto"]
        assert l["producto"] is None or l["producto"] in productos
    for mot in e["motivos"]:
        assert mot["linea"] is None or mot["linea"] <= len(e["lineas"])

    # Coherencia entre tipo, salida, motivos y alcance.
    codigos = {x["codigo"] for x in e["motivos"] if x["momento"] == "inicial"}
    if e["tipo"] in ("consulta", "reclamacion", "modificacion_anulacion"):
        assert e["salida"]["inicial"] == "revision" and codigos == {"R01"} and e["lineas"] == []
    if e["tipo"] == "otros":
        assert e["salida"]["inicial"] == "derivado" and not codigos and "destino" in e
    if e["salida"]["inicial"] == "automatico":
        assert not codigos and e["lineas"] and all(l["cantidad_uv"] for l in e["lineas"])
    assert (e["revision_necesaria"] is None) == (e["salida"]["final"] != "revision")
    for c in codigos & {"R03", "R04", "R05", "R06", "R07", "R09", "R13", "R14", "M04"}:
        assert c in e["depende_de"]
    if codigos & {"R10-EMBALAJE", "R10-UNIDAD"}:
        assert {"R10", "R07"} & set(e["depende_de"])
    if len(e["eml"]) > 1:
        assert "RESPUESTA" in e["depende_de"]
    if f["formato"] == "reenvio":
        assert "R03" in e["depende_de"]


@pytest.mark.parametrize("conjunto, caso", [(c, i) for c, i in CASOS if ETIQUETAS[c][i]["tipo"] == "pedido_nuevo"])
def test_precios_embalajes_e_importe_segun_la_especificacion(conjunto, caso, m):
    """R10, R11 y R13 calculadas aquí desde 04, sin el SQL: contrastan la etiqueta con los datos maestros."""
    e, f = ETIQUETAS[conjunto][caso], FICHAS[conjunto][caso]
    if not e["cliente"]:
        return
    fecha = datetime.fromisoformat(str(f["correos"][0]["fecha"])).date().isoformat()
    productos = {p["codigo"]: p for p in m["productos"]}
    tarifas = {t["producto"]: t["precio"] for t in m["tarifas"]
               if t["cliente"] == e["cliente"] and t["estado"] == "activa" and t["desde"] <= fecha <= t["hasta"]}
    por_linea = {(x["codigo"], x["linea"]) for x in e["motivos"]}
    cortado = {x["codigo"] for x in e["motivos"]} & {"R02", "R04", "M02", "M01"}
    total = Decimal(0)
    for n, l in enumerate(e["lineas"], start=1):
        p = productos.get(l["producto"])
        if not p or cortado:
            continue
        referencia = tarifas.get(l["producto"], p["precio"])
        precio = Decimal(str(l["precio_pedido"])) if l["precio_pedido"] is not None else referencia
        assert (abs(precio - referencia) > Decimal("0.01")) == (("R11", n) in por_linea), (n, precio, referencia)
        assert (not p["activo"]) == (("R09", n) in por_linea)
        if l["cantidad_uv"]:
            mal = l["cantidad_uv"] < p["minimo"] or l["cantidad_uv"] % p["embalaje"] != 0
            assert mal == (("R10-EMBALAJE", n) in por_linea), n
            total += max(precio, referencia) * l["cantidad_uv"]
    assert (total > 3000) == (("R13", None) in por_linea), total


@pytest.mark.parametrize("conjunto, caso", [(c, i) for c, i in CASOS if ETIQUETAS[c][i]["tipo"] == "pedido_nuevo"])
def test_r14_segun_la_especificacion(conjunto, caso, m):
    e = ETIQUETAS[conjunto][caso]
    esperados = {x["linea"] for x in e["motivos"] if x["codigo"] == "R14"}
    cortado = {x["codigo"] for x in e["motivos"]} & {"R02", "R04", "M02", "M01"}
    for n, l in enumerate(e["lineas"], start=1):
        previos = sorted(c for p in m["pedidos"] if p["cliente"] == e["cliente"] for prod, c, _ in p["lineas"]
                         if prod == l["producto"])
        if len(previos) < 3 or cortado or not l["cantidad_uv"]:
            assert n not in esperados
            continue
        k = len(previos)
        mediana = (previos[k // 2] + previos[(k - 1) // 2]) / 2
        anomala = l["cantidad_uv"] > 5 * mediana or l["cantidad_uv"] < mediana / 5
        assert anomala == (n in esperados), (n, previos)


@pytest.mark.parametrize("conjunto, caso", CASOS)
def test_remitentes_segun_r02(conjunto, caso, m):
    e, f = ETIQUETAS[conjunto][caso], FICHAS[conjunto][caso]
    if e["tipo"] != "pedido_nuevo":
        return
    c = f["correos"][0]
    direccion = (c.get("reenvio") or c)["de"][1]
    clientes = {x["cliente"] for x in m["contactos"] if x["email"] == direccion}
    falla = len(clientes) != 1 or c.get("dmarc") == "fail"
    assert falla == any(x["codigo"] == "R02" for x in e["motivos"])
    bloqueado = {x["codigo"] for x in m["clientes"] if x["bloqueado"]} & clientes
    assert bool(bloqueado) == any(x["codigo"] == "R04" for x in e["motivos"])


# ---------------------------------------------------------------- alcance y congelación

def test_el_alcance_publicado_es_el_de_las_etiquetas():
    md = (gm.RAIZ / "eval" / "alcance-prueba-v2.md").read_text()
    tabla = {i: {d.strip() for d in deps.split(",")} for i, deps in re.findall(r"^\| (P\d\d) \| ([^|]+) \|", md, re.M)}
    assert tabla == {i: set(e["depende_de"]) for i, e in ETIQUETAS["prueba"].items() if e["depende_de"]}
    en_alcance = re.search(r"<!-- en alcance -->\n(.+?)\n<!-- fin -->", md, re.S).group(1)
    assert set(re.findall(r"P\d\d", en_alcance)) == {i for i, e in ETIQUETAS["prueba"].items() if not e["depende_de"]}
