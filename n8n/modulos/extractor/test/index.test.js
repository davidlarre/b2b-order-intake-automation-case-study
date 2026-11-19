const { test } = require('node:test');
const assert = require('node:assert/strict');

const modulo = require('..');

test('exporta la versión del paquete (el runner no deja cargar package.json)', () => {
  assert.equal(modulo.VERSION, require('../package.json').version);
  assert.match(modulo.VERSION, /^\d+\.\d+\.\d+$/);
});
