"""Datos maestros generados (scripts/generar_maestros.py): deterministas, coherentes y sin tocar lo de la v1."""

from collections import Counter
from datetime import date
from decimal import Decimal

import pytest

import generar_maestros as g


@pytest.fixture(scope="module")
def m():
    return g.generar()


def test_el_fichero_cargado_es_el_que_produce_el_generador(m):
    assert g.DESTINO.read_text() == g.a_sql(m)
    assert g.a_sql(g.generar()) == g.a_sql(m)     # semilla fija


def test_volumen(m):
    assert len(m["productos"]) == 498 and len(m["clientes"]) == 120
    assert 1300 <= len(m["pedidos"]) <= 1500 and 5300 <= sum(len(p["lineas"]) for p in m["pedidos"]) <= 6300
    assert min(p["fecha"].date() for p in m["pedidos"]) >= g.INICIO
    assert max(p["fecha"].date() for p in m["pedidos"]) <= g.MIGRACION


def test_los_lunes_tienen_mas_pedidos_y_agosto_menos(m):
    dias = Counter(p["fecha"].weekday() for p in m["pedidos"])
    meses = Counter(p["fecha"].month for p in m["pedidos"])
    assert dias[0] > 1.5 * dias[2] and meses[8] < 0.6 * meses[7]
    assert not {5, 6} & set(dias)


def test_lo_de_la_v1_no_se_vuelve_a_escribir(m):
    sql = g.a_sql(m)
    for codigo in g.del_seed("productos"):
        assert f"  ('{codigo}', '" not in sql.split("insert into erp.conversiones_unidad")[0]
    assert "('C0001', 'B6" not in sql and "('C0002', 'B6" not in sql and "('C0003', 'B6" not in sql
    for tabla in ("direcciones", "contactos", "tarifas", "equivalencias", "pedidos"):
        assert not [f for f in m[tabla] if (f[0] if isinstance(f, tuple) else f["cliente"]) in ("C0001", "C0002", "C0003")]


def test_referencias_y_unidades_validas(m):
    productos = {p["codigo"]: p for p in m["productos"]}
    assert len(productos) == len(m["productos"])
    for p in m["pedidos"]:
        for prod, cantidad, precio in p["lineas"]:
            assert cantidad >= productos[prod]["minimo"] and cantidad % productos[prod]["embalaje"] == 0
            assert precio > 0
    claves = [(t["cliente"], t["producto"], t["desde"]) for t in m["tarifas"]]
    assert len(claves) == len(set(claves))
    eq = [(c, r) for c, r, _ in m["equivalencias"]]
    assert len(eq) == len(set(eq)) and all(r == r.upper().strip() for _, r in eq)
    assert {p for p, s in g.DESCATALOGADOS.items()} == {p["codigo"] for p in m["productos"] if not p["activo"]}


def test_todos_los_correos_son_example(m):
    assert all(c["email"].endswith(".example") for c in m["contactos"])
    assert all(c[2].endswith(".example") for c in m["comerciales"])


def test_anclas(m):
    """Lo que necesitan los casos: lo que cambie aquí rompe la etiqueta de algún correo."""
    def pedidos(cliente, producto):
        return [c for p in m["pedidos"] if p["cliente"] == cliente for prod, c, _ in p["lineas"] if prod == producto]

    assert sorted(c["codigo"] for c in m["clientes"] if c["bloqueado"]) == ["C0019", "C0072"]
    assert len(pedidos("C0095", "CIN-EMB-66")) == 2                            # P09: R14 no se aplica
    assert sorted(pedidos("C0096", "SIE-HOJ-24")) == [90, 100, 100, 100, 120]  # P35
    assert sorted(pedidos("C0103", "GUA-PU-9")) == [24, 24, 24, 36]            # P36
    assert len([p for p in m["pedidos"] if p["cliente"] == "C0080" and p["num"] == "12"]) == 2    # P29
    por_email = Counter(c["email"] for c in m["contactos"])
    assert por_email["compras@gruptecnicvalles.example"] == 2 and por_email["pedidos@centraltalleres.example"] == 3
    tarifa = {(t["cliente"], t["producto"]): t for t in m["tarifas"]}
    assert tarifa[("C0100", "SPR-LUB")]["estado"] == "pendiente"
    assert tarifa[("C0086", "LLC-17")]["hasta"] == g.SIN_VIGENCIA.isoformat() == "2027-01-28"
    ultimo = max((p for p in m["pedidos"] if p["cliente"] == "C0034"), key=lambda p: p["fecha"])
    assert ultimo["direccion"]["calle"] == "Carrer de la Forja"                # P17: «la de siempre»


def test_hay_precios_facturados_que_no_estan_en_ninguna_tarifa(m):
    assert ("C0108", "GUA-COR-9") in m["telefono"]
    tarifas = {(t["cliente"], t["producto"]) for t in m["tarifas"]}
    assert not tarifas & set(m["telefono"])
    facturado = {pr for p in m["pedidos"] if p["cliente"] == "C0108" for prod, _, pr in p["lineas"] if prod == "GUA-COR-9"}
    assert facturado == {Decimal("4.50")}


def test_cargado_en_la_base(cur, m):
    cur.execute("select (select count(*) from erp.productos), (select count(*) from erp.clientes),"
                " (select count(*) from erp.pedidos where origen = 'historico'), (select count(*) from erp.festivos),"
                " (select count(*) from erp.conversiones_unidad)")
    assert cur.fetchone() == (498, 120, len(m["pedidos"]), len(g.FESTIVOS), len(m["conversiones"]))
    cur.execute("select count(*) from erp.lineas_pedido l join erp.pedidos p on p.id = l.pedido where p.origen = 'historico'")
    assert cur.fetchone()[0] == sum(len(p["lineas"]) for p in m["pedidos"])
    cur.execute("select codigo, precio_general from erp.productos where codigo in ('TOR-M8X30-ZN', 'DIS-COR-125')")
    assert dict(cur.fetchall()) == {"TOR-M8X30-ZN": Decimal("0.0950"), "DIS-COR-125": Decimal("0.8900")}
    # Un pedido nuevo no puede repetir un número del histórico.
    cur.execute("select nextval('erp.numero_pedido') > max(substr(numero, 3)::int) from erp.pedidos where origen = 'historico'")
    assert cur.fetchone()[0] is True


def test_los_festivos_cubren_los_correos_de_enero(m):
    assert {date.fromisoformat(f) for f, _ in m["festivos"]} >= {date(2026, 12, 8), date(2027, 1, 6)}
