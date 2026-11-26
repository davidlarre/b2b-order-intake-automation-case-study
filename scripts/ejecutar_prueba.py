"""Ejecución única de la prueba congelada (tag prueba-v2.1), una configuración cada vez (eval/alcance-prueba-v2.md).

Uso:
    uv run scripts/ejecutar_prueba.py --configuracion hibrido
    uv run scripts/ejecutar_prueba.py --configuracion hibrido --motivo "intento 1 cortado por 429 en P31"

Antes de enviar nada comprueba que la prueba es la del manifiesto, que el tag existe, que el código está
commiteado, que los prompts activos son los de extraction/ y que la base está recién cargada (sin casos).

- Envía los 66 .eml por orden de su cabecera Date, con su Message-ID original.
- Guarda en eval/ejecuciones/prueba-v2.1-<configuracion>-intento<N>.jsonl una cabecera, una fila por .eml y un
  cierre con el estado: "completa" o "cortada".
- Se corta en el primer fallo de infraestructura: un M03 por 429 o 503 de Gemini, o un error HTTP de n8n. Una
  pasada cortada no vale: se repite entera, con la base recargada, y el intento siguiente exige --motivo.
- Un M03 que no es de infraestructura (respuesta no válida) no corta: es un resultado y va en su columna.
- Con una pasada completa de esa configuración ya guardada, se niega a ejecutar otra.
"""

import argparse
import json
import subprocess
import sys
import time
import urllib.error
from datetime import datetime

from cargar_prompts import EXTRACTION, hash_de, leer_prompt
from congelar_prueba import EVALUACION, MANIFIESTO, diferencias, ficheros
from entorno import RAIZ, leer_env
from enviar_eml import CONFIGURACIONES, URL_POR_DEFECTO, con_configuracion, enviar, fecha

TAG = "prueba-v2.1"
CORREOS = EVALUACION / "prueba" / "correos"
EJECUCIONES = RAIZ / "eval" / "ejecuciones"


def es_de_infraestructura(error):
    """Un 429 o un 503 de Gemini. Con un 429, n8n sustituye el mensaje por su propio consejo."""
    return bool(error) and (error.startswith(("429", "503")) or "spacing your requests" in error
                            or "high demand" in error)


def numero(ruta):
    return int(ruta.stem.rsplit("intento", 1)[1])


def intentos(configuracion, carpeta=EJECUCIONES):
    return sorted(carpeta.glob(f"{TAG}-{configuracion}-intento*.jsonl"), key=numero)


def estado(ruta):
    """"completa" solo si la última línea lo dice; una pasada interrumpida, o vacía, está cortada."""
    lineas = ruta.read_text().splitlines()
    return (lineas and json.loads(lineas[-1]).get("estado")) or "cortada"


def git(*args):
    return subprocess.run(["git", *args], capture_output=True, text=True, cwd=RAIZ, check=True).stdout.rstrip("\n")


def sin_commitear(porcelana):
    """Rutas de `git status --porcelain` fuera de eval/ejecuciones/ (donde se escriben las pasadas)."""
    return [l for l in porcelana.splitlines() if l and not l[3:].startswith("eval/ejecuciones/")]


def comprobar(configuracion, motivo, conn):
    """Devuelve los metadatos de la ejecución, o sale con el motivo por el que no se puede ejecutar."""
    manifiesto = json.loads(MANIFIESTO.read_text())
    if dif := diferencias(manifiesto, ficheros()):
        sys.exit("La prueba no es la congelada:\n  " + "\n  ".join(dif))
    if manifiesto["tag"] != TAG or not git("tag", "--list", TAG):
        sys.exit(f"Falta el tag {TAG}, o el manifiesto no es el suyo")
    if subprocess.run(["git", "merge-base", "--is-ancestor", TAG, "HEAD"], cwd=RAIZ).returncode:
        sys.exit(f"HEAD no desciende de {TAG}")
    if sucio := sin_commitear(git("status", "--porcelain")):
        sys.exit("Hay cambios sin commitear: la ejecución tiene que corresponder a un commit\n  " + "\n  ".join(sucio))
    previos = intentos(configuracion)
    if any(estado(p) == "completa" for p in previos):
        sys.exit(f"{configuracion} ya tiene una pasada completa: la prueba se ejecuta una sola vez")
    if previos and not motivo:
        sys.exit(f"Hay {len(previos)} intento(s) cortado(s) de {configuracion}: el siguiente necesita --motivo")
    if conn.execute("select count(*) from intake.casos").fetchone()[0]:
        sys.exit("La base no está recién cargada: hay casos (supabase db reset y cargar_prompts.py --activar)")
    activos = dict(conn.execute("select prompt, hash from intake.prompt_versiones where activa").fetchall())
    en_ficheros = {p.name: hash_de(leer_prompt(p)) for p in EXTRACTION.iterdir() if p.is_dir()}
    if activos != en_ficheros:
        sys.exit("Los prompts activos no son los de extraction/ (cargar_prompts.py --activar)")
    return {"tag": TAG, "hash_total": manifiesto["hash_total"], "commit": git("rev-parse", "HEAD"),
            "configuracion": configuracion, "intento": max(map(numero, previos), default=0) + 1, "motivo_repeticion": motivo,
            "prompts": activos, "inicio": datetime.now().astimezone().isoformat(timespec="seconds")}


def main():
    import psycopg

    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--configuracion", choices=CONFIGURACIONES, required=True)
    parser.add_argument("--motivo", help="por qué se repite: el fallo de infraestructura del intento anterior")
    parser.add_argument("--pausa", type=float, help="segundos entre correos (por defecto 10; 0 en solo_reglas)")
    args = parser.parse_args()
    env = leer_env()
    conn = psycopg.connect(env["SUPABASE_DB_URL"], autocommit=True)
    cabecera = comprobar(args.configuracion, args.motivo, conn)
    pausa = args.pausa if args.pausa is not None else (0 if args.configuracion == "solo_reglas" else 10)
    salida = EJECUCIONES / f"{TAG}-{args.configuracion}-intento{cabecera['intento']}.jsonl"
    url = con_configuracion(URL_POR_DEFECTO, args.configuracion)
    correos = sorted(CORREOS.glob("*.eml"), key=lambda p: fecha(p.read_bytes()))
    print(f"{TAG} · {args.configuracion} · intento {cabecera['intento']} · {len(correos)} .eml → {salida.name}")

    EJECUCIONES.mkdir(parents=True, exist_ok=True)
    with salida.open("x") as f:
        def escribir(fila):
            f.write(json.dumps(fila, ensure_ascii=False) + "\n")
            f.flush()

        escribir({"cabecera": {**cabecera, "pausa": pausa}})
        corte = None
        for i, ruta in enumerate(correos):
            if i and pausa:
                time.sleep(pausa)
            try:
                r = enviar(url, env["PRUEBAS_WEBHOOK_TOKEN"], ruta.read_bytes())
            except urllib.error.HTTPError as e:
                corte = f"HTTP {e.code} de n8n en {ruta.stem}: {e.read().decode(errors='replace')[:200]}"
                break
            except urllib.error.URLError as e:
                corte = f"n8n no responde en {ruta.stem}: {e.reason}"
                break
            except (TimeoutError, json.JSONDecodeError) as e:
                corte = f"Sin respuesta válida de n8n en {ruta.stem}: {e!r}"
                break
            if "salida" not in r:
                corte = f"Respuesta inesperada de n8n en {ruta.stem}: {json.dumps(r)[:200]}"
                break
            caso = r["caso"]
            extracciones = [
                {"prompt": p, "valido": v, "modelo": m, "resultado": res, "tokens_entrada": te, "tokens_salida": ts}
                for p, v, m, res, te, ts in conn.execute(
                    "select prompt, valido, modelo, resultado, tokens_entrada, tokens_salida from intake.extracciones"
                    " where caso = %s order by id", (caso,)).fetchall()]
            error = conn.execute("select detalle ->> 'error' from intake.motivos where caso = %s and codigo = 'M03'",
                                 (caso,)).fetchone()
            error = error and error[0]
            lineas = conn.execute("select producto, cantidad from erp.lineas_pedido where pedido = %s order by linea",
                                  (r.get("pedido"),)).fetchall()
            clasificacion = next((x["resultado"] for x in extracciones if x["prompt"] == "clasificacion"), None)
            fila = {"eml": ruta.stem, "caso": caso, "salida": r["salida"], "pedido": r.get("pedido"),
                    "motivos": sorted({m["codigo"] for m in r.get("motivos") or []}),
                    "tipo": clasificacion and clasificacion.get("tipo"),
                    "destino": clasificacion and clasificacion.get("destino"),
                    "lineas": [[p, int(c)] for p, c in lineas], "error": error, "extracciones": extracciones,
                    "hora": datetime.now().astimezone().isoformat(timespec="seconds")}
            escribir(fila)
            print(f"{ruta.stem:5} caso {caso:>4}  tipo {fila['tipo'] or '-':22} {fila['salida']:11}"
                  f" motivos {', '.join(fila['motivos']) or '-'}", flush=True)
            if es_de_infraestructura(error):
                corte = f"M03 de infraestructura en {ruta.stem}: {error[:200]}"
                break
        escribir({"estado": "cortada" if corte else "completa", "corte": corte,
                  "fin": datetime.now().astimezone().isoformat(timespec="seconds")})
    print(f"Cortada: {corte}. No vale: se repite entera, con la base recargada." if corte else "Completa.")
    sys.exit(1 if corte else 0)


if __name__ == "__main__":
    main()
