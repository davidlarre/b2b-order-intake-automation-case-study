"""Lectura del .env de la raíz, compartida por los scripts y los tests. Las variables de entorno mandan."""

import os
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent


def leer_env() -> dict:
    valores = {}
    ruta = RAIZ / ".env"
    if ruta.exists():
        for linea in ruta.read_text().splitlines():
            if "=" in linea and not linea.lstrip().startswith("#"):
                clave, valor = linea.split("=", 1)
                valores[clave.strip()] = valor.strip().strip('"').strip("'")
    return {**valores, **os.environ}
