"""Compara los 20 correos de la v1.1 con lo que se publicó (eval/resultados-v1-1.md, pasada 3).

Uso:
    uv run scripts/regresion_v1_1.py [--pausa 6] [--configuracion hibrido]

Los envía con Message-ID nuevo, en las tres configuraciones, y compara salida, motivos y veredicto (que incluye
las líneas del pedido). Lo que cambie se imprime; un M03 no es un cambio del sistema: se cuenta aparte.
"""

import argparse
import re
import subprocess
import sys

from entorno import RAIZ

CARPETAS = ("corte-vertical", "extraccion", "evaluacion-v1")
LINEA = re.compile(r"^(\S+\.eml)\s+caso\s+\d+\s+(\S+)\s+pedido\s+\S+\s+motivos (\S+(?:, \S+)*)\s{2}(.+)$")


def leer(texto):
    """{(configuracion, correo): (salida, motivos, veredicto)}"""
    configuracion, resultado = None, {}
    for linea in texto.splitlines():
        if linea.startswith("Configuración: "):
            configuracion = linea.split(": ")[1].strip()
        elif m := LINEA.match(linea):
            resultado[(configuracion, m[1])] = (m[2], m[3], m[4])
    return resultado


def publicado():
    md = (RAIZ / "eval" / "resultados-v1-1.md").read_text()
    bloque = re.search(r"pasada 3 \(la publicada\)</summary>\s+```\n(.*?)```", md, re.S).group(1)
    return leer(bloque)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--pausa", default="6")
    parser.add_argument("--configuracion", choices=("solo_reglas", "solo_ia", "hibrido"))
    args = parser.parse_args()
    antes = publicado()
    ahora = {}
    for c in [args.configuracion] if args.configuracion else ("solo_reglas", "solo_ia", "hibrido"):
        for carpeta in CARPETAS:
            pausa = "0" if c == "solo_reglas" else args.pausa
            p = subprocess.run([sys.executable, str(RAIZ / "scripts" / "enviar_eml.py"),
                                str(RAIZ / "data" / "synthetic" / carpeta), "--configuracion", c, "--nuevos",
                                "--pausa", pausa], capture_output=True, text=True)
            print(p.stdout, end="", flush=True)
            if p.stderr:
                print(p.stderr, file=sys.stderr)
            ahora.update(leer(p.stdout))
    esperados = {k: v for k, v in antes.items() if not args.configuracion or k[0] == args.configuracion}
    cambios = [(k, v, ahora.get(k)) for k, v in esperados.items() if ahora.get(k) != v]
    print(f"\n{len(esperados)} resultados comparados, {len(cambios)} distintos de la v1.1")
    for (c, correo), v, n in cambios:
        print(f"  {c:12} {correo:34} {v}  ->  {n}")
    sys.exit(1 if cambios else 0)


if __name__ == "__main__":
    main()
