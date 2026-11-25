"""Genera el estado correcto de los datos maestros (05; decisión 1B), con semilla fija.

Uso:
    uv run scripts/generar_maestros.py              # escribe supabase/seeds/maestros.sql
    uv run scripts/generar_maestros.py --comprobar  # falla si el fichero no es el que sale ahora

- Produce solo el estado correcto (lo que tendría el ERP tras una migración sin errores): productos, clientes,
  contactos, direcciones, tarifas, equivalencias, conversiones, festivos e histórico. Los ficheros sucios, el
  catálogo de errores y la migración son otro incremento.
- Los 10 productos y los 3 clientes de supabase/seed.sql se conservan tal cual: aquí no se vuelven a escribir.
  Esos 3 clientes no tienen histórico ni tarifas nuevas.
- Entradas: las listas de data/synthetic/listas y las anclas de data/synthetic/listas/anclas.json (lo que
  necesitan los casos de evaluación: clientes bloqueados, direcciones, precios, pedidos citados...).
- `supabase db reset` carga el fichero después de seed.sql (supabase/config.toml).
"""

import argparse
import csv
import json
import random
import re
import sys
import unicodedata
from datetime import date, datetime, time, timedelta
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
LISTAS = RAIZ / "data" / "synthetic" / "listas"
DESTINO = RAIZ / "supabase" / "seeds" / "maestros.sql"
SEED = RAIZ / "supabase" / "seed.sql"

SEMILLA = 20261030
INICIO = date(2026, 5, 1)
MIGRACION = date(2026, 10, 30)          # T: parámetro fijo del escenario, nunca la fecha de ejecución
SIN_VIGENCIA = MIGRACION + timedelta(days=90)
PRIMER_PEDIDO = 12001                   # numeración del ERP antes de la automatización
DOMINIO_PUBLICO = "correopublico.example"   # ficticio: ninguna dirección puede ser de una persona real

FESTIVOS = [
    ("2026-05-01", "Fiesta del Trabajo"), ("2026-06-24", "Sant Joan"), ("2026-08-15", "Asunción"),
    ("2026-09-11", "Diada"), ("2026-10-12", "Fiesta Nacional"), ("2026-11-01", "Todos los Santos"),
    ("2026-12-06", "Constitución"), ("2026-12-08", "Inmaculada"), ("2026-12-25", "Navidad"),
    ("2026-12-26", "Sant Esteve"), ("2027-01-01", "Año Nuevo"), ("2027-01-06", "Reyes"),
    ("2027-03-26", "Viernes Santo"), ("2027-03-29", "Lunes de Pascua"),
]
COMERCIALES = [   # COM-1 y COM-2 ya están en seed.sql
    ("COM-3", "Raquel Navarro", "raquel.navarro@orvalle.example"),
    ("COM-4", "Albert Casals", "albert.casals@orvalle.example"),
    ("COM-5", "Óscar Delgado", "oscar.delgado@orvalle.example"),
]
DESCATALOGADOS = {   # código: sustituto aprobado, o None
    "BRO-HSS-1-5": "BRO-HSS-2", "DIS-LAM-60": "DIS-LAM-80", "GAF-PROT-AMA": "GAF-PROT-INC",
    "GUA-COR-7": "GUA-COR-8", "ORE-SNR27": "ORE-SNR31", "LLC-9": "LLC-10", "TIR-6X40-ZN": "TIR-6X60-ZN",
    "MAR-300": None, "TAC-NY-5": None, "ABR-8-12": None, "PUN-SDS-400": None, "LAL-2": None,
}


def sin_acentos(texto):
    texto = texto.replace("l·l", "ll").replace("·", "")
    return unicodedata.normalize("NFD", texto).encode("ascii", "ignore").decode()


def dominio(razon_social):
    nombre = re.sub(r",?\s+S\.(L|A|C\.P|L\.U)\.$", "", razon_social)
    return re.sub(r"[^a-z0-9]", "", sin_acentos(nombre).lower()) + ".example"


def redondear(precio):
    paso = Decimal("0.01") if precio >= 1 else Decimal("0.0001")
    return Decimal(str(precio)).quantize(paso, ROUND_HALF_UP)


def leer_lista(nombre):
    with open(LISTAS / nombre, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f, delimiter=";"))


def del_seed(tabla):
    """Primera columna de los insert de seed.sql: los códigos que ya existen."""
    bloque = re.search(rf"insert into erp\.{tabla} .*?;", SEED.read_text(), re.S).group(0)
    return re.findall(r"^\s*\('([^']+)'", bloque, re.M)


def precios_del_seed():
    """Los 10 productos de la v1 conservan su precio: no sale de la lista."""
    bloque = re.search(r"insert into erp\.productos .*?;", SEED.read_text(), re.S).group(0)
    return {c: Decimal(p) for c, p in re.findall(r"^\s*\('([^']+)'.*?([\d.]+)\)[,;]$", bloque, re.M)}


def generar_productos():
    productos, conversiones, conservados = [], [], precios_del_seed()
    for fam in leer_lista("familias.csv"):
        if "=" in fam["medidas"]:
            medidas = re.findall(r"(\S+)=(.*?)(?=\s+\S+=|$)", fam["medidas"])
        else:
            medidas = [(m, m) for m in fam["medidas"].split()]
        minimo, maximo = float(fam["precio_min"]), float(fam["precio_max"])
        for i, (clave, texto) in enumerate(medidas):
            codigo = fam["codigo"].replace("{m}", clave.replace(".", "-").upper())
            if texto == clave:
                texto = clave.replace(".", ",")
                if re.search(r"\dX\d", texto):
                    texto = texto.replace("X", "x")
            fraccion = i / (len(medidas) - 1) if len(medidas) > 1 else 0
            productos.append({
                "codigo": codigo, "descripcion": fam["descripcion"].replace("{m}", texto),
                "unidad": fam["unidad"], "embalaje": int(fam["embalaje"]), "minimo": int(fam["minimo"]),
                "activo": codigo not in DESCATALOGADOS, "sustituto": DESCATALOGADOS.get(codigo),
                "precio": conservados.get(codigo) or redondear(minimo + (maximo - minimo) * fraccion),
            })
            # Tornillería y arandelas en cajas de 100; tuercas también. Guantes por pares en cajas de su embalaje.
            if re.match(r"(TOR|ALL|AVE|TUE|TUA|ARA|ARG|ARL|PRI)-", codigo) and fam["embalaje"] == "100":
                conversiones.append((codigo, "caja", 100))
            elif codigo.startswith(("GUA-PU", "GUA-CUE")):
                conversiones.append((codigo, "caja", 12))
            elif codigo.startswith("VAR-"):
                conversiones.append((codigo, "paquete", 10))
    return productos, conversiones


def generar_clientes(rng):
    personas = leer_lista("personas.csv")
    nombres = [p["valor"] for p in personas if p["tipo"] == "nombre"]
    apellidos = [p["valor"] for p in personas if p["tipo"] == "apellido"]
    poblaciones, calles = leer_lista("poblaciones.csv"), leer_lista("calles.csv")
    poligono = [c["calle"] for c in calles if c["poligono"] == "si"]
    casco = [c["calle"] for c in calles if c["poligono"] == "no"]
    comerciales = ["COM-1", "COM-2", "COM-3", "COM-4", "COM-5"]
    clientes, direcciones, contactos = [], [], []

    for i, e in enumerate(leer_lista("empresas.csv"), start=1):
        codigo = f"C{i:04d}"
        letra = {"S.A.": "A", "S.C.P.": "J"}.get(e["razon_social"].split(", ")[-1], "B")
        clientes.append({
            "codigo": codigo, "cif": f"{letra}{60000000 + i * 11}", "razon_social": e["razon_social"],
            "telefono": f"+34 930 000 {i:03d}", "bloqueado": False,
            "comercial": {1: "COM-1", 2: "COM-1", 3: "COM-2"}.get(i, comerciales[(i - 1) % 5]), "idioma": e["idioma"], "actividad": e["actividad"],
        })
        if i <= 3:
            continue
        n_direcciones = 1 if rng.random() < 0.78 else rng.choice([2, 2, 3])
        usadas = set()
        while len(usadas) < n_direcciones:
            industrial = e["actividad"] != "instalador" or rng.random() < 0.4
            calle = rng.choice(poligono if industrial else casco)
            pob = rng.choice(poblaciones)
            numero = str(rng.randint(1, 120))
            if (calle, numero) in usadas:
                continue
            usadas.add((calle, numero))
            nave = f"Nave {rng.randint(1, 14)}" if industrial and rng.random() < 0.4 else None
            direcciones.append({"cliente": codigo, "calle": calle, "numero": numero, "nave": nave,
                                "cp": pob["cp"], "poblacion": pob["poblacion"]})
        dom = dominio(e["razon_social"])
        for buzon in rng.sample(["compras", "pedidos", "oficina", "taller", "administracion", "almacen"],
                                rng.choice([1, 1, 2, 2, 3])):
            nombre = f"{rng.choice(nombres)} {rng.choice(apellidos)}"
            contactos.append({"cliente": codigo, "email": f"{buzon}@{dom}", "nombre": nombre})
    return clientes, direcciones, contactos


def dia_habil(d, festivos):
    return d.weekday() < 5 and d not in festivos


def generar_historico(rng, clientes, productos, direcciones, precio_real, festivos, excluidos):
    """Pedidos del 01-05 al 30-10: segmentos de frecuencia, cesta habitual, calendario y ~3 % de ruido."""
    dias, pesos = [], []
    d = INICIO
    while d <= MIGRACION:
        if dia_habil(d, festivos):
            previo = d - timedelta(days=1)
            peso = 1.0
            if d.weekday() == 0 or previo in festivos:
                peso = 2.0          # lunes y días después de un festivo, el doble
            if d.month == 8:
                peso *= 0.3
            dias.append(d)
            pesos.append(peso)
        d += timedelta(days=1)

    activos = [p for p in productos if p["activo"]]
    por_embalaje = {p["codigo"]: p["embalaje"] for p in productos}
    dir_de = {}
    for x in direcciones:
        dir_de.setdefault(x["cliente"], []).append(x)
    pedidos, cestas = [], {}
    clientes = [c for c in clientes if int(c["codigo"][1:]) > 3]
    segmentos = ["semanal"] * 23 + ["mensual"] * 58 + ["ocasional"] * (len(clientes) - 81)
    rng.shuffle(segmentos)
    for c, segmento in zip(clientes, segmentos):
        cod = c["codigo"]
        prohibidos = {p for cl, p in excluidos if cl == cod}
        candidatos = [p["codigo"] for p in activos if p["codigo"] not in prohibidos]
        cesta = rng.sample(candidatos, rng.randint(5, 15))
        habitual = {p: por_embalaje[p] * rng.choice([1, 1, 2, 3, 5, 10] if por_embalaje[p] >= 50 else [1, 2, 4, 6, 10])
                    for p in cesta}
        cestas[cod] = cesta
        n = {"semanal": rng.randint(27, 36), "mensual": rng.randint(6, 14), "ocasional": rng.randint(1, 3)}[segmento]
        for dia in sorted(rng.choices(dias, pesos, k=n)):
            k = min(len(cesta), max(1, min(25, round(rng.lognormvariate(1.28, 0.65)))))
            lineas = []
            for p in rng.sample(cesta, k):
                cantidad = habitual[p]
                if rng.random() < 0.35:
                    cantidad = max(por_embalaje[p], cantidad + por_embalaje[p] * rng.choice([-1, 1]))
                if rng.random() < 0.03:
                    cantidad *= rng.randint(3, 8)
                lineas.append((p, cantidad, precio_real(cod, p)))
            hora = time(rng.randint(8, 17), rng.randint(0, 59))
            pedidos.append({"cliente": cod, "fecha": datetime.combine(dia, hora), "num": None,
                            "direccion": rng.choice(dir_de[cod]), "lineas": lineas})
    return pedidos, cestas


def generar():
    rng = random.Random(SEMILLA)
    anclas = json.loads((LISTAS / "anclas.json").read_text())
    festivos = {date.fromisoformat(f) for f, _ in FESTIVOS}

    productos, conversiones = generar_productos()
    precio_general = {p["codigo"]: p["precio"] for p in productos}
    clientes, direcciones, contactos = generar_clientes(rng)
    cliente = {c["codigo"]: c for c in clientes}

    # ---- anclas de clientes, contactos y direcciones
    for cod in anclas["bloqueados"]:
        cliente[cod]["bloqueado"] = True
    for cod, lista in anclas["direcciones"].items():
        direcciones = [d for d in direcciones if d["cliente"] != cod]
        direcciones += [{"cliente": cod, **d} for d in lista]
    for cod, lista in anclas["contactos"].items():
        contactos = [c for c in contactos if c["cliente"] != cod]
        contactos += [{"cliente": cod, **c} for c in lista]
    direcciones.sort(key=lambda d: d["cliente"])
    contactos.sort(key=lambda c: c["cliente"])

    # ---- tarifas: anclas, y el resto según la cesta de cada cliente (más abajo)
    tarifas = [{"cliente": t["cliente"], "producto": t["producto"], "precio": Decimal(t["precio"]),
                "desde": t.get("desde", "2026-01-01"), "hasta": t.get("hasta", "2026-12-31"),
                "estado": t.get("estado", "activa")} for t in anclas["tarifas"]]
    pactado = {(t["cliente"], t["producto"]): t["precio"] for t in tarifas if t["estado"] == "activa"}
    telefono = {(t["cliente"], t["producto"]): Decimal(t["precio"]) for t in anclas["precios_por_telefono"]}

    def precio_real(cod, prod):
        return telefono.get((cod, prod)) or pactado.get((cod, prod)) or precio_general[prod]

    # Los productos de las anclas no entran en la cesta aleatoria de su cliente: las medianas y los
    # conteos que prueban R14 y R07 son exactamente los del plan.
    excluidos = {(t["cliente"], t["producto"]) for t in anclas["tarifas"] + anclas["precios_por_telefono"]}
    excluidos |= {(p["cliente"], l[0]) for p in anclas["pedidos"] for l in p["lineas"]}
    excluidos |= {(c, p) for c, p in anclas["reservados"]}

    # Primera pasada: cestas. Las tarifas pactadas salen de ellas y fijan el precio real del histórico.
    estado_rng = rng.getstate()
    _, cestas = generar_historico(rng, clientes, productos, direcciones, precio_real, festivos, excluidos)
    rng_tarifas = random.Random(SEMILLA + 1)
    for cod, cesta in sorted(cestas.items()):
        hasta = SIN_VIGENCIA.isoformat() if rng_tarifas.random() < 0.15 else "2026-12-31"
        for prod in sorted(rng_tarifas.sample(cesta, rng_tarifas.randint(0, min(8, len(cesta))))):
            if rng_tarifas.random() < 0.02:     # pactado por teléfono: facturado, pero en ninguna tarifa
                telefono[(cod, prod)] = redondear(precio_general[prod] * Decimal("0.88"))
                continue
            precio = redondear(precio_general[prod] * (1 - Decimal(rng_tarifas.randint(5, 20)) / 100))
            tarifas.append({"cliente": cod, "producto": prod, "precio": precio, "desde": "2026-01-01",
                            "hasta": hasta, "estado": "activa"})
            pactado[(cod, prod)] = precio

    # ---- equivalencias: anclas y las de los clientes que usan sus propias referencias
    equivalencias = [(e["cliente"], e["referencia"], e["producto"]) for e in anclas["equivalencias"]]
    rng_eq = random.Random(SEMILLA + 2)
    con_ancla = {e[0] for e in equivalencias}
    for cod, cesta in sorted(cestas.items()):
        if cod in con_ancla or rng_eq.random() > 0.4:
            continue
        prefijo = cliente[cod]["razon_social"].split()[-2].rstrip(",")[:3]
        prefijo = re.sub(r"[^A-Z]", "", sin_acentos(prefijo).upper()) or "REF"
        for n, prod in enumerate(sorted(rng_eq.sample(cesta, rng_eq.randint(2, min(6, len(cesta)))))):
            equivalencias.append((cod, f"{prefijo}-{rng_eq.randint(100, 999)}{n}", prod))

    # ---- histórico
    rng.setstate(estado_rng)
    pedidos, _ = generar_historico(rng, clientes, productos, direcciones, precio_real, festivos, excluidos)
    dir_de = {}
    for d in direcciones:
        dir_de.setdefault(d["cliente"], []).append(d)
    for p in anclas["pedidos"]:
        pedidos.append({"cliente": p["cliente"], "fecha": datetime.fromisoformat(p["fecha"]), "num": p.get("num"),
                        "direccion": dir_de[p["cliente"]][p.get("direccion", 1) - 1],
                        "lineas": [(prod, cant, precio_real(p["cliente"], prod)) for prod, cant in p["lineas"]]})
    pedidos.sort(key=lambda p: (p["fecha"], p["cliente"], p["lineas"][0][0]))
    for i, p in enumerate(pedidos):
        p["numero"] = f"PV{PRIMER_PEDIDO + i:06d}"
        p["entrega"] = p["fecha"].date() + timedelta(days=1)
        while not dia_habil(p["entrega"], festivos):
            p["entrega"] += timedelta(days=1)

    return {"productos": productos, "conversiones": conversiones, "clientes": clientes, "direcciones": direcciones,
            "contactos": contactos, "tarifas": tarifas, "equivalencias": equivalencias, "pedidos": pedidos,
            "festivos": FESTIVOS, "comerciales": COMERCIALES, "telefono": telefono}


# ---------------------------------------------------------------- SQL

def lit(v):
    if v is None:
        return "null"
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, Decimal)):
        return str(v)
    return "'" + str(v).replace("'", "''") + "'"


def insertar(tabla, columnas, filas, por_bloque=400):
    trozos = []
    for i in range(0, len(filas), por_bloque):
        valores = ",\n".join("  (" + ", ".join(lit(v) for v in f) + ")" for f in filas[i:i + por_bloque])
        trozos.append(f"insert into {tabla} ({columnas}) values\n{valores};\n")
    return "\n".join(trozos)


def insertar_desde(tabla, columnas, seleccion, alias, union, filas, por_bloque=400):
    """Como insertar, pero buscando la clave de otra tabla. Todas las columnas que pueden faltar son texto."""
    trozos = []
    for i in range(0, len(filas), por_bloque):
        valores = ",\n".join("  (" + ", ".join("null::text" if v is None else lit(v) for v in f) + ")"
                             for f in filas[i:i + por_bloque])
        trozos.append(f"insert into {tabla} ({columnas})\n{seleccion}\nfrom (values\n{valores}\n) as h ({alias})\n{union};\n")
    return "\n".join(trozos)


def a_sql(m):
    ya_productos, ya_clientes = set(del_seed("productos")), set(del_seed("clientes"))
    nuevos = [p for p in m["productos"] if p["codigo"] not in ya_productos]
    # Sustitutos después: la clave ajena exige que el sustituto exista.
    sql = ["-- GENERADO por scripts/generar_maestros.py: no editar a mano.",
           f"-- Semilla {SEMILLA}. Estado correcto de los datos maestros (docs/05). Todo es sintético.",
           "-- Se carga después de seed.sql, que conserva los 10 productos y 3 clientes de la v1.", ""]
    sql.append(insertar("intake.dominios_publicos", "dominio", [(DOMINIO_PUBLICO,)]))
    sql.append(insertar("erp.festivos", "fecha, nombre", m["festivos"]))
    sql.append(insertar("erp.comerciales", "id, nombre, email", m["comerciales"]))
    sql.append(insertar("erp.productos", "codigo, descripcion, unidad_venta, embalaje, minimo, activo, precio_general",
                        [(p["codigo"], p["descripcion"], p["unidad"], p["embalaje"], p["minimo"], p["activo"],
                          p["precio"]) for p in nuevos]))
    sql.append("".join(f"update erp.productos set sustituto = {lit(p['sustituto'])} where codigo = {lit(p['codigo'])};\n"
                       for p in nuevos if p["sustituto"]))
    sql.append(insertar("erp.conversiones_unidad", "producto, unidad, factor", m["conversiones"]))
    sql.append(insertar("erp.clientes", "codigo, cif, razon_social, telefono, bloqueado, comercial_id",
                        [(c["codigo"], c["cif"], c["razon_social"], c["telefono"], c["bloqueado"], c["comercial"])
                         for c in m["clientes"] if c["codigo"] not in ya_clientes]))
    sql.append(insertar("erp.direcciones", "cliente, calle, numero, nave, cp, poblacion",
                        [(d["cliente"], d["calle"], d["numero"], d["nave"], d["cp"], d["poblacion"])
                         for d in m["direcciones"]]))
    sql.append(insertar("erp.contactos", "cliente, email, nombre",
                        [(c["cliente"], c["email"], c["nombre"]) for c in m["contactos"]]))
    sql.append(insertar("erp.tarifas", "cliente, producto, precio_neto, desde, hasta, estado, origen",
                        [(t["cliente"], t["producto"], t["precio"], t["desde"], t["hasta"], t["estado"], "migracion")
                         for t in m["tarifas"]]))
    sql.append(insertar("erp.equivalencias", "cliente, referencia_cliente, producto, origen, creada_por",
                        [(c, r, p, "migracion", "generador") for c, r, p in m["equivalencias"]]))
    # Las filas llevan el número de pedido y la clave natural de la dirección: los ids los pone la base.
    sql.append(insertar_desde(
        "erp.pedidos", "numero, cliente, num_pedido_cliente, direccion, fecha_prevista, origen, creado_en",
        "select h.numero, h.cliente, h.num, d.id, h.entrega::date, 'historico',"
        " h.creado::timestamp at time zone 'Europe/Madrid'",
        "numero, cliente, num, calle, via, nave, cp, entrega, creado",
        "join erp.direcciones d on d.cliente = h.cliente and d.calle = h.calle and d.numero = h.via"
        " and d.cp = h.cp and d.nave is not distinct from h.nave\norder by h.numero",
        [(p["numero"], p["cliente"], p["num"], p["direccion"]["calle"], p["direccion"]["numero"],
          p["direccion"]["nave"], p["direccion"]["cp"], p["entrega"].isoformat(), p["fecha"].isoformat(sep=" "))
         for p in m["pedidos"]]))
    sql.append(insertar_desde(
        "erp.lineas_pedido", "pedido, linea, producto, cantidad, precio_unitario",
        "select p.id, h.linea, h.producto, h.cantidad, h.precio", "numero, linea, producto, cantidad, precio",
        "join erp.pedidos p on p.numero = h.numero",
        [(p["numero"], i, prod, cant, precio) for p in m["pedidos"]
         for i, (prod, cant, precio) in enumerate(p["lineas"], start=1)]))
    ultimo = PRIMER_PEDIDO + len(m["pedidos"]) - 1
    sql.append(f"select setval('erp.numero_pedido', {ultimo});\n")
    return "\n".join(s for s in sql if s is not None)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--comprobar", action="store_true")
    args = parser.parse_args()
    maestros = generar()
    sql = a_sql(maestros)
    if args.comprobar:
        if not DESTINO.exists() or DESTINO.read_text() != sql:
            sys.exit(f"{DESTINO.relative_to(RAIZ)} no es el que produce el generador")
        print("Igual que el generador")
        return
    DESTINO.parent.mkdir(exist_ok=True)
    DESTINO.write_text(sql)
    print({k: len(v) for k, v in maestros.items()}, "líneas del histórico:",
          sum(len(p["lineas"]) for p in maestros["pedidos"]))


if __name__ == "__main__":
    main()
