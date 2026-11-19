"""Tests de api.codigos_producto: la lista de códigos que usa el extractor determinista (04, sección 6.3)."""


def test_devuelve_todos_los_codigos_del_catalogo_y_nada_mas(cur):
    cur.execute("select codigo from erp.productos order by codigo")
    esperados = [c for (c,) in cur.fetchall()]
    cur.execute("set local role service_role")
    cur.execute("select api.codigos_producto()")
    assert cur.fetchone()[0] == esperados


def test_incluye_los_descatalogados(cur):
    # Si un cliente pide un descatalogado, el extractor tiene que leer la línea: el que decide es R09.
    cur.execute("update erp.productos set activo = false where codigo = 'BRO-HSS-8'")
    cur.execute("set local role service_role")
    cur.execute("select api.codigos_producto()")
    assert "BRO-HSS-8" in cur.fetchone()[0]
