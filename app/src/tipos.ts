// La forma de lo que devuelven las funciones de adv (supabase/migrations/2026112000000{9,10,11}_*.sql y
// 20261126000001_no_son_pedidos.sql).

export type Adjunto = { nombre: string | null; tipo: string | null; tamano: number | null };

export type MotivoCola = { codigo: string; linea: number | null; detalle: Record<string, unknown> };

export type FilaCola = {
  caso: number;
  recibido: string;
  prioridad: 1 | 2 | 3;
  cliente: string | null;
  razon_social: string | null;
  cliente_propuesto: string | null;
  cliente_por_remitente: boolean;
  remitente: string | null;
  asunto: string | null;
  adjuntos: Adjunto[];
  configuracion: string | null;
  motivos: MotivoCola[];
};

export type Clasificacion = {
  tipo: string | null;
  destino: 'contabilidad' | 'archivo' | 'ninguno' | null;
  modelo: string | null;
  version: string | null;
  fecha: string | null;
};

export type FilaNoPedido = {
  caso: number;
  recibido: string;
  remitente: string | null;
  remitente_nombre: string | null;
  asunto: string | null;
  adjuntos: Adjunto[];
  ruta_eml: string | null;
  clasificacion: Clasificacion;
};

export type Accion = 'forzar' | 'forzar_con_telefono' | 'bloqueado_otro_dueno' | 'corregir_linea' | 'solo_cerrar';

export type Motivo = MotivoCola & {
  salida: 'revision' | 'pedir_datos';
  estado: 'abierto' | 'forzado';
  accion: Accion;
};

export type Linea = {
  linea: number;
  texto: string | null;
  referencia: string | null;
  cantidad: number | null;
  unidad: string | null;
  precio: number | null;
  producto: string | null;
  precio_referencia: number | null;
  fuente: 'ia' | 'determinista' | 'ambas' | null;
  referencia_determinista: string | null;
  cantidad_determinista: number | null;
  producto_propuesto: string | null;
  precio_propuesto: number | null;
};

export type Nombres = {
  clientes: Record<string, { razon_social: string; telefono: string | null }>;
  productos: Record<string, string>;
  comerciales: Record<string, string>;
};

export type Detalle = {
  caso: number;
  estado: string;
  tipo: string | null;
  configuracion: string | null;
  resultado_cierre: string | null;
  recibido: string;
  cliente: string | null;
  razon_social: string | null;
  cliente_propuesto: string | null;
  cliente_por_remitente: boolean;
  clientes_del_remitente: string[];
  nombres: Nombres;
  pedido: { id: number; numero: string } | null;
  correo: {
    remitente: string;
    remitente_nombre: string | null;
    asunto: string | null;
    autenticacion: string | null;
    adjuntos: Adjunto[];
    ruta_eml: string | null;
  } | null;
  lineas: Linea[];
  motivos: Motivo[];
  eventos: { tipo: string; actor: string; fecha: string }[];
};

export type Razon = 'verificado_telefono' | 'cliente_confirmado' | 'lectura_comprobada' | 'otra';
