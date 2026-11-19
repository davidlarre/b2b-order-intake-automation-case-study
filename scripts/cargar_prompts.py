"""Carga los prompts de extraction/ en intake.prompt_versiones (ADR 0002).

Uso:
    uv run scripts/cargar_prompts.py            # carga las versiones nuevas, sin activarlas
    uv run scripts/cargar_prompts.py --activar  # además, activa la versión que hay ahora en los ficheros

Cada carpeta de extraction/ es un prompt: prompt.md (con la marca {correo}), esquema.json,
ejemplos.json y config.json (modelo). El hash cubre los cuatro: cambiar cualquiera crea una versión nueva.
Si el hash ya está cargado, no hace nada.
"""

import argparse
import hashlib
import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
EXTRACTION = RAIZ / "extraction"


def leer_prompt(carpeta: Path) -> dict:
    texto = (carpeta / "prompt.md").read_text()
    # El fichero acaba en salto de línea, como todo fichero de texto; el prompt no.
    if texto.endswith("\n"):
        texto = texto[:-1]
    if texto.count("{correo}") != 1:
        raise ValueError(f"{carpeta.name}/prompt.md tiene que contener una sola marca {{correo}}")
    return {
        "prompt": carpeta.name,
        "texto": texto,
        "esquema": json.loads((carpeta / "esquema.json").read_text()),
        "ejemplos": json.loads((carpeta / "ejemplos.json").read_text()),
        "modelo": json.loads((carpeta / "config.json").read_text())["modelo"],
    }


def hash_de(version: dict) -> str:
    canonico = json.dumps(
        {k: version[k] for k in ("texto", "esquema", "ejemplos", "modelo")},
        sort_keys=True, ensure_ascii=False, separators=(",", ":"),
    )
    return hashlib.sha256(canonico.encode()).hexdigest()


def cargar(cur, carpeta: Path, activar: bool) -> dict:
    """Carga la versión de los ficheros si es nueva y, si se pide, la activa. Devuelve su estado."""
    from psycopg.types.json import Jsonb

    version = leer_prompt(carpeta)
    h = hash_de(version)
    cur.execute("select version, activa from intake.prompt_versiones where hash = %s", (h,))
    fila = cur.fetchone()
    nueva = fila is None
    if nueva:
        cur.execute(
            "insert into intake.prompt_versiones (prompt, version, hash, texto, esquema, ejemplos, modelo)"
            " select %s, coalesce(max(version), 0) + 1, %s, %s, %s, %s, %s"
            " from intake.prompt_versiones where prompt = %s returning version",
            (version["prompt"], h, version["texto"], Jsonb(version["esquema"]), Jsonb(version["ejemplos"]),
             version["modelo"], version["prompt"]),
        )
        numero, activa = cur.fetchone()[0], False
    else:
        numero, activa = fila
    if activar and not activa:
        cur.execute("update intake.prompt_versiones set activa = false where prompt = %s and activa",
                    (version["prompt"],))
        cur.execute("update intake.prompt_versiones set activa = true where hash = %s", (h,))
        activa = True
    return {"prompt": version["prompt"], "version": numero, "hash": h, "nueva": nueva, "activa": activa}


def main():
    import psycopg

    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--activar", action="store_true")
    args = parser.parse_args()

    from entorno import leer_env

    url = leer_env().get("SUPABASE_DB_URL")
    if not url:
        sys.exit("Falta SUPABASE_DB_URL en .env")

    with psycopg.connect(url) as conn, conn.cursor() as cur:
        for carpeta in sorted(p for p in EXTRACTION.iterdir() if p.is_dir()):
            r = cargar(cur, carpeta, args.activar)
            estado = "nueva" if r["nueva"] else "ya cargada"
            print(f"{r['prompt']}: versión {r['version']} ({estado}, {'activa' if r['activa'] else 'inactiva'})"
                  f"  hash {r['hash'][:12]}")


if __name__ == "__main__":
    main()
