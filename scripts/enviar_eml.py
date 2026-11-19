"""Envía los .eml de una carpeta a la entrada de pruebas de n8n y muestra el resultado de cada uno.

Uso:
    uv run scripts/enviar_eml.py data/synthetic/corte-vertical [--nuevos] [--url URL]
    uv run scripts/enviar_eml.py data/synthetic/extraccion/04-excel-xlsx.eml --url URL_DE_PRUEBA

- Acepta una carpeta o un solo .eml. Los envía por orden de su cabecera Date, como la evaluación (04, sección 7).
- Si la carpeta tiene un esperado.json, compara la salida y los motivos con lo esperado.
- --nuevos añade un sufijo al Message-ID para que n8n los trate como correos nuevos
  (sin él, un segundo envío devuelve "duplicado").
"""

import argparse
import email.utils
import json
import re
import sys
import time
import urllib.error
import urllib.request
from email.parser import BytesHeaderParser
from pathlib import Path

from entorno import leer_env

RAIZ = Path(__file__).resolve().parent.parent
URL_POR_DEFECTO = "http://localhost:5678/webhook/pruebas/eml"


def fecha(eml: bytes):
    cabeceras = BytesHeaderParser().parsebytes(eml)
    return email.utils.parsedate_to_datetime(cabeceras["Date"])


def con_message_id_nuevo(eml: bytes, sufijo: str) -> bytes:
    cabeceras, separador, cuerpo = eml.partition(b"\r\n\r\n")
    cabeceras = re.sub(rb"(?im)^(Message-ID:\s*<)([^@>]+)@", rb"\g<1>\g<2>." + sufijo.encode() + rb"@", cabeceras, count=1)
    return cabeceras + separador + cuerpo


def enviar(url, token, eml: bytes):
    peticion = urllib.request.Request(
        url, data=eml, method="POST",
        headers={"X-Pruebas-Token": token, "Content-Type": "message/rfc822"},
    )
    with urllib.request.urlopen(peticion, timeout=120) as respuesta:
        return json.loads(respuesta.read())


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("ruta", type=Path, help="carpeta con .eml o un solo .eml")
    parser.add_argument("--url", default=URL_POR_DEFECTO)
    parser.add_argument("--nuevos", action="store_true", help="Message-ID nuevo en cada envío")
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
    sufijo = time.strftime("%Y%m%d%H%M%S")

    fallos = 0
    for _, ruta in correos:
        eml = ruta.read_bytes()
        if args.nuevos:
            eml = con_message_id_nuevo(eml, sufijo)
        try:
            resultado = enviar(args.url, token, eml)
        except urllib.error.HTTPError as e:
            print(f"{ruta.name:32} HTTP {e.code}: {e.read().decode(errors='replace')[:200]}")
            fallos += 1
            continue
        except urllib.error.URLError as e:
            sys.exit(f"No se pudo conectar con n8n ({args.url}): {e.reason}")

        if resultado.get("duplicado"):
            print(f"{ruta.name:32} caso {resultado['caso']:>4}  ya registrado (usa --nuevos para reenviarlo)")
            continue

        codigos = sorted({m["codigo"] for m in resultado.get("motivos") or []})
        linea = (f"{ruta.name:32} caso {resultado['caso']:>4}  {resultado['salida']:11}"
                 f" pedido {resultado.get('pedido') or '-':>4}  motivos {', '.join(codigos) or '-'}")
        if ruta.name in esperado:
            e = esperado[ruta.name]
            ok = resultado["salida"] == e["salida"] and codigos == sorted(e["motivos"])
            fallos += not ok
            linea += "  OK" if ok else f"  FALLO (esperado {e['salida']}, motivos {', '.join(e['motivos']) or '-'})"
        print(linea)

    sys.exit(1 if fallos else 0)


if __name__ == "__main__":
    main()
