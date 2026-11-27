-- Datos maestros que faltaban del modelo (04, sección 5.3): conversiones de unidad (R10) y festivos (R06).
-- Solo las tablas: las reglas que las usan todavía no existen. Nada las lee por ahora.
-- Vuelta atrás: drop table erp.conversiones_unidad, erp.festivos;

create table erp.conversiones_unidad (
  producto  text not null references erp.productos (codigo),
  unidad    text not null check (unidad = lower(btrim(unidad))),
  factor    integer not null check (factor > 0),   -- unidades de venta que hay en una `unidad`
  primary key (producto, unidad)
);

create table erp.festivos (
  fecha   date primary key,
  nombre  text not null
);

alter table erp.conversiones_unidad enable row level security;
alter table erp.festivos enable row level security;
