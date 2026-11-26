"""Tablas del informe de la prueba v2, desde las pasadas completas de eval/ejecuciones/ y las etiquetas congeladas.

Uso:
    uv run scripts/informe_prueba.py > /tmp/tablas.md

Solo lee: no llama a n8n ni a la base. Cada caso se mide por su primer .eml (salida inicial); los .eml de
respuesta (P14b…P18c) van en su propia tabla. La métrica principal es la de eval/alcance-prueba-v2.md.
"""

import json
import sys
from collections import Counter

import yaml

from ejecutar_prueba import EJECUCIONES, TAG, estado, intentos
from enviar_eml import CONFIGURACIONES
from evaluar_desarrollo import nota
from congelar_prueba import EVALUACION

TIPOS = ["pedido_nuevo", "modificacion_anulacion", "consulta", "reclamacion", "otros", "dudoso"]


def etiquetas():
    return {p.stem: yaml.safe_load(p.read_text()) for p in sorted((EVALUACION / "prueba" / "etiquetas").glob("*.yaml"))}


def pasada(configuracion, carpeta=EJECUCIONES):
    """(cabecera, {eml: fila}) de la pasada completa, o None si no la hay."""
    completas = [p for p in intentos(configuracion, carpeta) if estado(p) == "completa"]
    if not completas:
        return None
    filas = [json.loads(l) for l in completas[0].read_text().splitlines()]
    return filas[0]["cabecera"], {f["eml"]: f for f in filas[1:-1]}


def medir(etiqueta, fila):
    """Nota del tipo y de la salida, y si es un pedido automático erróneo o indebido."""
    lineas = Counter((p, c) for p, c in fila["lineas"])
    resultado = {"salida": fila["salida"], "motivos": [{"codigo": c} for c in fila["motivos"]], "pedido": fila["pedido"]}
    n_tipo, n_salida, dif = nota(etiqueta, resultado, fila["tipo"], lineas)
    automatico = fila["salida"] == "automatico" and bool(fila["pedido"])
    debe = Counter((l["producto"], l["cantidad_uv"]) for l in etiqueta["lineas"])
    return {"nota_tipo": n_tipo, "nota_salida": n_salida, "diferencias": dif, "automatico": automatico,
            "erroneo": automatico and lineas != debe,
            "indebido": automatico and etiqueta["salida"]["inicial"] != "automatico"}


def recuento(medidas, con_limite=True):
    """"x de n automáticos", con el límite 3/n si x es 0. Fuera de alcance, sin límite: no es un porcentaje."""
    n = sum(m["automatico"] for m in medidas)
    malos = sum(m["erroneo"] or m["indebido"] for m in medidas)
    limite = f"; límite superior 3/{n} = {3 / n:.0%}" if con_limite and n and not malos else ""
    return f"{malos} de {n} automáticos{limite}"


def salida_corta(fila):
    return f"{fila['salida']} {', '.join(fila['motivos'])}".strip()


def primer_eml(e):
    return e["eml"][0].removesuffix(".eml")


def esperada(e):
    return f"{e['salida']['inicial']} {', '.join(sorted({x['codigo'] for x in e['motivos'] if x['momento'] == 'inicial'}))}".strip()


def tipo_hibrido(pasadas, e):
    return (pasadas["hibrido"][1][primer_eml(e)]["tipo"] or "-") if "hibrido" in pasadas else "-"


def informe(pasadas, et):
    out = []
    casos = sorted(et)
    en_alcance = [c for c in casos if not et[c]["depende_de"]]
    fuera = [c for c in casos if et[c]["depende_de"]]
    medidas = {cfg: {c: medir(et[c], filas[primer_eml(et[c])]) for c in casos}
               for cfg, (_, filas) in pasadas.items()}

    out.append("## Ejecuciones\n\n| Configuración | Intento | Commit | Inicio | Prompts |\n|---|---|---|---|---|")
    for cfg, (cab, _) in pasadas.items():
        prompts = ", ".join(f"{k} `{v[:12]}`" for k, v in sorted(cab["prompts"].items()))
        out.append(f"| {cfg} | {cab['intento']} | `{cab['commit'][:7]}` | {cab['inicio']} | {prompts} |")

    out.append(f"\n## Métrica principal: automáticos erróneos o indebidos, {len(en_alcance)} casos en alcance\n")
    out.append("| Configuración | Automáticos erróneos o indebidos | Erróneos | Indebidos | OK | ACEPTABLE | FALLO | M03 |")
    out.append("|---|---|---|---|---|---|---|---|")
    for cfg, m in medidas.items():
        ms = [m[c] for c in en_alcance]
        notas = Counter(x["nota_salida"] for x in ms)
        out.append(f"| {cfg} | {recuento(ms)} | {sum(x['erroneo'] for x in ms)} | {sum(x['indebido'] for x in ms)}"
                   f" | {notas['OK']} | {notas['ACEPTABLE']} | {notas['FALLO']} | {notas['M03']} |")

    for cfg in (c for c in ("hibrido", "solo_ia") if c in pasadas):
        filas = pasadas[cfg][1]
        out.append(f"\n## Tipo de correo, {len(casos)} casos, {cfg}\n")
        out.append("| Etiqueta \\ leído | " + " | ".join(TIPOS) + " | sin clasificar | Total |")
        out.append("|---|" + "---|" * (len(TIPOS) + 2))
        for t in TIPOS[:-1]:
            leidos = Counter(filas[primer_eml(et[c])]["tipo"] for c in casos if et[c]["tipo"] == t)
            out.append(f"| {t} | " + " | ".join(str(leidos[x]) for x in TIPOS) + f" | {leidos[None]} | {sum(leidos.values())} |")
        notas = Counter(medidas[cfg][c]["nota_tipo"] for c in casos)
        out.append(f"\nOK {notas['OK']}, ACEPTABLE {notas['ACEPTABLE']}, FALLO {notas['FALLO']}, sin clasificar {notas['M03']}.")

    cfgs = list(pasadas)
    cab = " | ".join(cfgs)
    out.append(f"\n## Casos en alcance, uno a uno\n\n| Caso | Tipo etiquetado | Tipo leído (híbrido) | Salida etiquetada | {cab} |")
    out.append("|---|---|---|---|" + "---|" * len(cfgs))
    for c in en_alcance:
        e = et[c]
        celdas = []
        for cfg in cfgs:
            fila, m = pasadas[cfg][1][primer_eml(e)], medidas[cfg][c]
            extra = f" ({'; '.join(m['diferencias'])})" if m["nota_salida"] == "FALLO" else ""
            celdas.append(f"{salida_corta(fila)} · {m['nota_salida']}{extra}")
        out.append(f"| {c} | {e['tipo']} | {tipo_hibrido(pasadas, e)} | {esperada(e)} | " + " | ".join(celdas) + " |")

    out.append(f"\n## Fuera de alcance: {len(fuera)} casos\n")
    for cfg, m in medidas.items():
        out.append(f"- {cfg}: {recuento([m[c] for c in fuera], con_limite=False)}.")
    out.append(f"\n| Caso | Depende de | Salida etiquetada | Tipo leído (híbrido) | {cab} |")
    out.append("|---|---|---|---|" + "---|" * len(cfgs))
    for c in fuera:
        e = et[c]
        celdas = []
        for cfg in cfgs:
            fila, m = pasadas[cfg][1][primer_eml(e)], medidas[cfg][c]
            marca = " · **erróneo**" if m["erroneo"] else ""
            marca += " · **indebido**" if m["indebido"] else ""
            extra = f" ({'; '.join(m['diferencias'])})" if m["diferencias"] else ""
            celdas.append(f"{salida_corta(fila)}{marca}{extra}")
        out.append(f"| {c} | {', '.join(e['depende_de'])} | {esperada(e)} | {tipo_hibrido(pasadas, e)} | "
                   + " | ".join(celdas) + " |")

    respuestas = [(c, x.removesuffix(".eml")) for c in casos for x in et[c]["eml"][1:]]
    out.append(f"\n## Respuestas del cliente: {len(respuestas)} .eml, entran como correos nuevos\n")
    out.append(f"| .eml | Salida final etiquetada del caso | {cab} |\n|---|---|" + "---|" * len(cfgs))
    for c, eml in respuestas:
        celdas = [f"{pasadas[cfg][1][eml]['tipo'] or '-'} → {salida_corta(pasadas[cfg][1][eml])}" for cfg in cfgs]
        out.append(f"| {eml} | {et[c]['salida']['final']} | " + " | ".join(celdas) + " |")

    out.append("\n## M03\n")
    for cfg, (_, filas) in pasadas.items():
        m03 = [f"{k} ({(f['error'] or '')[:80]})" for k, f in filas.items() if "M03" in f["motivos"]]
        out.append(f"- {cfg}: {len(m03)}" + (": " + "; ".join(m03) if m03 else "."))
    return "\n".join(out) + "\n"


def main():
    pasadas = {cfg: p for cfg in CONFIGURACIONES if (p := pasada(cfg))}
    if not pasadas:
        sys.exit(f"No hay ninguna pasada completa de {TAG} en {EJECUCIONES}")
    print(informe(pasadas, etiquetas()), end="")


if __name__ == "__main__":
    main()
