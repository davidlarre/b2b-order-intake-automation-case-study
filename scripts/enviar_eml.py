"""Envía los .eml de una carpeta a la entrada de pruebas de n8n y muestra el resultado de cada uno.

Uso:
    uv run scripts/enviar_eml.py data/synthetic/corte-vertical [--configuracion solo_reglas] [--nuevos] [--url URL]
    uv run scripts/enviar_eml.py data/synthetic/extraccion/04-excel-xlsx.eml --url URL_DE_PRUEBA

- Acepta una carpeta o un solo .eml. Los envía por orden de su cabecera Date, como la evaluación (04, sección 7).
- --configuracion elige solo_reglas, solo_ia o hibrido (sin ella, n8n usa hibrido).
- Si la carpeta tiene un esperado.json, compara con lo esperado la salida, los motivos y, si se creó un pedido,
  sus líneas (producto y cantidad), leídas de la base de datos. Un pedido automático con una línea de menos
  es un FALLO, no un OK. Lo esperado es lo correcto según la especificación, en todas las configuraciones.
  "aceptables" lista salidas seguras que no son la esperada (una revisión que no hacía falta): salen como
  ACEPTABLE, que cuenta como revisión innecesaria y no como fallo.
- --nuevos añade un sufijo al Message-ID para que n8n los trate como correos nuevos
  (sin él, un segundo envío devuelve "duplicado").
- --hoy cambia la fecha de cada correo a hoy, con la misma hora (para la demo: una cola de hoy).
"""

import argparse
import email.utils
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from email.parser import BytesHeaderParser
from pathlib import Path

from entorno import leer_env

RAIZ = Path(__file__).resolve().parent.parent
URL_POR_DEFECTO = "http://localhost:5678/webhook/pruebas/eml"
CONFIGURACIONES = ("solo_reglas", "solo_ia", "hibrido")


def fecha(eml: bytes):
    cabeceras = BytesHeaderParser().parsebytes(eml)
    return email.utils.parsedate_to_datetime(cabeceras["Date"])


def con_message_id_nuevo(eml: bytes, sufijo: str) -> bytes:
    cabeceras, separador, cuerpo = eml.partition(b"\r\n\r\n")
    cabeceras = re.sub(rb"(?im)^(Message-ID:\s*<)([^@>]+)@", rb"\g<1>\g<2>." + sufijo.encode() + rb"@", cabeceras, count=1)
    return cabeceras + separador + cuerpo


def con_fecha_de_hoy(eml: bytes) -> bytes:
    from datetime import datetime
    from zoneinfo import ZoneInfo

    original = fecha(eml)
    hoy = datetime.now(ZoneInfo("Europe/Madrid")).date()
    nueva = email.utils.format_datetime(original.replace(year=hoy.year, month=hoy.month, day=hoy.day))
    cabeceras, separador, cuerpo = eml.partition(b"\r\n\r\n")
    cabeceras = re.sub(rb"(?im)^Date:[^\r\n]*", b"Date: " + nueva.encode(), cabeceras, count=1)
    return cabeceras + separador + cuerpo


def con_configuracion(url, configuracion):
    if not configuracion:
        return url
    partes = urllib.parse.urlsplit(url)
    consulta = urllib.parse.parse_qsl(partes.query) + [("configuracion", configuracion)]
    return urllib.parse.urlunsplit(partes._replace(query=urllib.parse.urlencode(consulta)))


def enviar(url, token, eml: bytes):
    peticion = urllib.request.Request(
        url, data=eml, method="POST",
        headers={"X-Pruebas-Token": token, "Content-Type": "message/rfc822"},
    )
    with urllib.request.urlopen(peticion, timeout=120) as respuesta:
        return json.loads(respuesta.read())


class LineasDelPedido:
    """Lee las líneas de un pedido del ERP. Solo se conecta si hace falta comparar alguna."""

    def __init__(self):
        self._conexion = None

    def __call__(self, pedido):
        if self._conexion is None:
            import psycopg

            url = leer_env().get("SUPABASE_DB_URL")
            if not url:
                sys.exit("Falta SUPABASE_DB_URL en .env para comparar las líneas del pedido")
            self._conexion = psycopg.connect(url, autocommit=True)
        filas = self._conexion.execute(
            "select producto, cantidad from erp.lineas_pedido where pedido = %s", (pedido,)).fetchall()
        return Counter((producto, int(cantidad)) for producto, cantidad in filas)


def evaluar(resultado, esperado, lineas_del_pedido):
    """Devuelve ("OK" | "ACEPTABLE" | "FALLO", diferencias con la salida esperada).

    ACEPTABLE: no es la salida esperada, pero es una de las "aceptables" del caso (una revisión segura que no
    hacía falta, 05 sección 7). Cuenta como revisión innecesaria, no como fallo.
    """
    diferencias = comparar(resultado, esperado, lineas_del_pedido)
    if not diferencias:
        return "OK", []
    codigos = sorted({m["codigo"] for m in resultado.get("motivos") or []})
    for aceptable in esperado.get("aceptables", []):
        if resultado["salida"] == aceptable["salida"] and codigos == sorted(aceptable["motivos"]):
            return "ACEPTABLE", diferencias
    return "FALLO", diferencias


def comparar(resultado, esperado, lineas_del_pedido):
    """Devuelve la lista de diferencias con lo esperado (vacía si todo coincide)."""
    diferencias = []
    codigos = sorted({m["codigo"] for m in resultado.get("motivos") or []})
    if resultado["salida"] != esperado["salida"]:
        diferencias.append(f"salida {resultado['salida']}, esperada {esperado['salida']}")
    if codigos != sorted(esperado["motivos"]):
        diferencias.append(f"motivos {', '.join(codigos) or '-'}, esperados {', '.join(esperado['motivos']) or '-'}")
    if "lineas" in esperado and resultado.get("pedido"):
        hay = lineas_del_pedido(resultado["pedido"])
        debe = Counter((producto, cantidad) for producto, cantidad in esperado["lineas"])
        faltan = sorted((debe - hay).elements())
        sobran = sorted((hay - debe).elements())
        if faltan:
            diferencias.append("faltan " + ", ".join(f"{p} x{c}" for p, c in faltan))
        if sobran:
            diferencias.append("sobran " + ", ".join(f"{p} x{c}" for p, c in sobran))
    return diferencias


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("ruta", type=Path, help="carpeta con .eml o un solo .eml")
    parser.add_argument("--url", default=URL_POR_DEFECTO)
    parser.add_argument("--configuracion", choices=CONFIGURACIONES, help="por defecto, la de n8n (hibrido)")
    parser.add_argument("--nuevos", action="store_true", help="Message-ID nuevo en cada envío")
    parser.add_argument("--hoy", action="store_true", help="fecha de hoy, con la misma hora")
    args = parser.parse_args()

    token = leer_env().get("PRUEBAS_WEBHOOK_TOKEN")
    if not token:
        sys.exit("Falta PRUEBAS_WEBHOOK_TOKEN en .env")

    carpeta = args.ruta if args.ruta.is_dir() else args.ruta.parent
    ficheros = carpeta.glob("*.eml") if args.ruta.is_dir() else [args.ruta]
    correos = sorted(((fecha(p.read_bytes()), p) for p in ficheros), key=lambda par: par[0])
    if not correos:
        sys.exit(f"No hay .eml en {args.ruta}")
    ruta_esperado = carpeta / "esperado.json"
    esperado = json.loads(ruta_esperado.read_text()) if ruta_esperado.exists() else {}
    url = con_configuracion(args.url, args.configuracion)
    configuracion = args.configuracion or "hibrido"
    sufijo = time.strftime("%Y%m%d%H%M%S")
    lineas_del_pedido = LineasDelPedido()

    print(f"Configuración: {configuracion}")
    fallos = 0
    for _, ruta in correos:
        eml = ruta.read_bytes()
        if args.nuevos:
            eml = con_message_id_nuevo(eml, sufijo)
        if args.hoy:
            eml = con_fecha_de_hoy(eml)
        try:
            resultado = enviar(url, token, eml)
        except urllib.error.HTTPError as e:
            print(f"{ruta.name:32} HTTP {e.code}: {e.read().decode(errors='replace')[:200]}")
            fallos += 1
            continue
        except urllib.error.URLError as e:
            sys.exit(f"No se pudo conectar con n8n ({url}): {e.reason}")

        if resultado.get("duplicado"):
            print(f"{ruta.name:32} caso {resultado['caso']:>4}  ya registrado (usa --nuevos para reenviarlo)")
            continue

        codigos = sorted({m["codigo"] for m in resultado.get("motivos") or []})
        linea = (f"{ruta.name:32} caso {resultado['caso']:>4}  {resultado['salida']:11}"
                 f" pedido {resultado.get('pedido') or '-':>4}  motivos {', '.join(codigos) or '-'}")
        e = esperado.get(ruta.name)
        if e:
            estado, diferencias = evaluar(resultado, e, lineas_del_pedido)
            fallos += estado == "FALLO"
            if estado == "OK":
                linea += "  OK"
            elif estado == "ACEPTABLE":
                linea += f"  ACEPTABLE (salida segura; esperado {e['salida']})"
            else:
                linea += "  FALLO: " + "; ".join(diferencias)
        print(linea)

    sys.exit(1 if fallos else 0)


if __name__ == "__main__":
    main()
