// Extractor determinista (04, sección 6.3). Sin IA: solo lo que es estructurado.
// - Excel: lectura por nombre de columna, con el mapeo de cabeceras de cabeceras.json.
// - Texto: solo códigos que existen en el catálogo de Orvalle y la cantidad que los acompaña.
// Solo acepta cantidades enteras y limpias: "200 uds" en una celda, "1.000" o "2,5" no son líneas para él
// (quedan para la IA). Las líneas tienen la misma forma que las de la IA, para poder compararlas (R12).

const CABECERAS = require('./cabeceras.json');
const { SEPARADOR } = require('./preprocesado');

const ENTERO = /^\d+$/;
const PRECIO = /^\d+(?:[.,]\d+)?$/;
const UNIDADES = new Set(['ud', 'uds', 'unidad', 'unidades', 'caja', 'cajas', 'caixa', 'caixes', 'cj', 'paquete', 'paquetes']);

function normalizar(texto) {
  return String(texto ?? '')
    .normalize('NFD').replace(/[̀-ͯ]/g, '')
    .toLowerCase().replace(/\s+/g, ' ').trim().replace(/:$/, '');
}

function campoDeCabecera(celda, cabeceras) {
  const n = normalizar(celda);
  return ['referencia', 'cantidad', 'precio', 'unidad'].find((campo) => cabeceras[campo].includes(n)) ?? null;
}

// La fila de cabecera es la primera que tiene a la vez una columna de referencia y una de cantidad.
function columnas(fila, cabeceras) {
  const cols = {};
  fila.forEach((celda, i) => {
    const campo = campoDeCabecera(celda, cabeceras);
    if (campo && cols[campo] === undefined) cols[campo] = i;
  });
  return cols.referencia !== undefined && cols.cantidad !== undefined ? cols : null;
}

function extraerDeExcel(excel, cabeceras = CABECERAS) {
  const { filas } = excel;
  const inicio = filas.findIndex((fila) => columnas(fila, cabeceras));
  if (inicio === -1) return [];
  const cols = columnas(filas[inicio], cabeceras);
  const ignoradas = new Set(cabeceras.filas_ignoradas);
  const lineas = [];
  for (const fila of filas.slice(inicio + 1)) {
    const referencia = (fila[cols.referencia] ?? '').trim();
    const cantidad = (fila[cols.cantidad] ?? '').trim();
    if (!referencia || ignoradas.has(normalizar(referencia)) || !ENTERO.test(cantidad)) continue;
    const precio = cols.precio !== undefined ? (fila[cols.precio] ?? '').trim() : '';
    const unidad = cols.unidad !== undefined ? (fila[cols.unidad] ?? '').trim() : '';
    lineas.push({
      texto: fila.join(SEPARADOR),
      referencia,
      cantidad: Number(cantidad),
      unidad: unidad || null,
      precio: PRECIO.test(precio) ? Number(precio.replace(',', '.')) : null,
    });
  }
  return lineas;
}

// La cantidad va justo después del código ("TOR-M8X30-ZN 500 uds", "TUE-M8-ZN: 1000") o al principio de la
// línea, antes del código ("500 uds de TOR-M8X30-ZN", "- 500 TOR-M8X30-ZN"). Un número suelto antes del código
// no vale: en "Pedido semana 46 TOR-M8X30-ZN", el 46 no es una cantidad. Tiene que ser un entero que no forme
// parte de "1.000" ni de "0,10".
const DESPUES = /^\s*[:\-–x×]?\s*(\d+)(?![\d.,]*\d)(?:\s+([A-Za-zÀ-ÿ.]+))?/;
const ANTES = /^[\s\-–•*]*(\d+)\s*(?:([A-Za-zÀ-ÿ.]+)\s+)?(?:de\s+|x\s+|×\s+)?$/i;
const CANDIDATO = /[A-Za-z0-9][A-Za-z0-9-]*[A-Za-z0-9]/g;

function unidadDe(palabra) {
  const p = normalizar(palabra).replace(/\.$/, '');
  return UNIDADES.has(p) ? palabra.replace(/\.$/, '') : null;
}

function extraerDeTexto(texto, codigos) {
  const catalogo = codigos instanceof Set ? codigos : new Set(codigos);
  const lineas = [];
  for (const bruta of String(texto ?? '').split(/\r?\n/)) {
    const linea = bruta.trim();
    if (!linea || linea.startsWith('>')) continue; // vacía, o citada de un mensaje anterior
    for (const m of linea.matchAll(CANDIDATO)) {
      const codigo = m[0].toUpperCase();
      if (!catalogo.has(codigo)) continue;
      const despues = DESPUES.exec(linea.slice(m.index + m[0].length));
      const antes = despues ? null : ANTES.exec(linea.slice(0, m.index));
      const encontrado = despues ?? antes;
      if (!encontrado) continue;
      lineas.push({
        texto: linea,
        referencia: codigo,
        cantidad: Number(encontrado[1]),
        unidad: encontrado[2] ? unidadDe(encontrado[2]) : null,
        precio: null, // los precios del texto no son estructurados: los lee la IA
      });
    }
  }
  return lineas;
}

// cuerpo: el texto del correo (sin los Excel); excels: los de preprocesarAdjuntos; codigos: los del catálogo.
function extraerDeterminista({ cuerpo, excels, codigos, cabeceras = CABECERAS }) {
  return [
    ...(excels ?? []).flatMap((excel) => extraerDeExcel(excel, cabeceras)),
    ...extraerDeTexto(cuerpo, codigos),
  ];
}

module.exports = { extraerDeterminista, extraerDeExcel, extraerDeTexto, normalizar };
