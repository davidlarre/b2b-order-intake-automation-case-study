-- Corte vertical: esquemas mínimos erp e intake (04, sección 5.3).
-- Solo lo que necesitan R02, R08 y R11. El resto de tablas se añade con su incremento.

create schema erp;
create schema intake;

-- La API no expone estos esquemas y los roles de la API no tienen permisos:
-- la automatización entrará solo por funciones (04, sección 5.2), en el paso 2.
revoke all on schema erp, intake from public, anon, authenticated;

-- ============================================================
-- erp: ERP simulado
-- ============================================================

create table erp.comerciales (
  id      text primary key,
  nombre  text not null,
  email   text not null unique check (email = lower(email))
);

create table erp.productos (
  codigo          text primary key check (codigo = upper(btrim(codigo))),
  descripcion     text not null,
  unidad_venta    text not null,
  embalaje        integer not null default 1 check (embalaje > 0),
  minimo          integer not null default 1 check (minimo > 0),
  activo          boolean not null default true,
  sustituto       text references erp.productos (codigo),
  precio_general  numeric(12, 4) not null check (precio_general >= 0)
);

create table erp.clientes (
  codigo        text primary key,
  cif           text not null unique,
  razon_social  text not null,
  telefono      text,
  bloqueado     boolean not null default false,
  comercial_id  text not null references erp.comerciales (id)
);

create table erp.direcciones (
  id          bigint generated always as identity primary key,
  cliente     text not null references erp.clientes (codigo),
  calle       text not null,
  numero      text not null,
  nave        text,
  cp          text not null check (cp ~ '^[0-9]{5}$'),
  poblacion   text not null
);

-- Un email repetido en varios clientes es un email compartido (R02): por eso no es único global.
create table erp.contactos (
  id       bigint generated always as identity primary key,
  cliente  text not null references erp.clientes (codigo),
  email    text not null check (email = lower(btrim(email))),
  nombre   text,
  unique (cliente, email)
);

create table erp.tarifas (
  id           bigint generated always as identity primary key,
  cliente      text not null references erp.clientes (codigo),
  producto     text not null references erp.productos (codigo),
  precio_neto  numeric(12, 4) not null check (precio_neto >= 0),
  desde        date not null,
  hasta        date,
  estado       text not null default 'activa' check (estado in ('activa', 'pendiente')),
  origen       text not null,
  unique (cliente, producto, desde),
  check (hasta is null or hasta >= desde)
);

create table erp.equivalencias (
  id                  bigint generated always as identity primary key,
  cliente             text not null references erp.clientes (codigo),
  referencia_cliente  text not null,
  producto            text not null references erp.productos (codigo),
  origen              text not null check (origen in ('migracion', 'revision')),
  creada_por          text,
  creada_en           timestamptz not null default now(),
  validada_por        text,
  validada_en         timestamptz,
  unique (cliente, referencia_cliente)
);

create table erp.pedidos (
  id                  bigint generated always as identity primary key,
  numero              text not null unique,
  cliente             text not null references erp.clientes (codigo),
  num_pedido_cliente  text,
  direccion           bigint references erp.direcciones (id),
  fecha_prevista      date not null,
  origen              text not null check (origen in ('historico', 'automatico', 'revision', 'manual')),
  caso                bigint,
  creado_en           timestamptz not null default now()
);

create table erp.lineas_pedido (
  pedido           bigint not null references erp.pedidos (id),
  linea            integer not null,
  producto         text not null references erp.productos (codigo),
  cantidad         numeric(12, 3) not null check (cantidad > 0),
  precio_unitario  numeric(12, 4) not null check (precio_unitario >= 0),
  primary key (pedido, linea)
);

-- ============================================================
-- intake: la automatización
-- ============================================================

create table intake.configuracion (
  parametro  text primary key,
  valor      jsonb not null
);

create table intake.casos (
  id                bigint generated always as identity primary key,
  tipo              text,
  estado            text not null default 'recibido'
                    check (estado in ('recibido', 'clasificado', 'pendiente_cliente', 'en_revision',
                                      'pedido_creado', 'derivado', 'cerrado')),
  resultado_cierre  text,
  cliente           text references erp.clientes (codigo),
  hora_recepcion    timestamptz not null,
  origen            text not null check (origen in ('gmail', 'pruebas')),
  hilo              text
);

create table intake.correos (
  id               bigint generated always as identity primary key,
  caso             bigint not null references intake.casos (id),
  direccion        text not null check (direccion in ('entrada', 'salida')),
  message_id       text not null unique,
  hilo             text,
  remitente        text not null,
  asunto           text,
  autenticacion    text,
  ruta_eml         text
);

create table intake.extracciones (
  id               bigint generated always as identity primary key,
  caso             bigint not null references intake.casos (id),
  prompt           text not null,
  version          text not null,
  modelo           text,
  configuracion    text not null check (configuracion in ('solo_reglas', 'solo_ia', 'hibrido')),
  resultado        jsonb not null,
  valido           boolean not null,
  tokens_entrada   integer,
  tokens_salida    integer,
  coste_usd        numeric(10, 6),
  creada_en        timestamptz not null default now()
);

create table intake.lineas_caso (
  id                 bigint generated always as identity primary key,
  caso               bigint not null references intake.casos (id),
  linea              integer not null,
  texto_original     text,
  referencia         text,
  cantidad           numeric(12, 3),
  unidad             text,
  precio             numeric(12, 4),
  producto           text references erp.productos (codigo),
  cantidad_uv        numeric(12, 3),
  precio_referencia  numeric(12, 4),
  fuente             text check (fuente in ('determinista', 'ia', 'ambas')),
  unique (caso, linea)
);

create table intake.motivos (
  id             bigint generated always as identity primary key,
  caso           bigint not null references intake.casos (id),
  linea          integer,
  codigo         text not null,
  detalle        jsonb not null default '{}',
  estado         text not null default 'abierto' check (estado in ('abierto', 'resuelto', 'forzado')),
  razon_forzado  text,
  actor          text,
  fecha          timestamptz not null default now()
);

-- Registro de eventos: solo se añaden filas (04, sección 5.4). El trigger también para al superusuario.
create table intake.eventos (
  id     bigint generated always as identity primary key,
  caso   bigint references intake.casos (id),
  tipo   text not null,
  actor  text not null,
  carga  jsonb not null default '{}',
  fecha  timestamptz not null default now()
);

create function intake.eventos_solo_anadir() returns trigger
language plpgsql as $$
begin
  raise exception 'intake.eventos solo admite inserciones';
end;
$$;

create trigger eventos_solo_anadir
  before update or delete on intake.eventos
  for each row execute function intake.eventos_solo_anadir();

create trigger eventos_sin_truncate
  before truncate on intake.eventos
  for each statement execute function intake.eventos_solo_anadir();
