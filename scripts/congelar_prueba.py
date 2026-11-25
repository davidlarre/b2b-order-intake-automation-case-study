"""Manifiesto SHA-256 de la prueba congelada (05, sección 8).

Uso:
    uv run scripts/congelar_prueba.py              # comprueba que nada ha cambiado
    uv run scripts/congelar_prueba.py --congelar   # escribe el manifiesto (solo si no existe)

Cubre los correos, fichas y etiquetas de la prueba, la guía y el esquema, el alcance fijado antes de congelar y los
datos maestros con los que se evalúa. Un fichero cambiado, añadido o borrado es una diferencia.
"""

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import date

from entorno import RAIZ

EVALUACION = RAIZ / "data" / "synthetic" / "evaluacion-v2"
MANIFIESTO = EVALUACION / "manifiesto-prueba.json"
SUELTOS = [
    EVALUACION / "guia-etiquetado.md", EVALUACION / "esquema-etiqueta.json",
    RAIZ / "eval" / "alcance-prueba-v2.md",
    RAIZ / "supabase" / "seed.sql", RAIZ / "supabase" / "seeds" / "maestros.sql",
]


def ficheros(raiz=RAIZ):
    de_prueba = (p for p in (raiz / EVALUACION.relative_to(RAIZ) / "prueba").rglob("*")
                 if p.is_file() and p.name != ".DS_Store")
    sueltos = [raiz / s.relative_to(RAIZ) for s in SUELTOS]
    return {p.relative_to(raiz).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted([*de_prueba, *(s for s in sueltos if s.exists())])}


def hash_total(hashes):
    return hashlib.sha256("".join(f"{h}  {r}\n" for r, h in sorted(hashes.items())).encode()).hexdigest()


def diferencias(manifiesto, hashes):
    congelados = manifiesto["ficheros"]
    salida = [f"falta {r}" for r in sorted(set(congelados) - set(hashes))]
    salida += [f"nuevo {r}" for r in sorted(set(hashes) - set(congelados))]
    salida += [f"cambiado {r}" for r in sorted(set(hashes) & set(congelados)) if hashes[r] != congelados[r]]
    if hash_total(congelados) != manifiesto["hash_total"]:
        salida.append("el hash total del manifiesto no es el de sus ficheros")
    return salida


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--congelar", action="store_true")
    args = parser.parse_args()
    hashes = ficheros()
    if args.congelar:
        if MANIFIESTO.exists():
            sys.exit("La prueba ya está congelada: un cambio es una prueba nueva, con otro manifiesto y otro tag")
        commit = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=RAIZ).stdout.strip()
        MANIFIESTO.write_text(json.dumps({
            "tag": "prueba-v2", "congelada": date.today().isoformat(), "version_del_sistema": commit,
            "generador": "claude-opus-5-5 (Claude Code); montaje con scripts/generar_correos.py",
            "hash_total": hash_total(hashes), "ficheros": hashes}, indent=2, ensure_ascii=False) + "\n")
        print(f"{len(hashes)} ficheros congelados, hash total {hash_total(hashes)}")
        return
    dif = diferencias(json.loads(MANIFIESTO.read_text()), hashes)
    if dif:
        sys.exit("La prueba no es la congelada:\n  " + "\n  ".join(dif))
    print(f"La prueba es la congelada: {len(hashes)} ficheros")


if __name__ == "__main__":
    main()
