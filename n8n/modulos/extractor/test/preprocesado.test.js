const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const { clasificarAdjunto, leerXlsx, filasATexto, preprocesarAdjuntos } = require('..');

const fixture = (nombre) => fs.readFileSync(path.join(__dirname, 'fixtures', nombre));
const XLSX = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet';

test('clasifica los adjuntos: .xlsx se lee, las imágenes se ignoran y el resto no está soportado', () => {
  assert.equal(clasificarAdjunto({ filename: 'pedido.xlsx', contentType: 'application/octet-stream' }), 'xlsx');
  assert.equal(clasificarAdjunto({ filename: 'sin-extension', contentType: XLSX }), 'xlsx');
  assert.equal(clasificarAdjunto({ filename: 'PEDIDO.XLSX', contentType: '' }), 'xlsx');
  assert.equal(clasificarAdjunto({ filename: 'logo.png', contentType: 'image/png' }), 'ignorar');
  assert.equal(clasificarAdjunto({ filename: 'pedido.xls', contentType: 'application/vnd.ms-excel' }), 'no_soportado');
  assert.equal(clasificarAdjunto({ filename: 'pedido.pdf', contentType: 'application/pdf' }), 'no_soportado');
  assert.equal(clasificarAdjunto({ filename: 'pedido.csv', contentType: 'text/csv' }), 'no_soportado');
});

test('lee solo la primera hoja, con las celdas como texto y sin filas vacías', async () => {
  const { hoja, filas } = await leerXlsx(fixture('pedido.xlsx'));
  assert.equal(hoja, 'Pedido');
  assert.deepEqual(filas, [
    ['Talleres Ferran - Pedido OC-2211'],         // celda combinada: una sola vez
    ['Ref.', 'Descripción', 'Cant.', 'Precio'],
    ['TOR-M8X30-ZN', 'Tornillo M8x30', '500', '0.082'],
    ['ARAND 8', 'Arandela M8', '1000'],           // precio vacío al final: se quita
    ['TUE-M8-ZN', 'Tuerca M8', '200 uds', '0.027'],
    ['Fecha entrega', '2026-11-12'],              // fecha sin hora
  ]);
});

test('una barra o un salto de línea dentro de una celda no rompen el formato', async () => {
  const { filas } = await leerXlsx(fixture('celdas-raras.xlsx'));
  assert.deepEqual(filas.slice(1), [
    ['DIS-COR-125', 'entregar en muelle 2 \\| antes de las 12'],
    ['BRO-HSS-8', 'línea uno línea dos'],
  ]);
});

test('el texto del Excel tiene siempre la misma forma: nombre, hoja y una línea por fila', () => {
  assert.equal(
    filasATexto('pedido.xlsx', 'Pedido', [['Ref.', 'Cant.'], ['TOR-M8X30-ZN', '500']]),
    'Adjunto pedido.xlsx (hoja Pedido):\nRef. | Cant.\nTOR-M8X30-ZN | 500',
  );
});

test('preprocesa una mezcla de adjuntos', async () => {
  const r = await preprocesarAdjuntos([
    { filename: 'logo.png', contentType: 'image/png', content: Buffer.from('') },
    { filename: 'pedido.xlsx', contentType: XLSX, content: fixture('pedido.xlsx') },
    { filename: 'viejo.xls', contentType: 'application/vnd.ms-excel', content: Buffer.from('') },
  ]);
  assert.equal(r.ignorados, 1);
  assert.deepEqual(r.noSoportados, [{ nombre: 'viejo.xls', formato: 'xls' }]);
  assert.equal(r.excels.length, 1);
  assert.ok(r.texto.startsWith('Adjunto pedido.xlsx (hoja Pedido):\nTalleres Ferran - Pedido OC-2211\nRef. | Descripción'));
});

test('sin adjuntos no hay texto ni nada no soportado', async () => {
  assert.deepEqual(await preprocesarAdjuntos([]), { excels: [], noSoportados: [], ignorados: 0, texto: '' });
});
