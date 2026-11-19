"""Tests de evaluar_caso y de las reglas R02, R08 y R11 (04, sección 3).

Cada test crea un caso con su correo y sus líneas, como lo dejaría n8n, llama a evaluar_caso
y comprueba la salida y los motivos. Todo ocurre en una transacción que se deshace.
"""

import json
from decimal import Decimal

import psycopg
import pytest

CLIENTE_FERRAN = "compras@talleresferran.example"  # C0001, con tarifas y equivalencias
CLIENTE_VALLES = "pedidos@mantenimentsvalles.example"  # C0002
NOVIEMBRE = "2026-11-10 09:30+01"


def crear_caso(cur, remitente, lineas, autenticacion="dmarc=pass", hora=NOVIEMBRE):
    """lineas: lista de (referencia, cantidad, precio o None)."""
    cur.execute("insert into intake.casos (hora_recepcion, origen) values (%s, 'pruebas') returning id", (hora,))
    caso = cur.fetchone()[0]
    cur.execute(
        "insert into intake.correos (caso, direccion, message_id, remitente, autenticacion)"
        " values (%s, 'entrada', %s, %s, %s)",
        (caso, f"<test-{caso}@pruebas.example>", remitente, autenticacion),
    )
    for n, (referencia, cantidad, precio) in enumerate(lineas, start=1):
        cur.execute(
            "insert into intake.lineas_caso (caso, linea, referencia, cantidad, precio, fuente)"
            " values (%s, %s, %s, %s, %s, 'ia')",
            (caso, n, referencia, cantidad, precio),
        )
    return caso


def evaluar(cur, caso):
    cur.execute("select intake.evaluar_caso(%s)", (caso,))
    return cur.fetchone()[0]


def motivos(cur, caso):
    cur.execute("select codigo, linea, salida, detalle from intake.motivos"
                " where caso = %s and estado = 'abierto' order by codigo, linea", (caso,))
    return cur.fetchall()


# ---------------------------------------------------------------- R02

def test_r02_pasa_con_un_contacto_de_un_unico_cliente(cur):
    caso = crear_caso(cur, CLIENTE_FERRAN, [("TOR-M8X30-ZN", 500, None)])
    assert evaluar(cur, caso)["salida"] == "automatico"
    cur.execute("select cliente from intake.casos where id = %s", (caso,))
    assert cur.fetchone()[0] == "C0001"


def test_r02_email_compartido_por_dos_clientes(cur):
    cur.execute("insert into erp.contactos (cliente, email) values ('C0002', %s)", (CLIENTE_FERRAN,))
    caso = crear_caso(cur, CLIENTE_FERRAN, [("TOR-M8X30-ZN", 500, None)])
    assert evaluar(cur, caso)["salida"] == "revision"
    [(codigo, _, _, detalle)] = motivos(cur, caso)
    assert codigo == "R02" and detalle == {"tipo": "email_compartido", "clientes": 2}


@pytest.mark.parametrize("remitente, sugerencia", [
    ("nuevo@talleresferran.example", "C0001"),   # dominio exacto de un cliente → sugerencia
    ("nuevo@ta11eresferran.example", None),      # dominio parecido → nunca
    ("talleresferran@correo-gratuito.example", None),          # dominio público → nunca
])
def test_r02_remitente_desconocido_y_sugerencia_por_dominio(cur, remitente, sugerencia):
    caso = crear_caso(cur, remitente, [("TOR-M8X30-ZN", 500, None)])
    assert evaluar(cur, caso)["salida"] == "revision"
    [(codigo, _, _, detalle)] = motivos(cur, caso)
    assert codigo == "R02" and detalle == {"tipo": "desconocido", "sugerencia": sugerencia}


def test_r02_dmarc_fail_va_a_revision_y_dmarc_none_no(cur):
    caso_fail = crear_caso(cur, CLIENTE_FERRAN, [("TOR-M8X30-ZN", 500, None)], autenticacion="spf=pass; dmarc=fail")
    assert evaluar(cur, caso_fail)["salida"] == "revision"
    assert motivos(cur, caso_fail)[0][3] == {"tipo": "remitente_no_verificado"}

    caso_none = crear_caso(cur, CLIENTE_FERRAN, [("TOR-M8X30-ZN", 500, None)], autenticacion="dmarc=none")
    assert evaluar(cur, caso_none)["salida"] == "automatico"


def test_r02_corta_el_flujo(cur):
    # Línea inexistente y precio absurdo: si R02 falla, R08 y R11 ni se evalúan.
    caso = crear_caso(cur, "nadie@desconocido.example", [("XYZ-999", 1, 99.0)])
    evaluar(cur, caso)
    assert [m[0] for m in motivos(cur, caso)] == ["R02"]


# ---------------------------------------------------------------- R08

@pytest.mark.parametrize("referencia, producto", [
    ("TOR-M8X30-ZN", "TOR-M8X30-ZN"),     # código exacto de Orvalle
    ("  tor-m8x30-zn ", "TOR-M8X30-ZN"),  # el mismo, con espacios y en minúsculas
    ("torn 8x30", "TOR-M8X30-ZN"),        # equivalencia de C0001
])
def test_r08_pasa_por_codigo_o_equivalencia(cur, referencia, producto):
    caso = crear_caso(cur, CLIENTE_FERRAN, [(referencia, 500, None)])
    assert evaluar(cur, caso)["salida"] == "automatico"
    cur.execute("select producto from intake.lineas_caso where caso = %s", (caso,))
    assert cur.fetchone()[0] == producto


def test_r08_la_equivalencia_es_de_cada_cliente(cur):
    # "TORN 8X30" es una equivalencia de C0001, no de C0002.
    caso = crear_caso(cur, CLIENTE_VALLES, [("TORN 8X30", 500, None)])
    evaluar(cur, caso)
    assert motivos(cur, caso)[0][0] == "R08"


def test_r08_solo_descripcion_va_a_revision_con_candidatos(cur):
    caso = crear_caso(cur, CLIENTE_FERRAN, [("arandela plana M10", 100, None)])
    assert evaluar(cur, caso)["salida"] == "revision"
    [(codigo, linea, salida, detalle)] = motivos(cur, caso)
    assert (codigo, linea, salida, detalle["tipo"]) == ("R08", 1, "revision", "solo_descripcion")
    assert detalle["candidatos"][0] == "ARA-M10-ZN"


def test_r08_no_encontrada_pide_datos(cur):
    caso = crear_caso(cur, CLIENTE_FERRAN, [("XYZ-999", 10, None)])
    assert evaluar(cur, caso)["salida"] == "pedir_datos"
    [(codigo, _, salida, detalle)] = motivos(cur, caso)
    assert (codigo, salida, detalle) == ("R08", "pedir_datos", {"tipo": "no_encontrada", "referencia": "XYZ-999"})


# ---------------------------------------------------------------- R11

@pytest.mark.parametrize("precio, salida", [
    (None, "automatico"),     # sin precio → se usa la tarifa
    (Decimal("0.0820"), "automatico"),   # igual a la tarifa pactada
    (Decimal("0.0920"), "automatico"),   # 0,01 €/ud por encima: solo redondeo (CA-13)
    (Decimal("0.0921"), "revision"),     # por encima de la tolerancia
    (Decimal("0.0950"), "revision"),     # el precio general no es el de este cliente
])
def test_r11_tolerancia_contra_la_tarifa_pactada(cur, precio, salida):
    caso = crear_caso(cur, CLIENTE_FERRAN, [("TOR-M8X30-ZN", 500, precio)])
    assert evaluar(cur, caso)["salida"] == salida


def test_r11_motivo_con_precios_y_comercial(cur):
    caso = crear_caso(cur, CLIENTE_FERRAN, [("TOR-M8X30-ZN", 500, Decimal("0.1020"))])
    evaluar(cur, caso)
    [(codigo, _, _, detalle)] = motivos(cur, caso)
    assert codigo == "R11"
    assert detalle == {"precio_pedido": Decimal("0.1020"), "precio_referencia": Decimal("0.0820"), "diferencia": Decimal("0.0200"), "comercial": "COM-1"}


def test_r11_usa_la_hora_de_recepcion_y_no_la_actual(cur):
    # La tarifa de C0001 vence el 31-12-2026. Un pedido recibido en enero de 2027 usa el precio general.
    caso = crear_caso(cur, CLIENTE_FERRAN, [("TOR-M8X30-ZN", 500, Decimal("0.0820"))], hora="2027-01-15 09:30+01")
    evaluar(cur, caso)
    [(codigo, _, _, detalle)] = motivos(cur, caso)
    assert codigo == "R11" and detalle["precio_referencia"] == Decimal("0.0950")


def test_r11_ignora_las_tarifas_pendientes(cur):
    cur.execute("insert into erp.tarifas (cliente, producto, precio_neto, desde, estado, origen)"
                " values ('C0002', 'TUE-M8-ZN', 0.0250, '2026-01-01', 'pendiente', 'test')")
    caso = crear_caso(cur, CLIENTE_VALLES, [("TUE-M8-ZN", 100, None)])
    assert evaluar(cur, caso)["salida"] == "automatico"
    cur.execute("select precio_referencia from intake.lineas_caso where caso = %s", (caso,))
    assert cur.fetchone()[0] == Decimal("0.0310")  # precio general, no la tarifa pendiente de 0,0250


# ---------------------------------------------------------------- evaluar_caso

def test_automatico_crea_el_pedido_en_el_erp(cur):
    caso = crear_caso(cur, CLIENTE_FERRAN, [("TOR-M8X30-ZN", 500, None), ("ARAND 8", 500, None)])
    resultado = evaluar(cur, caso)
    assert resultado["salida"] == "automatico" and resultado["pedido"] is not None
    cur.execute("select p.cliente, p.origen, p.caso, count(l.*), sum(l.cantidad * l.precio_unitario)"
                " from erp.pedidos p join erp.lineas_pedido l on l.pedido = p.id"
                " where p.id = %s group by p.id", (resultado["pedido"],))
    cliente, origen, caso_pedido, lineas, total = cur.fetchone()
    assert (cliente, origen, caso_pedido, lineas) == ("C0001", "automatico", caso, 2)
    assert total == 500 * Decimal("0.0820") + 500 * Decimal("0.0100")
    cur.execute("select estado from intake.casos where id = %s", (caso,))
    assert cur.fetchone()[0] == "pedido_creado"


def test_revision_gana_a_pedir_datos(cur):
    # Línea 1 no encontrada (pedir datos) y línea 2 con precio distinto (revisión).
    caso = crear_caso(cur, CLIENTE_FERRAN, [("XYZ-999", 10, None), ("TOR-M8X30-ZN", 500, Decimal("0.2000"))])
    assert evaluar(cur, caso)["salida"] == "revision"
    assert [(m[0], m[1]) for m in motivos(cur, caso)] == [("R08", 1), ("R11", 2)]
    cur.execute("select estado from intake.casos where id = %s", (caso,))
    assert cur.fetchone()[0] == "en_revision"


def test_solo_faltan_datos_queda_pendiente_del_cliente_sin_pedido(cur):
    caso = crear_caso(cur, CLIENTE_FERRAN, [("XYZ-999", 10, None)])
    assert evaluar(cur, caso)["pedido"] is None
    cur.execute("select estado from intake.casos where id = %s", (caso,))
    assert cur.fetchone()[0] == "pendiente_cliente"


def test_reevaluar_da_el_mismo_resultado_y_sustituye_los_motivos(cur):
    caso = crear_caso(cur, CLIENTE_FERRAN, [("TOR-M8X30-ZN", 500, Decimal("0.2000"))])
    primera, segunda = evaluar(cur, caso), evaluar(cur, caso)
    assert primera["salida"] == segunda["salida"] == "revision"
    cur.execute("select estado, count(*) from intake.motivos where caso = %s group by estado order by estado", (caso,))
    assert cur.fetchall() == [("abierto", 1), ("resuelto", 1)]


def test_un_caso_con_pedido_no_se_vuelve_a_evaluar(cur):
    caso = crear_caso(cur, CLIENTE_FERRAN, [("TOR-M8X30-ZN", 500, None)])
    evaluar(cur, caso)
    with pytest.raises(psycopg.errors.RaiseException, match="estado final"):
        evaluar(cur, caso)


def test_cada_evaluacion_deja_un_evento_sin_datos_personales(cur):
    caso = crear_caso(cur, "nuevo@talleresferran.example", [("TOR-M8X30-ZN", 500, None)])
    evaluar(cur, caso)
    cur.execute("select tipo, carga from intake.eventos where caso = %s", (caso,))
    [(tipo, carga)] = cur.fetchall()
    assert tipo == "reglas_evaluadas" and carga["salida"] == "revision"
    assert "@" not in json.dumps(carga)


# ---------------------------------------------------------------- permisos

def test_solo_la_automatizacion_puede_llamar_a_evaluar_caso(cur):
    caso = crear_caso(cur, CLIENTE_FERRAN, [("TOR-M8X30-ZN", 500, None)])
    cur.execute("savepoint antes")
    for rol in ("anon", "authenticated"):
        cur.execute(f"set local role {rol}")
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            evaluar(cur, caso)
        cur.execute("rollback to savepoint antes")
    cur.execute("set local role service_role")
    assert evaluar(cur, caso)["salida"] == "automatico"


def test_la_automatizacion_no_llega_a_las_reglas_ni_a_las_tablas(cur):
    # Se comprueba en el catálogo y no ejecutando: en Supabase local (Postgres 17.6), ejecutar como
    # service_role una función sin permiso tumba el proceso del servidor (segmentation fault).
    cur.execute("select p.oid::regprocedure::text from pg_proc p join pg_namespace n on n.oid = p.pronamespace"
                " where n.nspname in ('intake', 'erp')"
                " and has_function_privilege('service_role', p.oid, 'execute')")
    assert [f for (f,) in cur.fetchall()] == ["intake.evaluar_caso(bigint)"]
    cur.execute("select n.nspname || '.' || c.relname from pg_class c join pg_namespace n on n.oid = c.relnamespace"
                " where n.nspname in ('intake', 'erp') and c.relkind = 'r'"
                " and has_table_privilege('service_role', c.oid, 'select, insert, update, delete')")
    assert cur.fetchall() == []
