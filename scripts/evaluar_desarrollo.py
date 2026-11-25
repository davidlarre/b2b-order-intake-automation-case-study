"""Pasa los 20 correos de desarrollo de evaluacion-v2 por el flujo de n8n y los compara con sus etiquetas.

Uso:
    uv run scripts/evaluar_desarrollo.py [--configuracion hibrido] [--pausa 8] [--salida eval/ejecuciones/x.jsonl]

- Solo desarrollo: no admite la prueba, que se ejecuta una sola vez y desde otro sitio.
- Entra por la puerta de pruebas, con Message-ID nuevo, por orden de Date.
- Si Gemini dice que se ha agotado la cuota (429), o falla tres veces seguidas (caída general, 04 sección 2.6),
  se para: no insiste.
- Guarda un JSONL con lo que dio cada caso, la clasificación en bruto y la versión de cada prompt.
"""

import argparse
import json
import sys
import time
from collections import Counter
from pathlib import Path

import yaml

from entorno import RAIZ, leer_env
from enviar_eml import CONFIGURACIONES, URL_POR_DEFECTO, con_configuracion, con_message_id_nuevo, enviar, fecha

DESARROLLO = RAIZ / "data" / "synthetic" / "evaluacion-v2" / "desarrollo"


def nota(etiqueta, resultado, tipo, lineas):
    """(nota del tipo, nota de la salida, diferencias). El M03 va aparte: es el servicio, no el sistema."""
    codigos = sorted({m["codigo"] for m in resultado["motivos"]})
    if "M03" in codigos:
        return "M03", "M03", []
    if tipo is None:
        nota_tipo = "-"
    elif tipo == etiqueta["tipo"]:
        nota_tipo = "OK"
    else:
        nota_tipo = "ACEPTABLE" if tipo in etiqueta["tipos_aceptables"] else "FALLO"

    esperados = sorted({m["codigo"] for m in etiqueta["motivos"] if m["momento"] == "inicial"})
    diferencias = []
    if resultado["salida"] != etiqueta["salida"]["inicial"]:
        diferencias.append(f"salida {resultado['salida']}, esperada {etiqueta['salida']['inicial']}")
    if codigos != esperados and not etiqueta.get("motivos_sin_codigo"):
        diferencias.append(f"motivos {', '.join(codigos) or '-'}, esperados {', '.join(esperados) or '-'}")
    if resultado.get("pedido"):
        debe = Counter((l["producto"], l["cantidad_uv"]) for l in etiqueta["lineas"])
        if lineas != debe:
            diferencias.append("líneas " + ", ".join(f"{p} x{c}" for p, c in sorted((lineas - debe).elements()))
                               + " en lugar de " + ", ".join(f"{p} x{c}" for p, c in sorted((debe - lineas).elements())))
    if not diferencias:
        return nota_tipo, "OK", []
    aceptable = any(a["salida"] == resultado["salida"] and sorted(a["motivos"]) == codigos
                    for a in etiqueta["salida"]["aceptables"])
    return nota_tipo, "ACEPTABLE" if aceptable else "FALLO", diferencias


def main():
    import psycopg

    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--configuracion", choices=CONFIGURACIONES, default="hibrido")
    parser.add_argument("--pausa", type=float, default=8)
    parser.add_argument("--salida", type=Path)
    args = parser.parse_args()
    env = leer_env()
    url = con_configuracion(URL_POR_DEFECTO, args.configuracion)
    sufijo = time.strftime("%Y%m%d%H%M%S")
    conn = psycopg.connect(env["SUPABASE_DB_URL"], autocommit=True)
    versiones = dict(conn.execute("select prompt, hash from intake.prompt_versiones where activa").fetchall())
    filas = []
    print(f"Configuración: {args.configuracion}")
    for i, ruta in enumerate(sorted((DESARROLLO / "correos").glob("*.eml"), key=lambda p: fecha(p.read_bytes()))):
        if i:
            time.sleep(args.pausa)
        etiqueta = yaml.safe_load((DESARROLLO / "etiquetas" / f"{ruta.stem}.yaml").read_text())
        r = enviar(url, env["PRUEBAS_WEBHOOK_TOKEN"], con_message_id_nuevo(ruta.read_bytes(), sufijo))
        clasificacion = conn.execute("select resultado, modelo, tokens_entrada, tokens_salida from intake.extracciones"
                                     " where caso = %s and prompt = 'clasificacion'", (r["caso"],)).fetchone()
        error = conn.execute("select detalle ->> 'error' from intake.motivos where caso = %s and codigo = 'M03'",
                             (r["caso"],)).fetchone()
        lineas = Counter((p, int(c)) for p, c in conn.execute(
            "select producto, cantidad from erp.lineas_pedido where pedido = %s", (r.get("pedido"),)).fetchall())
        tipo = clasificacion[0]["tipo"] if clasificacion else None
        n_tipo, n_salida, dif = nota(etiqueta, r, tipo, lineas)
        fila = {"caso": ruta.stem, "configuracion": args.configuracion, "tipo": tipo, "nota_tipo": n_tipo,
                "salida": r["salida"], "motivos": sorted({m["codigo"] for m in r["motivos"]}),
                "nota_salida": n_salida, "diferencias": dif, "depende_de": etiqueta["depende_de"],
                "lineas": sorted(lineas.elements()),
                "clasificacion": clasificacion and {"respuesta": clasificacion[0], "modelo": clasificacion[1],
                                                    "tokens_entrada": clasificacion[2], "tokens_salida": clasificacion[3]},
                "error": error and error[0], "prompts": versiones}
        filas.append(fila)
        fuera = f"  [fuera de alcance: {', '.join(etiqueta['depende_de'])}]" if etiqueta["depende_de"] else ""
        print(f"{ruta.stem}  tipo {tipo or '-':22} {n_tipo:9} salida {r['salida']:11} motivos {', '.join(fila['motivos']) or '-':8}"
              f" {n_salida}{': ' + '; '.join(dif) if dif else ''}{fuera}", flush=True)
        if error and error[0] and "429" in error[0][:10]:
            print("Cuota de Gemini agotada: se para aquí.")
            break
        if [f["nota_salida"] for f in filas[-3:]] == ["M03"] * 3:
            print("Tres fallos seguidos del servicio: se para aquí.")
            break
    if args.salida:
        args.salida.parent.mkdir(parents=True, exist_ok=True)
        args.salida.write_text("".join(json.dumps(f, ensure_ascii=False) + "\n" for f in filas))
    for campo in ("nota_tipo", "nota_salida"):
        print(campo, dict(Counter(f[campo] for f in filas)), "· en alcance:",
              dict(Counter(f[campo] for f in filas if not f["depende_de"])))
    sys.exit(1 if len(filas) < 20 else 0)


if __name__ == "__main__":
    main()
