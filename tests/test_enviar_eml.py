"""Tests de la comparación de enviar_eml.py con esperado.json, sin n8n ni base de datos."""

from collections import Counter

from enviar_eml import comparar, con_configuracion, con_fecha_de_hoy, evaluar, fecha

ESPERADO = {"salida": "automatico", "motivos": [], "lineas": [["TOR-M8X30-ZN", 1000], ["TUE-M8-ZN", 1000]]}


def pedido_con(*lineas):
    return lambda _pedido: Counter(lineas)


def test_pedido_completo_es_ok():
    r = {"salida": "automatico", "motivos": [], "pedido": 1}
    assert comparar(r, ESPERADO, pedido_con(("TOR-M8X30-ZN", 1000), ("TUE-M8-ZN", 1000))) == []


def test_un_pedido_automatico_con_una_linea_de_menos_es_fallo():
    # El correo 01 en "solo reglas": la salida y los motivos coinciden, pero falta una línea.
    r = {"salida": "automatico", "motivos": [], "pedido": 1}
    assert comparar(r, ESPERADO, pedido_con(("TUE-M8-ZN", 1000))) == ["faltan TOR-M8X30-ZN x1000"]


def test_cantidad_equivocada_sale_como_falta_y_sobra():
    r = {"salida": "automatico", "motivos": [], "pedido": 1}
    assert comparar(r, ESPERADO, pedido_con(("TOR-M8X30-ZN", 1000), ("TUE-M8-ZN", 100))) == [
        "faltan TUE-M8-ZN x1000", "sobran TUE-M8-ZN x100"]


def test_sin_pedido_no_se_comparan_lineas():
    r = {"salida": "revision", "motivos": [{"codigo": "R11"}], "pedido": None}
    def no_llamar(_):
        raise AssertionError("no debería leer el pedido")
    assert comparar(r, {"salida": "revision", "motivos": ["R11"], "lineas": [["X", 1]]}, no_llamar) == []


def test_salida_y_motivos_distintos():
    r = {"salida": "automatico", "motivos": [], "pedido": 1}
    assert comparar(r, {"salida": "revision", "motivos": ["R11"]}, pedido_con()) == [
        "salida automatico, esperada revision", "motivos -, esperados R11"]


def test_la_configuracion_se_anade_a_la_url():
    assert con_configuracion("http://h/webhook/pruebas/eml", "solo_ia") == "http://h/webhook/pruebas/eml?configuracion=solo_ia"
    assert con_configuracion("http://h/x?a=1", "hibrido") == "http://h/x?a=1&configuracion=hibrido"
    assert con_configuracion("http://h/x", None) == "http://h/x"


# El 06: el cliente corrige la cantidad en la misma línea. Resultados reales de las tres configuraciones.
CASO_06 = {
    "salida": "automatico", "motivos": [],
    "lineas": [["TOR-M8X30-ZN", 1000], ["TUE-M8-ZN", 1200]],
    "aceptables": [{"salida": "revision", "motivos": ["R12"]}],
}


def test_06_solo_reglas_es_fallo_por_cantidad():
    r = {"salida": "automatico", "motivos": [], "pedido": 138}
    estado, diferencias = evaluar(r, CASO_06, pedido_con(("TOR-M8X30-ZN", 1000), ("TUE-M8-ZN", 1000)))
    assert estado == "FALLO" and diferencias == ["faltan TUE-M8-ZN x1200", "sobran TUE-M8-ZN x1000"]


def test_06_solo_ia_es_ok():
    r = {"salida": "automatico", "motivos": [], "pedido": 141}
    assert evaluar(r, CASO_06, pedido_con(("TOR-M8X30-ZN", 1000), ("TUE-M8-ZN", 1200))) == ("OK", [])


def test_06_hibrido_en_revision_por_r12_es_aceptable():
    r = {"salida": "revision", "motivos": [{"codigo": "R12"}], "pedido": None}
    estado, _ = evaluar(r, CASO_06, pedido_con())
    assert estado == "ACEPTABLE"


def test_una_revision_que_no_esta_entre_las_aceptables_es_fallo():
    r = {"salida": "revision", "motivos": [{"codigo": "R11"}], "pedido": None}
    assert evaluar(r, CASO_06, pedido_con())[0] == "FALLO"


def test_con_fecha_de_hoy_cambia_el_dia_y_conserva_la_hora():
    from datetime import datetime
    from zoneinfo import ZoneInfo

    eml = b"From: a@b.example\r\nDate: Tue, 10 Nov 2026 08:05:00 +0100\r\nSubject: x\r\n\r\nDate: en el cuerpo no se toca\r\n"
    nuevo = con_fecha_de_hoy(eml)
    d = fecha(nuevo)
    assert d.date() == datetime.now(ZoneInfo("Europe/Madrid")).date()
    assert (d.hour, d.minute, d.utcoffset().total_seconds()) == (8, 5, 3600)
    assert nuevo.endswith(b"Date: en el cuerpo no se toca\r\n")
