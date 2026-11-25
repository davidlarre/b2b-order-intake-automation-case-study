"""Monta los .eml de evaluacion-v2 a partir de sus fichas, y calcula las marcas (dónde se desvía cada correo de su ficha).

Uso:
    uv run scripts/generar_correos.py              # escribe correos/ de los dos conjuntos
    uv run scripts/generar_correos.py --comprobar  # falla si algún .eml no es el que sale de su ficha

- La ficha lleva lo que escribiría una persona (cuerpo, firma y celdas, escritos por Claude). Este script monta lo
  demás: cabeceras, MIME, adjuntos, hilos, reenvíos y fechas. La salida es determinista, byte a byte.
- Las marcas comparan el .eml ya montado con lo que pretendía la ficha: códigos, cantidades, precios, fechas,
  textos obligatorios o prohibidos y catalán. No dicen que el correo esté mal: dicen dónde mirar con atención al
  etiquetar. Se etiqueta lo que dice el correo, no la ficha (guia-etiquetado.md).
"""

import argparse
import email
import email.policy
import email.utils
import html
import io
import re
import sys
import zipfile
from datetime import datetime
from email.message import EmailMessage
from pathlib import Path

import yaml

RAIZ = Path(__file__).resolve().parent.parent
EVALUACION = RAIZ / "data" / "synthetic" / "evaluacion-v2"
CONJUNTOS = ("desarrollo", "prueba")
PARA = "pedidos@orvalle.example"
XLSX = ("application", "vnd.openxmlformats-officedocument.spreadsheetml.sheet")

DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre",
         "noviembre", "diciembre"]


# ---------------------------------------------------------------- lectura de fichas

def leer_fichas(conjunto):
    carpeta = EVALUACION / conjunto / "fichas"
    return {p.stem: yaml.safe_load(p.read_text()) for p in sorted(carpeta.glob("*.yaml"))}


# ---------------------------------------------------------------- adjuntos deterministas

def xlsx(hoja, filas):
    """Un .xlsx con los mismos bytes en cualquier máquina: sin fechas de creación y sin compresión."""
    from openpyxl import Workbook

    libro = Workbook()
    h = libro.active
    h.title = hoja
    for fila in filas:
        h.append(fila or [None])
    bruto = io.BytesIO()
    libro.save(bruto)
    salida = io.BytesIO()
    with zipfile.ZipFile(bruto) as origen, zipfile.ZipFile(salida, "w", zipfile.ZIP_STORED) as destino:
        for nombre in sorted(origen.namelist()):
            datos = origen.read(nombre)
            if nombre == "docProps/core.xml":
                datos = re.sub(rb"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ", b"2026-11-01T00:00:00Z", datos)
            destino.writestr(zipfile.ZipInfo(nombre, (2026, 11, 1, 0, 0, 0)), datos)
    return salida.getvalue()


def pdf(lineas):
    """Un PDF de una página con texto. Nadie lo lee: es un formato no soportado (M02)."""
    escapar = lambda t: t.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    texto = "BT /F1 11 Tf 60 780 Td 15 TL " + " ".join(f"({escapar(l)}) Tj T*" for l in lineas) + " ET"
    flujo = texto.encode("latin-1", "replace")
    objetos = [b"<</Type/Catalog/Pages 2 0 R>>", b"<</Type/Pages/Kids[3 0 R]/Count 1>>",
               b"<</Type/Page/Parent 2 0 R/MediaBox[0 0 595 842]/Contents 4 0 R/Resources<</Font<</F1 5 0 R>>>>>>",
               b"<</Length %d>>\nstream\n%s\nendstream" % (len(flujo), flujo),
               b"<</Type/Font/Subtype/Type1/BaseFont/Helvetica/Encoding/WinAnsiEncoding>>"]
    salida, posiciones = b"%PDF-1.4\n", []
    for i, o in enumerate(objetos, start=1):
        posiciones.append(len(salida))
        salida += b"%d 0 obj\n%s\nendobj\n" % (i, o)
    xref = len(salida)
    salida += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objetos) + 1)
    salida += b"".join(b"%010d 00000 n \n" % p for p in posiciones)
    return salida + b"trailer\n<</Size %d/Root 1 0 R>>\nstartxref\n%d\n%%%%EOF\n" % (len(objetos) + 1, xref)


# ---------------------------------------------------------------- montaje

def message_id(correo):
    nombre = Path(correo["eml"]).stem.lower()
    return f"<v2-{nombre}@{correo['de'][1].split('@')[1]}>"


def autenticacion(correo):
    dominio = correo["de"][1].split("@")[1]
    dmarc = correo.get("dmarc", "pass")
    if dmarc == "pass":
        return (f"mx.orvalle.example; spf=pass smtp.mailfrom={dominio}; dkim=pass header.d={dominio};"
                f" dmarc=pass header.from={dominio}")
    if dmarc == "none":
        return f"mx.orvalle.example; spf=pass smtp.mailfrom={dominio}; dmarc=none header.from={dominio}"
    return f"mx.orvalle.example; spf=fail smtp.mailfrom={dominio}; dkim=none; dmarc=fail header.from={dominio}"


def cuerpo_de(correo):
    texto = correo["cuerpo"].rstrip("\n") + "\n"
    r = correo.get("reenvio")
    if not r or r["estilo"] == "eml":
        return texto
    f = datetime.fromisoformat(str(r["fecha"]))
    nombre, direccion = r["de"]
    para = correo["de"][1]
    if r["estilo"] == "gmail":
        cabecera = (f"---------- Forwarded message ---------\nDe: {nombre} <{direccion}>\n"
                    f"Date: {DIAS[f.weekday()][:3]}, {f.day} {MESES[f.month - 1][:3]} {f.year} a las {f.hour}:{f.minute:02d}\n"
                    f"Subject: {r['asunto']}\nTo: <{para}>\n")
    else:
        cabecera = (f"________________________________\nDe: {nombre} <{direccion}>\n"
                    f"Enviado: {DIAS[f.weekday()]}, {f.day} de {MESES[f.month - 1]} de {f.year} {f.hour}:{f.minute:02d}\n"
                    f"Para: {correo['de'][0]} <{para}>\nAsunto: {r['asunto']}\n")
    return f"{texto}\n{cabecera}\n{r['cuerpo'].rstrip()}\n"


def a_html(texto):
    parrafos = "".join(f"<p>{html.escape(p).replace(chr(10), '<br>')}</p>\n" for p in texto.strip().split("\n\n"))
    return f"<html><body style=\"font-family:Calibri\">\n{parrafos}</body></html>\n"


def montar(correo, hilo):
    """hilo: los Message-ID de los .eml anteriores del caso a los que responde."""
    m = EmailMessage(policy=email.policy.SMTP.clone(max_line_length=200, cte_type="8bit"))
    nombre, direccion = correo["de"]
    m["From"] = email.utils.formataddr((nombre, direccion), charset="utf-8") if nombre else direccion
    m["To"] = PARA
    m["Subject"] = correo["asunto"]
    m["Date"] = email.utils.format_datetime(datetime.fromisoformat(str(correo["fecha"])))
    m["Message-ID"] = message_id(correo)
    if hilo:
        m["In-Reply-To"] = hilo[-1]
        m["References"] = " ".join(hilo)
    if correo.get("automatico"):
        m["Auto-Submitted"] = "auto-replied"
        m["X-Autoreply"] = "yes"
    m["Authentication-Results"] = autenticacion(correo)
    texto = cuerpo_de(correo)
    if correo.get("html"):
        m.set_content(a_html(texto), subtype="html", charset="utf-8", cte="8bit")
    else:
        m.set_content(texto, charset="utf-8", cte="8bit")
    if x := correo.get("excel"):
        m.add_attachment(xlsx(x.get("hoja", "Hoja1"), x["filas"]), maintype=XLSX[0], subtype=XLSX[1], filename=x["nombre"])
    if p := correo.get("pdf"):
        m.add_attachment(pdf(p["lineas"]), maintype="application", subtype="pdf", filename=p["nombre"])
    r = correo.get("reenvio")
    if r and r["estilo"] == "eml":
        original = EmailMessage(policy=m.policy)
        original["From"] = email.utils.formataddr(tuple(r["de"]), charset="utf-8")
        original["To"] = direccion
        original["Subject"] = r["asunto"]
        original["Date"] = email.utils.format_datetime(datetime.fromisoformat(str(r["fecha"])))
        original["Message-ID"] = f"<orig-{Path(correo['eml']).stem.lower()}@{r['de'][1].split('@')[1]}>"
        original.set_content(r["cuerpo"], charset="utf-8", cte="8bit")
        m.add_attachment(original, filename="original.eml")
    if m.is_multipart():
        m.set_boundary(f"=_{Path(correo['eml']).stem.lower()}_orvalle_v2")
    return m.as_bytes()


def generar(conjunto):
    """{nombre del .eml: bytes} de un conjunto."""
    salida = {}
    for ficha in leer_fichas(conjunto).values():
        por_nombre = {c["eml"]: c for c in ficha["correos"]}
        for correo in ficha["correos"]:
            hilo = [r if r.startswith("<") else message_id(por_nombre[r]) for r in correo.get("responde_a", [])]
            salida[correo["eml"]] = montar(correo, hilo)
    return salida


# ---------------------------------------------------------------- lo que dice un .eml

def filas_xlsx(datos):
    from openpyxl import load_workbook

    hoja = load_workbook(io.BytesIO(datos), read_only=True).worksheets[0]
    for fila in hoja.iter_rows(values_only=True):
        celdas = ["" if c is None else str(c) for c in fila]
        if any(celdas):
            yield " | ".join(celdas)


def texto_de(eml: bytes):
    """Líneas legibles del correo: cuerpo (sin etiquetas), mensaje adjunto y primera hoja del Excel. Sin el PDF."""
    m = email.message_from_bytes(eml, policy=email.policy.default)
    lineas = []
    for parte in m.walk():
        tipo = parte.get_content_type()
        if tipo == "text/plain":
            lineas += parte.get_content().splitlines()
        elif tipo == "text/html":
            limpio = re.sub(r"<(br|/p|/tr|/td)[^>]*>", "\n", parte.get_content())
            lineas += html.unescape(re.sub(r"<[^>]+>", "", limpio)).splitlines()
        elif parte.get_filename() and parte.get_filename().endswith(".xlsx"):
            lineas += list(filas_xlsx(parte.get_payload(decode=True)))
    return lineas


# ---------------------------------------------------------------- marcas

CATALAN = set("""us amb comanda gràcies necessitem necessito caixes unitats però setmana aquest aquesta salutacions bon
 són heu podeu volem també adjunt parells rotlles demà dilluns dimarts dimecres dijous divendres ens gairebé
 teniu hauria fer enviar avui mateix som només sisplau magatzem mati matí vam""".split())
CASTELLANO = set("""buenos buenas días tardes gracias pedido necesitamos necesito unidades pero semana esta este saludos
 hola son podéis queremos también cajas pares mañana lunes martes miércoles jueves viernes nos tenéis enviar hoy
 por favor almacén los las con""".split())


def idioma(texto):
    palabras = re.findall(r"[a-zà-ÿ·]+", texto.lower())
    ca = sum(p in CATALAN for p in palabras)
    es = sum(p in CASTELLANO for p in palabras)
    if ca and ca >= 2 * es:
        return "entero"
    return "frases" if ca >= 2 else "no"


def plano(t):
    return re.sub(r"\s+", " ", str(t)).strip().lower()


def marcas(ficha, emls, catalogo):
    """Diferencias entre lo que pretendía la ficha y lo que dicen los .eml del caso."""
    lineas = [l for c in ficha["correos"] for l in texto_de(emls[c["eml"]])]
    # Lo que se responde o se cita no se vuelve a pedir: no cuenta para las líneas.
    propias = [plano(l) for l in lineas if not l.lstrip().startswith(">")]
    todo = "\n".join(propias)
    salida = []
    esperados = set()
    for n, l in enumerate(ficha.get("lineas") or [], start=1):
        ref = l.get("ref", l.get("producto"))
        esperados.add(l.get("producto"))
        con_ref = [t for t in propias if plano(ref) in t]
        if not con_ref:
            salida.append(f"codigo: la línea {n} ({ref}) no aparece en el correo")
            continue
        numero = re.compile(rf"(?<![\d.,])0*{l['cantidad']}(?![\d]|[.,]\d)")
        sin_ref = [t.replace(plano(ref), " ") for t in con_ref]
        if not any(numero.search(t) for t in sin_ref):
            salida.append(f"cantidad: {l['cantidad']} no aparece como número junto a {ref}")
        if l.get("precio") is not None:
            p = str(l["precio"])
            if not any(p.replace(".", ",") in t or p in t for t in con_ref):
                salida.append(f"precio: {p} no aparece junto a {ref}")
    for codigo in sorted(set(re.findall(r"[a-z0-9]+(?:-[a-z0-9]+)+", todo)) & {c.lower() for c in catalogo}):
        if codigo.upper() not in esperados and codigo.upper() not in (ficha.get("otros_codigos") or []):
            salida.append(f"codigo: {codigo.upper()} aparece y no está en la ficha")
    for t in ficha.get("debe_incluir") or []:
        if plano(t) not in plano(" ".join(propias)):
            salida.append(f"texto: falta «{t}»")
    for t in ficha.get("no_debe_incluir") or []:
        if plano(t) in plano(" ".join(propias)):
            salida.append(f"texto: aparece «{t}» y no debía")
    leido = idioma("\n".join(c["cuerpo"] + "\n" + (c.get("reenvio") or {}).get("cuerpo", "") for c in ficha["correos"]))
    if leido != ficha.get("catalan", "no"):
        salida.append(f"catalan: la ficha dice «{ficha.get('catalan', 'no')}» y el correo parece «{leido}»")
    return salida


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--comprobar", action="store_true")
    args = parser.parse_args()
    distintos = []
    for conjunto in CONJUNTOS:
        carpeta = EVALUACION / conjunto / "correos"
        emls = generar(conjunto)
        for nombre, datos in emls.items():
            ruta = carpeta / nombre
            if args.comprobar:
                if not ruta.exists() or ruta.read_bytes() != datos:
                    distintos.append(f"{conjunto}/{nombre}")
            else:
                carpeta.mkdir(parents=True, exist_ok=True)
                ruta.write_bytes(datos)
        sobran = {p.name for p in carpeta.glob("*.eml")} - set(emls)
        distintos += [f"{conjunto}/{s} (sin ficha)" for s in sorted(sobran)]
        print(f"{conjunto}: {len(leer_fichas(conjunto))} fichas, {len(emls)} .eml")
    if distintos:
        sys.exit("No coinciden con su ficha: " + ", ".join(distintos))


if __name__ == "__main__":
    main()
