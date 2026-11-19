const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const { extraerDeterminista, extraerDeExcel, extraerDeTexto, leerXlsx } = require('..');

const CODIGOS = ['TOR-M8X30-ZN', 'TOR-M10X40-ZN', 'TUE-M8-ZN', 'TUE-M10-ZN', 'ARA-M8-ZN', 'GUA-NIT-L', 'GAF-PROT-INC', 'DIS-COR-125'];
const excel = (filas) => ({ nombre: 'pedido.xlsx', hoja: 'Hoja1', filas });

// ---------------------------------------------------------------- Excel

test('Excel: encuentra la cabecera debajo del título y lee por nombre de columna', async () => {
  const leido = await leerXlsx(fs.readFileSync(path.join(__dirname, 'fixtures', 'pedido.xlsx')));
  assert.deepEqual(extraerDeExcel({ nombre: 'pedido.xlsx', ...leido }), [
    { texto: 'TOR-M8X30-ZN | Tornillo M8x30 | 500 | 0.082', referencia: 'TOR-M8X30-ZN', cantidad: 500, unidad: null, precio: 0.082 },
    // La referencia del cliente se toma tal cual: la traduce R08 con las equivalencias.
    { texto: 'ARAND 8 | Arandela M8 | 1000', referencia: 'ARAND 8', cantidad: 1000, unidad: null, precio: null },
    // "200 uds" no es una cantidad limpia: esa línea queda para la IA.
  ]);
});

test('Excel: cabeceras en catalán y con acentos o dos puntos', () => {
  const lineas = extraerDeExcel(excel([['Codi:', 'Descripció', 'Quantitat', 'Preu'], ['GUA-NIT-L', 'Guants', '5', '6,20']]));
  assert.deepEqual(lineas, [{ texto: 'GUA-NIT-L | Guants | 5 | 6,20', referencia: 'GUA-NIT-L', cantidad: 5, unidad: null, precio: 6.2 }]);
});

test('Excel: con cabeceras desconocidas no saca nada (queda para la IA)', () => {
  assert.deepEqual(extraerDeExcel(excel([['Item', 'Qtty.'], ['TOR-M8X30-ZN', '500']])), []);
});

test('Excel: ignora las filas de total y las que no tienen referencia o cantidad entera', () => {
  const lineas = extraerDeExcel(excel([
    ['Ref.', 'Cant.'],
    ['TOR-M8X30-ZN', '500'],
    ['', '300'],
    ['TUE-M8-ZN', '1.000'],
    ['ARA-M8-ZN', '2,5'],
    ['Total', '800'],
  ]));
  assert.deepEqual(lineas.map((l) => [l.referencia, l.cantidad]), [['TOR-M8X30-ZN', 500]]);
});

// ---------------------------------------------------------------- Texto

test('Texto: código del catálogo con la cantidad detrás, en distintos formatos', () => {
  const lineas = extraerDeTexto([
    'TOR-M8X30-ZN 500 uds',
    '- TUE-M8-ZN: 1000',
    'tor-m10x40-zn x 300',
    'GUA-NIT-L  10 caixes a 6,50',
  ].join('\n'), CODIGOS);
  assert.deepEqual(lineas.map((l) => [l.referencia, l.cantidad, l.unidad]), [
    ['TOR-M8X30-ZN', 500, 'uds'],
    ['TUE-M8-ZN', 1000, null],
    ['TOR-M10X40-ZN', 300, null],
    ['GUA-NIT-L', 10, 'caixes'],
  ]);
  assert.equal(lineas[0].texto, 'TOR-M8X30-ZN 500 uds');
  assert.ok(lineas.every((l) => l.precio === null));
});

test('Texto: cantidad al principio de la línea, antes del código', () => {
  const lineas = extraerDeTexto('500 uds de TOR-M8X30-ZN\n- 200 DIS-COR-125', CODIGOS);
  assert.deepEqual(lineas.map((l) => [l.referencia, l.cantidad]), [['TOR-M8X30-ZN', 500], ['DIS-COR-125', 200]]);
});

test('Texto: un número de pedido con forma de código no es una línea', () => {
  assert.deepEqual(extraerDeTexto('Pedido PED-2026-0143 500 uds', CODIGOS), []);
});

test('Texto: un número suelto antes del código no es la cantidad', () => {
  assert.deepEqual(extraerDeTexto('Pedido semana 46 TOR-M8X30-ZN', CODIGOS), []);
});

test('Texto: cantidades que no son enteros limpios no se leen', () => {
  assert.deepEqual(extraerDeTexto('TOR-M8X30-ZN 1.000 uds\nTUE-M8-ZN 2,5\nARA-M8-ZN unos 300', CODIGOS), []);
});

test('Texto: las líneas citadas de un mensaje anterior se ignoran', () => {
  assert.deepEqual(extraerDeTexto('> TOR-M8X30-ZN 500 uds\nGracias', CODIGOS), []);
});

test('Texto: las equivalencias no las lee (son de R08), solo los códigos exactos', () => {
  assert.deepEqual(extraerDeTexto('- TORN 8X30: 1000', CODIGOS), []);
});

// ---------------------------------------------------------------- Juntos

test('extraerDeterminista junta Excel y texto, primero el Excel', () => {
  const lineas = extraerDeterminista({
    cuerpo: 'Y añadid TUE-M8-ZN 100 uds',
    excels: [excel([['Ref.', 'Cant.'], ['TOR-M8X30-ZN', '500']])],
    codigos: CODIGOS,
  });
  assert.deepEqual(lineas.map((l) => l.referencia), ['TOR-M8X30-ZN', 'TUE-M8-ZN']);
});

test('sin nada estructurado devuelve una lista vacía', () => {
  assert.deepEqual(extraerDeterminista({ cuerpo: 'Hola, necesito tornillos del 8.', excels: [], codigos: CODIGOS }), []);
});
