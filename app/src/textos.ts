// Todo lo que lee la gestora: frases con nombres de cliente y de producto, nunca códigos internos.
// Las decisiones las comprueba la base de datos; aquí solo se explican y se proponen.

import type { Adjunto, Detalle, FilaCola, Linea, Motivo, MotivoCola, Nombres, Razon } from './tipos';

type D = Record<string, any>;

// ---------------------------------------------------------------- formatos

export const numero = (n: unknown) => Number(n).toLocaleString('es-ES', { maximumFractionDigits: 3 });
export const euros = (n: unknown) =>
  `${Number(n).toLocaleString('es-ES', { minimumFractionDigits: 2, maximumFractionDigits: 4 })} €`;

export function haceCuanto(desde: string) {
  const minutos = Math.max(0, Math.round((Date.now() - new Date(desde).getTime()) / 60000));
  if (minutos < 1) return 'ahora mismo';
  if (minutos < 60) return `hace ${minutos} min`;
  if (minutos < 60 * 24) return `hace ${Math.round(minutos / 60)} h`;
  const dias = Math.round(minutos / 60 / 24);
  return dias === 1 ? 'ayer' : `hace ${dias} días`;
}

export const fechaHora = (iso: string) =>
  new Date(iso).toLocaleString('es-ES', { dateStyle: 'full', timeStyle: 'short' });

export function hoyALas(iso: string) {
  const d = new Date(iso);
  const hora = d.toLocaleTimeString('es-ES', { hour: 'numeric', minute: '2-digit' });
  const hoy = new Date();
  return d.toDateString() === hoy.toDateString() ? `hoy a las ${hora}` : `el ${d.toLocaleDateString('es-ES')} a las ${hora}`;
}

const extension = (a: Adjunto) => (a.nombre?.match(/\.([a-z0-9]+)$/i)?.[1] ?? '').toLowerCase();

export function describirAdjuntos(adjuntos: Adjunto[]) {
  if (adjuntos.length === 0) return 'Sin adjuntos.';
  const nombres = adjuntos.map((a) => a.nombre ?? 'sin nombre').join(', ');
  return `${adjuntos.length === 1 ? '1 adjunto' : `${adjuntos.length} adjuntos`}: ${nombres}.`;
}

// ---------------------------------------------------------------- nombres

export const nombreCliente = (n: Nombres, codigo: string | null | undefined) =>
  (codigo && n.clientes[codigo]?.razon_social) || codigo || '';
export const nombreProducto = (n: Nombres, codigo: string | null | undefined) =>
  (codigo && n.productos[codigo]) || codigo || '';
const corto = (razon: string) => razon.replace(/,?\s+(S\.L\.|S\.A\.|S\.C\.P\.|S\.L\.U\.)$/, '');

// ---------------------------------------------------------------- la cola

// "Por qué está en revisión": una frase concreta por pedido, a partir de su motivo principal.
const ORDEN = ['R02', 'R11', 'M02', 'M01', 'R08', 'R12'];
const principal = <T extends MotivoCola>(motivos: T[]) =>
  [...motivos].sort((a, b) => ORDEN.indexOf(a.codigo) - ORDEN.indexOf(b.codigo))[0];

export function porQueEnRevision(f: FilaCola): string {
  const m = principal(f.motivos);
  if (!m) return '';
  const d = m.detalle as D;
  const otros = f.motivos.length > 1 ? ` (y ${f.motivos.length - 1} cosa${f.motivos.length > 2 ? 's' : ''} más)` : '';
  switch (m.codigo) {
    case 'R02':
      if (d.tipo === 'remitente_no_verificado') return `Remitente sin verificar: podría no ser quien dice${otros}`;
      if (d.tipo === 'email_compartido') return `El remitente es contacto de varios clientes${otros}`;
      return (f.cliente_propuesto ? `Remitente no registrado; parece de ${corto(f.cliente_propuesto)}` : 'Remitente no registrado') + otros;
    case 'R11':
      return `Precio distinto del pactado: ${euros(d.precio_pedido)} frente a ${euros(d.precio_referencia)}${otros}`;
    case 'M02': {
      const formatos = (d.formatos ?? []).map((x: string) => `.${x}`).join(', ');
      const xls = (d.formatos ?? []).includes('xls');
      return `${xls ? 'Pedido en un Excel antiguo' : 'Pedido en un adjunto'} (${formatos}) que no se puede leer${otros}`;
    }
    case 'M01':
      return f.adjuntos.length === 0
        ? 'El correo no incluye ningún producto y no trae adjuntos'
        : 'No hemos encontrado ningún producto en el correo ni en sus adjuntos';
    case 'R08':
      return `Un producto sin identificar${otros}`;
    case 'R12':
      return d.tipo === 'omision_ia'
        ? `Hay una línea que podría faltar en el pedido${otros}`
        : `Cantidad dudosa: ${numero(d.determinista?.cantidad)} o ${numero(d.ia?.cantidad)} uds${otros}`;
    default:
      return 'Necesita revisión';
  }
}

export const PRIORIDAD: Record<number, string | null> = {
  1: 'Reclamación',
  2: 'Sale hoy si se resuelve antes de las 13:00',
  3: null,
};

// ---------------------------------------------------------------- el detalle

export function etiquetaEstado(det: Detalle): string | null {
  if (det.estado === 'pedido_creado') return 'Pedido creado';
  if (det.estado === 'cerrado') return det.resultado_cierre === 'descartado' ? 'Descartado' : 'Tecleado a mano';
  if (det.estado === 'pendiente_cliente') return 'Esperando al cliente';
  if (det.motivos.some((m) => m.estado === 'abierto' && m.codigo === 'R11')) return 'Esperando al comercial';
  return null;
}

export type Cliente =
  | { confirmado: true; nombre: string; nota: string | null }
  | { confirmado: false; nota: string };

export function clienteDe(det: Detalle): Cliente {
  const n = det.nombres;
  if (det.cliente) return { confirmado: true, nombre: nombreCliente(n, det.cliente), nota: null };
  if (det.cliente_por_remitente && det.cliente_propuesto) {
    return { confirmado: true, nombre: nombreCliente(n, det.cliente_propuesto),
             nota: 'Identificado por el remitente, que es un contacto registrado del cliente.' };
  }
  const r02 = det.motivos.find((m) => m.estado === 'abierto' && m.codigo === 'R02');
  const d = (r02?.detalle ?? {}) as D;
  if (d.tipo === 'email_compartido') {
    return { confirmado: false, nota: `El remitente es contacto de varios clientes: ${det.clientes_del_remitente.map((c) => nombreCliente(n, c)).join(' y ')}.` };
  }
  if (d.tipo === 'remitente_no_verificado' && det.cliente_propuesto) {
    return { confirmado: false, nota: `Propuesto: ${nombreCliente(n, det.cliente_propuesto)} (el remitente es su contacto, pero no se ha podido verificar).` };
  }
  if (det.cliente_propuesto) {
    return { confirmado: false, nota: `Propuesto: ${nombreCliente(n, det.cliente_propuesto)} (por el dominio del correo).` };
  }
  return { confirmado: false, nota: 'No hay ningún cliente propuesto: el remitente no está registrado y su dominio no es de ningún cliente.' };
}

// Lo que puede hacer la gestora. Cada acción dice exactamente qué pasa al pulsarla.
export type Accion =
  | { tipo: 'crear'; etiqueta: string; cliente: string | null; razonR02?: Razon }
  | { tipo: 'buscar_cliente'; etiqueta: string }
  | { tipo: 'descargar'; etiqueta: string; adjunto: string }
  | { tipo: 'a_mano'; etiqueta: string }
  | { tipo: 'descartar'; etiqueta: string };

export type Situacion = { problema: string; queHacer: string; acciones: Accion[]; ademas: string[] };

const DESCARTAR: Accion = { tipo: 'descartar', etiqueta: 'Descartar: no es un pedido' };
const A_MANO: Accion = { tipo: 'a_mano', etiqueta: 'Ya lo he tecleado en el ERP' };

function frase(m: Motivo, det: Detalle): string {
  const d = m.detalle as D;
  const n = det.nombres;
  const l = det.lineas.find((x) => x.linea === m.linea);
  const prod = nombreProducto(n, l?.producto ?? l?.producto_propuesto) || `«${l?.texto ?? ''}»`;
  switch (m.codigo) {
    case 'R02':
      if (d.tipo === 'remitente_no_verificado') return 'el remitente no se ha podido verificar';
      if (d.tipo === 'email_compartido') return 'el remitente es contacto de varios clientes';
      return 'el remitente no está registrado';
    case 'R11': return `${prod}: piden ${euros(d.precio_pedido)} y la tarifa es ${euros(d.precio_referencia)}`;
    case 'R08': return `no sabemos qué producto es «${l?.texto ?? d.referencia ?? ''}»`;
    case 'R12': return d.tipo === 'omision_ia'
      ? `la línea «${l?.texto ?? ''}» podría faltar en el pedido`
      : `en ${prod} no está clara la cantidad: ${numero(d.determinista?.cantidad)} o ${numero(d.ia?.cantidad)}`;
    case 'M01': return 'no hay productos en el correo';
    case 'M02': return 'el pedido está en un adjunto que no se puede leer';
    default: return 'hay algo que revisar';
  }
}

export function situacion(det: Detalle): Situacion | null {
  const abiertos = det.motivos.filter((m) => m.estado === 'abierto');
  if (det.estado !== 'en_revision' || abiertos.length === 0) return null;
  const m = principal(abiertos)!;
  const d = m.detalle as D;
  const n = det.nombres;
  const todosConfirmables = abiertos.every((x) => x.accion === 'forzar' || x.accion === 'forzar_con_telefono');
  const ademas = abiertos.filter((x) => x !== m).map((x) => frase(x, det));
  const remitente = det.correo?.remitente ?? '';
  const l = det.lineas.find((x) => x.linea === m.linea);
  const prod = nombreProducto(n, l?.producto ?? l?.producto_propuesto);
  const s = (problema: string, queHacer: string, acciones: Accion[]): Situacion => ({ problema, queHacer, acciones, ademas });
  // Si hay algo que no se puede confirmar aquí, el pedido se resuelve a mano: no se ofrece crearlo.
  const crear = (a: Accion[]) => (todosConfirmables ? a : [A_MANO]);

  switch (m.codigo) {
    case 'R02': {
      if (d.tipo === 'remitente_no_verificado') {
        const c = det.cliente_propuesto;
        const tel = c ? n.clientes[c]?.telefono : null;
        return s(`El correo dice venir de ${nombreCliente(n, c)}, pero no se ha podido verificar el remitente: podría ser una suplantación.`,
          `Llama a ${nombreCliente(n, c)} a un teléfono del ERP${tel ? ` (${tel})` : ''}, nunca al que venga en el correo, y confirma que el pedido es suyo.`,
          [...crear([{ tipo: 'crear', etiqueta: 'Lo he verificado por teléfono: crear el pedido', cliente: c, razonR02: 'verificado_telefono' }]), DESCARTAR]);
      }
      if (d.tipo === 'email_compartido') {
        return s(`El remitente, ${remitente}, es contacto de varios clientes.`, 'Elige de cuál es este pedido.',
          [...crear(det.clientes_del_remitente.map((c) => ({ tipo: 'crear' as const, etiqueta: `Es de ${corto(nombreCliente(n, c))}: crear el pedido`, cliente: c }))), DESCARTAR]);
      }
      if (d.sugerencia) {
        const quien = corto(nombreCliente(n, d.sugerencia));
        return s(`No conocemos al remitente, ${remitente}. Su dominio es el de ${quien}.`,
          `Si el pedido es de ${quien}, confírmalo: se creará con sus tarifas. Si es de otro cliente, búscalo.`,
          [...crear([{ tipo: 'crear', etiqueta: `Es de ${quien}: crear el pedido`, cliente: d.sugerencia }, { tipo: 'buscar_cliente', etiqueta: 'Es de otro cliente' }]), DESCARTAR]);
      }
      return s(`No conocemos al remitente, ${remitente}, y su dominio no es de ningún cliente.`,
        'Si sabes de quién es, búscalo y crea el pedido. Si no, descártalo.',
        [...crear([{ tipo: 'buscar_cliente', etiqueta: 'Buscar el cliente' }]), DESCARTAR]);
    }
    case 'R11': {
      const comercial = n.comerciales[d.comercial] ?? 'el comercial';
      return s(`${prod}: el cliente pide ${euros(d.precio_pedido)}/ud y su tarifa es ${euros(d.precio_referencia)}/ud.`,
        `El precio lo tiene que aprobar ${comercial}. La aprobación por correo todavía no está en la app: si el precio es correcto, teclea el pedido en el ERP.`,
        [A_MANO, DESCARTAR]);
    }
    case 'M02': {
      const adjunto = (d.adjuntos ?? [])[0] ?? det.correo?.adjuntos.find((a) => extension(a) && d.formatos?.includes(extension(a)))?.nombre;
      const xls = (d.formatos ?? []).includes('xls');
      return s(`El pedido viene en ${xls ? 'un Excel antiguo (.xls)' : `un adjunto (${(d.formatos ?? []).join(', ')})`} que el sistema no sabe leer.`,
        'Descárgalo, teclea el pedido en el ERP y márcalo como hecho. Si no es un pedido, descártalo.',
        [...(adjunto && det.correo?.ruta_eml ? [{ tipo: 'descargar' as const, etiqueta: `Descargar ${adjunto}`, adjunto }] : []), A_MANO, DESCARTAR]);
    }
    case 'M01':
      return s((det.correo?.adjuntos.length ?? 0) === 0
          ? 'El correo no incluye ningún producto y no trae adjuntos.'
          : 'No hemos encontrado ningún producto en el correo ni en sus adjuntos.',
        'Abre el correo. Si es un pedido, tecléalo en el ERP o pide al cliente que lo reenvíe; si no lo es, descártalo.',
        [A_MANO, DESCARTAR]);
    case 'R08':
      return s(`No sabemos qué producto es «${l?.texto ?? d.referencia ?? ''}».`,
        d.tipo === 'solo_descripcion'
          ? `Puede ser: ${(d.candidatos ?? []).map((c: string) => nombreProducto(n, c)).join('; ')}. Corregirlo todavía no está en la app: teclea el pedido en el ERP.`
          : 'Corregirlo todavía no está en la app: teclea el pedido en el ERP.',
        [A_MANO, DESCARTAR]);
    case 'R12':
      if (d.tipo === 'omision_ia') {
        return s(`La línea «${l?.texto ?? ''}» está en el correo, pero no la leyó la IA: ${numero(d.cantidad)} de ${prod}.`,
          'Comprueba en el correo si va en el pedido.',
          [...crear([{ tipo: 'crear', etiqueta: 'Sí, va en el pedido: crearlo', cliente: null }]), { tipo: 'a_mano', etiqueta: 'No: lo tecleo yo en el ERP' }, DESCARTAR]);
      }
      return s(`No está clara la cantidad de ${prod}: el correo dice «${l?.texto ?? ''}».`,
        `Una lectura da ${numero(d.determinista?.cantidad)} y otra ${numero(d.ia?.cantidad)}. Comprueba cuál es la buena.`,
        [...crear([{ tipo: 'crear', etiqueta: `Son ${numero(d.ia?.cantidad)}: crear el pedido`, cliente: null }]),
         { tipo: 'a_mano', etiqueta: `Son ${numero(d.determinista?.cantidad)}: lo tecleo yo en el ERP` }, DESCARTAR]);
    default:
      return s('Este pedido necesita revisión.', 'Revisa el correo y decide.', [A_MANO, DESCARTAR]);
  }
}

export function razonPorDefecto(m: Motivo): Razon {
  if (m.accion === 'forzar_con_telefono') return 'verificado_telefono';
  return m.codigo === 'R12' ? 'lectura_comprobada' : 'cliente_confirmado';
}

// ---------------------------------------------------------------- productos pedidos

export function sinProductos(det: Detalle): string {
  const m02 = det.motivos.find((m) => m.codigo === 'M02');
  if (m02) {
    const adjuntos = ((m02.detalle as D).adjuntos ?? []).join(', ');
    return `No hemos podido leer los productos: están en ${adjuntos ? `el adjunto ${adjuntos}` : 'un adjunto'}, que no se puede leer.`;
  }
  return 'No hemos encontrado productos en el texto del correo ni en adjuntos que se puedan leer.';
}

export type FilaProducto = {
  nombre: string;
  codigo: string | null;
  sinIdentificar: boolean;
  cantidad: string;
  cantidadDudosa: string | null;
  precioCorreo: string | null;
  precioDudoso: boolean;
  precioAplicado: string | null;
};

export function filaProducto(l: Linea, det: Detalle): FilaProducto {
  const n = det.nombres;
  const codigo = l.producto ?? l.producto_propuesto;
  const abiertos = det.motivos.filter((m) => m.estado === 'abierto' && m.linea === l.linea);
  const discrepa = abiertos.find((m) => m.codigo === 'R12' && (m.detalle as D).tipo === 'discrepancia');
  const aplicado = l.producto ? l.precio_referencia : l.precio_propuesto;
  return {
    nombre: codigo ? nombreProducto(n, codigo) : `«${l.texto ?? l.referencia ?? ''}»`,
    codigo,
    sinIdentificar: !codigo && !!det.cliente,
    cantidad: `${numero(l.cantidad)} ${l.unidad ?? 'uds'}`,
    cantidadDudosa: discrepa ? `otra lectura da ${numero((discrepa.detalle as D).determinista?.cantidad)}` : null,
    precioCorreo: l.precio != null ? `${euros(l.precio)}/ud` : null,
    precioDudoso: abiertos.some((m) => m.codigo === 'R11'),
    precioAplicado: aplicado != null ? `${euros(aplicado)}/ud` : null,
  };
}

export function notaPrecios(det: Detalle): string | null {
  if (det.cliente || det.cliente_por_remitente || !det.cliente_propuesto) {
    return !det.cliente && !det.cliente_propuesto && det.lineas.length > 0
      ? 'Los precios se calcularán al confirmar el cliente.'
      : null;
  }
  const quien = corto(nombreCliente(det.nombres, det.cliente_propuesto));
  return `Precios calculados con la tarifa de ${quien}. Se confirmarán al confirmar el cliente.`;
}

// ---------------------------------------------------------------- información técnica

export const NOMBRE_EVENTO: Record<string, string> = {
  recibido: 'Correo recibido',
  extraido: 'Productos leídos',
  reglas_evaluadas: 'Reglas evaluadas',
  enviado_a_revision: 'Enviado a revisión',
  motivo_forzado: 'Confirmado por ADV',
  pedido_creado_en_revision: 'Pedido creado desde la revisión',
  cerrado: 'Cerrado',
  reevaluado: 'Vuelto a evaluar',
};
