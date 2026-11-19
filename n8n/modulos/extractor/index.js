module.exports = {
  ...require('./preprocesado'),
  ...require('./extractor'),
  // El runner solo permite cargar el paquete por su nombre, no sus ficheros: la versión se exporta aquí.
  VERSION: require('./package.json').version,
};
