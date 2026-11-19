// Preprocesado de adjuntos (04, sección 6.2): qué se lee, qué se ignora y qué no está soportado,
// y cómo un Excel pasa a texto. Siempre igual, para que la evaluación reciba la misma entrada que producción.

const readXlsxFile = require('read-excel-file/node');

const TIPO_XLSX = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet';
const SEPARADOR = ' | ';

function extension(nombre) {
  const m = /\.([A-Za-z0-9]+)$/.exec(nombre || '');
  return m ? m[1].toLowerCase() : '';
}

// 'xlsx' se lee; 'ignorar' son imágenes (logos y firmas); el resto no está soportado y va a revisión (M02).
// read-excel-file solo lee .xlsx: un .xls (formato antiguo) tampoco está soportado.
function clasificarAdjunto({ filename, contentType }) {
  const tipo = (contentType || '').toLowerCase();
  if (extension(filename) === 'xlsx' || tipo === TIPO_XLSX) return 'xlsx';
  if (tipo.startsWith('image/')) return 'ignorar';
  return 'no_soportado';
}

function celdaATexto(valor) {
  if (valor === null || valor === undefined) return '';
  if (valor instanceof Date) {
    const iso = valor.toISOString();
    return iso.endsWith('T00:00:00.000Z') ? iso.slice(0, 10) : iso;
  }
  // Un salto de línea dentro de una celda partiría la fila; una barra se confundiría con el separador.
  return String(valor).replace(/\r?\n/g, ' ').replace(/\|/g, '\\|');
}

// Primera hoja, celdas como texto, sin filas vacías ni celdas vacías al final de cada fila.
async function leerXlsx(buffer) {
  const hojas = await readXlsxFile(buffer);
  const { sheet, data } = hojas[0];
  const filas = data
    .map((fila) => {
      const celdas = fila.map(celdaATexto);
      while (celdas.length && celdas[celdas.length - 1] === '') celdas.pop();
      return celdas;
    })
    .filter((celdas) => celdas.length > 0);
  return { hoja: sheet, filas };
}

function filasATexto(nombre, hoja, filas) {
  return [`Adjunto ${nombre} (hoja ${hoja}):`, ...filas.map((celdas) => celdas.join(SEPARADOR))].join('\n');
}

// adjuntos: los de mailparser ({ filename, contentType, content: Buffer }).
async function preprocesarAdjuntos(adjuntos) {
  const excels = [];
  const noSoportados = [];
  let ignorados = 0;
  for (const adjunto of adjuntos || []) {
    const clase = clasificarAdjunto(adjunto);
    if (clase === 'xlsx') {
      const { hoja, filas } = await leerXlsx(adjunto.content);
      excels.push({ nombre: adjunto.filename, hoja, filas });
    } else if (clase === 'ignorar') {
      ignorados += 1;
    } else {
      noSoportados.push({ nombre: adjunto.filename || null, formato: extension(adjunto.filename) || adjunto.contentType || 'desconocido' });
    }
  }
  return {
    excels,
    noSoportados,
    ignorados,
    texto: excels.map((e) => filasATexto(e.nombre, e.hoja, e.filas)).join('\n\n'),
  };
}

module.exports = { clasificarAdjunto, leerXlsx, filasATexto, preprocesarAdjuntos, SEPARADOR };
