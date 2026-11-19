"""Tests del esquema adv: la puerta de las personas de ADV (04, secciones 2.4 y 5.2).

Simulan lo que hace PostgREST con el token de la app: rol authenticated y los claims del token en
request.jwt.claims. Así se prueba la comprobación del rol tal como ocurrirá de verdad.
"""

import json

import psycopg
import pytest
from psycopg.types.json import Jsonb

USUARIO = "11111111-1111-1111-1111-111111111111"


def como(cur, app_metadata=None, user_metadata=None):
    claims = {"sub": USUARIO, "role": "authenticated",
              "app_metadata": app_metadata or {}, "user_metadata": user_metadata or {}}
    cur.execute("set local role authenticated")
    cur.execute("select set_config('request.jwt.claims', %s, true)", (json.dumps(claims),))


def como_adv(cur):
    como(cur, app_metadata={"rol": "adv"})


def caso_en_revision(cur, prompt_hash, remitente="compras@talleresferran.example", lineas=None,
                     autenticacion="dmarc=pass", mid="<adv@pruebas.example>"):
    """Crea un caso como lo haría n8n (service_role) y lo deja evaluado."""
    cur.execute("set local role service_role")
    cur.execute("select api.recibir_correo(%s, %s, 'Pedido', %s, '2026-11-10 09:30+01', 'pruebas')",
                (mid, remitente, autenticacion))
    caso = cur.fetchone()[0]["caso"]
    lineas = lineas or [{"texto": "TOR-M8X30-ZN 500 uds", "referencia": "TOR-M8X30-ZN", "cantidad": 500,
                         "unidad": "uds", "precio": None}]
    cur.execute("select api.registrar_extraccion(caso => %s, configuracion => 'solo_ia', extraccion_ia => %s,"
                " prompt_hash => %s, modelo => 'm')",
                (caso, Jsonb({"num_pedido_cliente": None, "lineas": lineas}), prompt_hash))
    resultado = cur.fetchone()[0]
    cur.execute("reset role")
    return caso, resultado


def llamar(cur, sql, params=()):
    cur.execute(sql, params)
    return cur.fetchone()[0]


# ---------------------------------------------------------------- quién puede entrar

def test_un_usuario_sin_rol_no_entra(cur):
    como(cur)
    with pytest.raises(psycopg.errors.RaiseException, match="Solo administración de ventas"):
        llamar(cur, "select adv.cola()")


def test_el_rol_en_user_metadata_no_da_acceso(cur):
    # user_metadata lo puede cambiar el propio usuario: ponerse el rol ahí no sirve de nada.
    como(cur, user_metadata={"rol": "adv"})
    with pytest.raises(psycopg.errors.RaiseException, match="rol: ninguno"):
        llamar(cur, "select adv.cola()")


def test_otro_rol_en_app_metadata_no_entra(cur):
    como(cur, app_metadata={"rol": "comercial"})
    with pytest.raises(psycopg.errors.RaiseException, match="rol: comercial"):
        llamar(cur, "select adv.cola()")


@pytest.mark.parametrize("rol", ["adv", "adv_responsable"])
def test_adv_y_su_responsable_entran(cur, rol):
    como(cur, app_metadata={"rol": rol})
    assert isinstance(llamar(cur, "select adv.cola()"), list)


def test_las_puertas_estan_separadas(cur):
    # authenticated solo usa adv, y ahí puede ejecutarlo todo; service_role no entra en adv.
    for rol, esquema, esperado in (("authenticated", "adv", True), ("authenticated", "api", False),
                                   ("authenticated", "intake", False), ("service_role", "adv", False),
                                   ("anon", "adv", False)):
        cur.execute("select has_schema_privilege(%s, %s, 'usage')", (rol, esquema))
        assert cur.fetchone()[0] is esperado, (rol, esquema)
    cur.execute("select p.oid::regprocedure::text from pg_proc p join pg_namespace n on n.oid = p.pronamespace"
                " where n.nspname = 'adv' and not has_function_privilege('authenticated', p.oid, 'execute')")
    assert cur.fetchall() == []


# ---------------------------------------------------------------- cola y detalle

def test_la_cola_muestra_los_casos_en_revision(cur, prompt_hash):
    caso, _ = caso_en_revision(cur, prompt_hash, remitente="nuevo@talleresferran.example")
    como_adv(cur)
    fila = next(f for f in llamar(cur, "select adv.cola()") if f["caso"] == caso)
    assert fila["motivos"] == ["R02"] and fila["prioridad"] == 3  # recibido otro día: ya no llega al corte


def test_el_detalle_dice_que_se_puede_hacer_con_cada_motivo(cur, prompt_hash):
    caso, _ = caso_en_revision(cur, prompt_hash, lineas=[
        {"texto": "TOR-M8X30-ZN 500 a 0,20", "referencia": "TOR-M8X30-ZN", "cantidad": 500, "unidad": "uds", "precio": 0.20},
        {"texto": "XYZ 3", "referencia": "XYZ-999", "cantidad": 3, "unidad": None, "precio": None},
    ])
    como_adv(cur)
    detalle = llamar(cur, "select adv.detalle_caso(%s)", (caso,))
    acciones = {(m["codigo"], m["linea"]): m["accion"] for m in detalle["motivos"]}
    assert acciones == {("R11", 1): "bloqueado_otro_dueno", ("R08", 2): "corregir_linea"}
    assert [l["referencia"] for l in detalle["lineas"]] == ["TOR-M8X30-ZN", "XYZ-999"]


# ---------------------------------------------------------------- crear el pedido

def test_forzar_r02_confirmando_el_cliente_crea_el_pedido(cur, prompt_hash):
    caso, r = caso_en_revision(cur, prompt_hash, remitente="nuevo@talleresferran.example")
    assert r["salida"] == "revision"
    como_adv(cur)
    resultado = llamar(cur, "select adv.crear_pedido(%s, %s, 'C0001')",
                       (caso, Jsonb([{"codigo": "R02", "linea": None, "razon": "cliente_confirmado"}])))
    assert resultado["salida"] == "automatico" and resultado["pedido"] is not None
    cur.execute("reset role")
    cur.execute("select origen, cliente from erp.pedidos where id = %s", (resultado["pedido"],))
    assert cur.fetchone() == ("revision", "C0001")
    # CA-25: las reglas se vuelven a pasar y el forzado queda con su razón y su autor.
    cur.execute("select estado, razon_forzado, actor from intake.motivos where caso = %s and codigo = 'R02'"
                " order by id desc limit 1", (caso,))
    assert cur.fetchone() == ("forzado", "cliente_confirmado", USUARIO)


def test_al_forzar_r02_se_aplican_las_demas_reglas_con_el_cliente_confirmado(cur, prompt_hash):
    # Con el cliente confirmado, R11 compara con su tarifa: 0,20 €/ud no es la pactada (0,082).
    caso, _ = caso_en_revision(cur, prompt_hash, remitente="nuevo@talleresferran.example", lineas=[
        {"texto": "TOR-M8X30-ZN 500 a 0,20", "referencia": "TOR-M8X30-ZN", "cantidad": 500, "unidad": "uds", "precio": 0.20}])
    como_adv(cur)
    with pytest.raises(psycopg.errors.RaiseException, match="quedan motivos sin resolver.*R11"):
        llamar(cur, "select adv.crear_pedido(%s, %s, 'C0001')",
               (caso, Jsonb([{"codigo": "R02", "linea": None, "razon": "cliente_confirmado"}])))


def test_si_no_se_puede_crear_no_cambia_nada(cur, prompt_hash):
    caso, _ = caso_en_revision(cur, prompt_hash, remitente="nuevo@talleresferran.example", lineas=[
        {"texto": "TOR-M8X30-ZN 500 a 0,20", "referencia": "TOR-M8X30-ZN", "cantidad": 500, "unidad": "uds", "precio": 0.20}])
    como_adv(cur)
    cur.execute("savepoint antes")
    with pytest.raises(psycopg.errors.RaiseException):
        llamar(cur, "select adv.crear_pedido(%s, %s, 'C0001')",
               (caso, Jsonb([{"codigo": "R02", "linea": None, "razon": "cliente_confirmado"}])))
    cur.execute("rollback to savepoint antes")
    cur.execute("reset role")
    cur.execute("select estado, cliente from intake.casos where id = %s", (caso,))
    assert cur.fetchone() == ("en_revision", None)
    cur.execute("select count(*) from intake.motivos where caso = %s and estado = 'forzado'", (caso,))
    assert cur.fetchone()[0] == 0


@pytest.mark.parametrize("codigo", ["R11"])
def test_los_motivos_de_otro_dueno_no_se_pueden_forzar(cur, prompt_hash, codigo):
    # CA-24: alguien llama por la API a forzar R11.
    caso, _ = caso_en_revision(cur, prompt_hash, lineas=[
        {"texto": "TOR-M8X30-ZN 500 a 0,20", "referencia": "TOR-M8X30-ZN", "cantidad": 500, "unidad": "uds", "precio": 0.20}])
    como_adv(cur)
    with pytest.raises(psycopg.errors.RaiseException, match="lo resuelve su dueño"):
        llamar(cur, "select adv.crear_pedido(%s, %s)",
               (caso, Jsonb([{"codigo": codigo, "linea": 1, "razon": "otra", "texto": "lo digo yo"}])))


def test_forzar_un_remitente_no_verificado_exige_el_telefono(cur, prompt_hash):
    # CA-24: forzar R02 con dmarc=fail sin verificación telefónica.
    caso, _ = caso_en_revision(cur, prompt_hash, autenticacion="dmarc=fail")
    como_adv(cur)
    forzado = [{"codigo": "R02", "linea": None, "razon": "cliente_confirmado"}]
    cur.execute("savepoint antes")
    with pytest.raises(psycopg.errors.RaiseException, match="verificarlo por teléfono"):
        llamar(cur, "select adv.crear_pedido(%s, %s, 'C0001')", (caso, Jsonb(forzado)))
    cur.execute("rollback to savepoint antes")
    forzado[0]["razon"] = "verificado_telefono"
    assert llamar(cur, "select adv.crear_pedido(%s, %s, 'C0001')", (caso, Jsonb(forzado)))["salida"] == "automatico"


def test_un_usuario_sin_rol_no_puede_forzar(cur, prompt_hash):
    # CA-24: un usuario sin rol de ADV fuerza un motivo.
    caso, _ = caso_en_revision(cur, prompt_hash, remitente="nuevo@talleresferran.example")
    como(cur, user_metadata={"rol": "adv"})
    with pytest.raises(psycopg.errors.RaiseException, match="Solo administración de ventas"):
        llamar(cur, "select adv.crear_pedido(%s, %s, 'C0001')",
               (caso, Jsonb([{"codigo": "R02", "linea": None, "razon": "cliente_confirmado"}])))


def test_un_forzado_de_r12_vale_mientras_el_detalle_sea_el_mismo(cur, prompt_hash):
    cur.execute("set local role service_role")
    cur.execute("select api.recibir_correo('<r12@pruebas.example>', 'compras@talleresferran.example', 'Pedido',"
                " 'dmarc=pass', '2026-11-10 09:30+01', 'pruebas')")
    caso = cur.fetchone()[0]["caso"]
    linea_ia = {"texto": "TUE-M8-ZN 1000 (son 1200)", "referencia": "TUE-M8-ZN", "cantidad": 1200, "unidad": None, "precio": None}
    linea_det = {**linea_ia, "cantidad": 1000}
    cur.execute("select api.registrar_extraccion(caso => %s, configuracion => 'hibrido', extraccion_ia => %s,"
                " prompt_hash => %s, modelo => 'm', extraccion_determinista => %s, version_determinista => '0.1.1')",
                (caso, Jsonb({"num_pedido_cliente": None, "lineas": [linea_ia]}), prompt_hash,
                 Jsonb({"lineas": [linea_det]})))
    assert cur.fetchone()[0]["motivos"][0]["codigo"] == "R12"
    cur.execute("reset role")
    como_adv(cur)
    r = llamar(cur, "select adv.crear_pedido(%s, %s)",
               (caso, Jsonb([{"codigo": "R12", "linea": 1, "razon": "lectura_comprobada", "texto": "el cliente corrige a 1200"}])))
    assert r["salida"] == "automatico"
    cur.execute("reset role")
    cur.execute("select cantidad::int from erp.lineas_pedido where pedido = %s", (r["pedido"],))
    assert cur.fetchone()[0] == 1200


def test_m01_y_m02_no_se_fuerzan_se_cierran(cur, prompt_hash):
    cur.execute("set local role service_role")
    cur.execute("select api.recibir_correo('<m02@pruebas.example>', 'compras@talleresferran.example', 'Pedido',"
                " 'dmarc=pass', '2026-11-10 09:30+01', 'pruebas')")
    caso = cur.fetchone()[0]["caso"]
    cur.execute("select api.enviar_a_revision(%s, 'M02', %s)", (caso, Jsonb({"formatos": ["pdf"]})))
    cur.execute("reset role")
    como_adv(cur)
    cur.execute("savepoint antes")
    with pytest.raises(psycopg.errors.RaiseException, match="solo_cerrar"):
        llamar(cur, "select adv.crear_pedido(%s, %s)", (caso, Jsonb([{"codigo": "M02", "linea": None, "razon": "otra"}])))
    cur.execute("rollback to savepoint antes")
    r = llamar(cur, "select adv.cerrar_caso(%s, 'procesado a mano', 'tecleado desde el PDF')", (caso,))
    assert r == {"caso": caso, "estado": "cerrado", "resultado": "procesado a mano"}


# ---------------------------------------------------------------- cerrar y reevaluar

def test_descartar_cierra_el_caso_y_lo_saca_de_la_cola(cur, prompt_hash):
    caso, _ = caso_en_revision(cur, prompt_hash, remitente="nuevo@talleresferran.example")
    como_adv(cur)
    llamar(cur, "select adv.cerrar_caso(%s, 'descartado', 'spam con forma de pedido')", (caso,))
    assert caso not in [f["caso"] for f in llamar(cur, "select adv.cola()")]
    cur.execute("reset role")
    cur.execute("select tipo, actor, carga from intake.eventos where caso = %s order by id desc limit 1", (caso,))
    assert cur.fetchone() == ("cerrado", USUARIO, {"resultado": "descartado"})


def test_reevaluar_tras_un_cambio_en_los_datos_maestros(cur, prompt_hash):
    caso, _ = caso_en_revision(cur, prompt_hash, remitente="nuevo@talleresferran.example")
    # ADV da de alta el contacto (lo haría desde la revisión) y reevalúa: R02 desaparece.
    cur.execute("insert into erp.contactos (cliente, email) values ('C0001', 'nuevo@talleresferran.example')")
    como_adv(cur)
    assert llamar(cur, "select adv.reevaluar(%s)", (caso,))["salida"] == "automatico"


def test_los_eventos_de_la_app_no_llevan_texto_libre(cur, prompt_hash):
    caso, _ = caso_en_revision(cur, prompt_hash, remitente="nuevo@talleresferran.example")
    como_adv(cur)
    llamar(cur, "select adv.crear_pedido(%s, %s, 'C0001')",
           (caso, Jsonb([{"codigo": "R02", "linea": None, "razon": "cliente_confirmado", "texto": "llamé a Ferran"}])))
    cur.execute("reset role")
    cur.execute("select carga from intake.eventos where caso = %s and tipo = 'motivo_forzado'", (caso,))
    assert cur.fetchone()[0] == {"codigo": "R02", "linea": None, "razon": "cliente_confirmado"}
