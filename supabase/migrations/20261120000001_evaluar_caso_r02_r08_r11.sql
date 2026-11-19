-- Corte vertical, paso 2: evaluar_caso con R02, R08 y R11 (04, sección 3; ADR 0001).
-- Cada regla es una función SQL que solo lee y devuelve sus motivos. evaluar_caso los escribe.

create extension if not exists pg_trgm with schema extensions;

-- Cada motivo dice qué salida provoca: revisión o pedir datos.
alter table intake.motivos
  add column salida text not null check (salida in ('revision', 'pedir_datos'));

-- Las referencias de las equivalencias se guardan normalizadas, para compararlas sin ambigüedad.
alter table erp.equivalencias
  add constraint referencia_normalizada check (referencia_cliente = upper(btrim(referencia_cliente)));

-- Dominios públicos: nunca sirven para sugerir un cliente por dominio (R02).
create table intake.dominios_publicos (
  dominio text primary key check (dominio = lower(btrim(dominio)))
);
alter table intake.dominios_publicos enable row level security;

insert into intake.dominios_publicos (dominio) values
  ('gmail.com'), ('googlemail.com'), ('hotmail.com'), ('hotmail.es'), ('outlook.com'), ('outlook.es'),
  ('live.com'), ('yahoo.com'), ('yahoo.es'), ('icloud.com'), ('me.com'), ('telefonica.net'),
  ('movistar.es'), ('terra.es'), ('orange.es'), ('vodafone.es'), ('protonmail.com'), ('proton.me'),
  ('gmx.es'), ('gmx.com');

-- Parámetro nuevo: similitud mínima para proponer un candidato por descripción (R08). Supuesto.
insert into intake.configuracion (parametro, valor) values ('r08_similitud_minima', '0.3');

create sequence erp.numero_pedido;

-- ============================================================
-- Auxiliares
-- ============================================================

-- Producto por código exacto de Orvalle o por equivalencia de ese cliente. Null si no lo encuentra.
create function intake.resolver_producto(p_cliente text, p_referencia text) returns text
language sql stable set search_path = '' as $$
  select coalesce(
    (select p.codigo from erp.productos p where p.codigo = upper(btrim(p_referencia))),
    (select e.producto from erp.equivalencias e
      where e.cliente = p_cliente and e.referencia_cliente = upper(btrim(p_referencia)))
  );
$$;

-- Tarifa pactada activa y vigente en la fecha de referencia; si no hay, precio general.
create function intake.precio_referencia(p_cliente text, p_producto text, p_fecha date) returns numeric
language sql stable set search_path = '' as $$
  select coalesce(
    (select t.precio_neto from erp.tarifas t
      where t.cliente = p_cliente and t.producto = p_producto and t.estado = 'activa'
        and t.desde <= p_fecha and (t.hasta is null or t.hasta >= p_fecha)
      order by t.desde desc limit 1),
    (select p.precio_general from erp.productos p where p.codigo = p_producto)
  );
$$;

-- ============================================================
-- Reglas: devuelven (linea, codigo, salida, detalle). No escriben nada.
-- ============================================================

-- R02: el remitente es contacto de un único cliente y no falla DMARC.
create function intake.r02_remitente(p_caso bigint)
returns table (linea integer, codigo text, salida text, detalle jsonb)
language sql stable set search_path = '' as $$
  with correo as (
    select lower(btrim(c.remitente)) as email, coalesce(c.autenticacion, '') as autenticacion
    from intake.correos c
    where c.caso = p_caso and c.direccion = 'entrada'
    order by c.id limit 1
  ),
  clientes_del_email as (
    select distinct ct.cliente from erp.contactos ct join correo on ct.email = correo.email
  ),
  dominio as (
    select split_part(correo.email, '@', 2) as d from correo
  ),
  clientes_del_dominio as (
    select distinct ct.cliente from erp.contactos ct join dominio on split_part(ct.email, '@', 2) = dominio.d
    where not exists (select 1 from intake.dominios_publicos dp where dp.dominio = dominio.d)
  )
  select null::integer, 'R02', 'revision', jsonb_build_object('tipo', 'remitente_no_verificado')
  from correo where correo.autenticacion ~* 'dmarc=fail'
  union all
  select null, 'R02', 'revision',
         jsonb_build_object('tipo', 'email_compartido', 'clientes', (select count(*) from clientes_del_email))
  where (select count(*) from clientes_del_email) > 1
  union all
  select null, 'R02', 'revision',
         jsonb_build_object('tipo', 'desconocido', 'sugerencia',
           case when (select count(*) from clientes_del_dominio) = 1
                then (select cliente from clientes_del_dominio) end)
  where (select count(*) from clientes_del_email) = 0;
$$;

-- R08: referencia por código exacto o equivalencia. Si no: candidatos por descripción → revisión;
-- ningún candidato → pedir datos.
create function intake.r08_referencias(p_caso bigint, p_cliente text)
returns table (linea integer, codigo text, salida text, detalle jsonb)
language sql stable set search_path = '' as $$
  select l.linea, 'R08',
         case when cand.lista is null then 'pedir_datos' else 'revision' end,
         case when cand.lista is null
              then jsonb_build_object('tipo', 'no_encontrada', 'referencia', l.referencia)
              else jsonb_build_object('tipo', 'solo_descripcion', 'candidatos', cand.lista) end
  from intake.lineas_caso l
  cross join lateral (
    select jsonb_agg(s.codigo order by s.similitud desc) as lista
    from (
      select p.codigo, extensions.similarity(p.descripcion, l.referencia) as similitud
      from erp.productos p
      where p.activo
        and extensions.similarity(p.descripcion, l.referencia) >=
            (select (cf.valor #>> '{}')::numeric from intake.configuracion cf
              where cf.parametro = 'r08_similitud_minima')
      order by similitud desc
      limit 3
    ) s
  ) cand
  where l.caso = p_caso and intake.resolver_producto(p_cliente, l.referencia) is null;
$$;

-- R11: precio pedido igual al de referencia, con la tolerancia de configuración. Sin precio → OK.
create function intake.r11_precios(p_caso bigint, p_cliente text, p_fecha date)
returns table (linea integer, codigo text, salida text, detalle jsonb)
language sql stable set search_path = '' as $$
  select l.linea, 'R11', 'revision',
         jsonb_build_object('precio_pedido', l.precio, 'precio_referencia', ref.precio,
                            'diferencia', l.precio - ref.precio, 'comercial', c.comercial_id)
  from intake.lineas_caso l
  join erp.clientes c on c.codigo = p_cliente
  cross join lateral (select intake.resolver_producto(p_cliente, l.referencia) as producto) r
  cross join lateral (select intake.precio_referencia(p_cliente, r.producto, p_fecha) as precio) ref
  where l.caso = p_caso
    and r.producto is not null
    and l.precio is not null
    and abs(l.precio - ref.precio) >
        (select (cf.valor #>> '{}')::numeric from intake.configuracion cf
          where cf.parametro = 'r11_tolerancia_precio_eur');
$$;

-- ============================================================
-- Contrato con el ERP (04, sección 5.2): crear el pedido
-- ============================================================

-- Corte vertical: sin R05 ni R06, la dirección es la única del cliente (o ninguna) y la fecha,
-- la de recepción. Se completan con su incremento.
create function erp.crear_pedido(p_caso bigint) returns bigint
language plpgsql security definer set search_path = '' as $$
declare
  v_cliente text;
  v_fecha date;
  v_pedido bigint;
begin
  select c.cliente, (c.hora_recepcion at time zone 'Europe/Madrid')::date
    into v_cliente, v_fecha
  from intake.casos c where c.id = p_caso;

  insert into erp.pedidos (numero, cliente, direccion, fecha_prevista, origen, caso)
  values (
    'PV' || lpad(nextval('erp.numero_pedido')::text, 6, '0'),
    v_cliente,
    (select d.id from erp.direcciones d where d.cliente = v_cliente
      and (select count(*) from erp.direcciones d2 where d2.cliente = v_cliente) = 1),
    v_fecha, 'automatico', p_caso)
  returning id into v_pedido;

  insert into erp.lineas_pedido (pedido, linea, producto, cantidad, precio_unitario)
  select v_pedido, l.linea, l.producto, l.cantidad, l.precio_referencia
  from intake.lineas_caso l where l.caso = p_caso;

  return v_pedido;
end;
$$;

-- ============================================================
-- Punto de entrada
-- ============================================================

create function intake.evaluar_caso(p_caso bigint) returns jsonb
language plpgsql security definer set search_path = '' as $$
declare
  v_caso intake.casos%rowtype;
  v_cliente text;
  v_fecha date;
  v_salida text;
  v_pedido bigint;
  v_motivos jsonb;
begin
  -- Bloquea el caso: dos evaluaciones a la vez del mismo caso no pueden crear dos pedidos.
  select * into v_caso from intake.casos where id = p_caso for update;
  if not found then
    raise exception 'El caso % no existe', p_caso;
  end if;
  if v_caso.estado in ('pedido_creado', 'derivado', 'cerrado') then
    raise exception 'El caso % ya está en un estado final (%)', p_caso, v_caso.estado;
  end if;

  -- Hora de referencia: la de recepción, nunca la actual (04, sección 3.2).
  v_fecha := (v_caso.hora_recepcion at time zone 'Europe/Madrid')::date;

  -- Los motivos abiertos de una evaluación anterior quedan sustituidos por los de esta.
  update intake.motivos set estado = 'resuelto', actor = 'evaluar_caso'
  where caso = p_caso and estado = 'abierto';

  -- R01–R04 cortan el flujo. En el corte vertical, solo R02.
  insert into intake.motivos (caso, linea, codigo, salida, detalle)
  select p_caso, r.linea, r.codigo, r.salida, r.detalle from intake.r02_remitente(p_caso) r;

  if found then
    v_salida := 'revision';
  else
    select ct.cliente into v_cliente
    from intake.correos c join erp.contactos ct on ct.email = lower(btrim(c.remitente))
    where c.caso = p_caso and c.direccion = 'entrada'
    order by c.id limit 1;

    update intake.casos set cliente = v_cliente where id = p_caso;

    update intake.lineas_caso l
    set producto = r.producto,
        precio_referencia = intake.precio_referencia(v_cliente, r.producto, v_fecha)
    from (select l2.id, intake.resolver_producto(v_cliente, l2.referencia) as producto
          from intake.lineas_caso l2 where l2.caso = p_caso) r
    where l.id = r.id;

    -- R05–R14 se evalúan todas y acumulan motivos. En el corte vertical, R08 y R11.
    insert into intake.motivos (caso, linea, codigo, salida, detalle)
    select p_caso, r.linea, r.codigo, r.salida, r.detalle from intake.r08_referencias(p_caso, v_cliente) r
    union all
    select p_caso, r.linea, r.codigo, r.salida, r.detalle from intake.r11_precios(p_caso, v_cliente, v_fecha) r;

    -- Algún motivo de revisión → revisión; si solo faltan datos → pedir datos; ninguno → automático.
    select case when bool_or(m.salida = 'revision') then 'revision'
                when bool_or(m.salida = 'pedir_datos') then 'pedir_datos'
                else 'automatico' end
      into v_salida
    from intake.motivos m where m.caso = p_caso and m.estado = 'abierto';
  end if;

  if v_salida = 'automatico' then
    v_pedido := erp.crear_pedido(p_caso);
    update intake.casos set estado = 'pedido_creado' where id = p_caso;
  elsif v_salida = 'pedir_datos' then
    update intake.casos set estado = 'pendiente_cliente' where id = p_caso;
  else
    update intake.casos set estado = 'en_revision' where id = p_caso;
  end if;

  select jsonb_agg(jsonb_build_object('codigo', m.codigo, 'linea', m.linea, 'salida', m.salida)
                   order by m.codigo, m.linea)
    into v_motivos
  from intake.motivos m where m.caso = p_caso and m.estado = 'abierto';

  -- El evento solo lleva códigos e identificadores, sin datos personales (04, sección 5.4).
  insert into intake.eventos (caso, tipo, actor, carga)
  values (p_caso, 'reglas_evaluadas', 'evaluar_caso',
          jsonb_build_object('salida', v_salida, 'motivos', coalesce(v_motivos, '[]'::jsonb),
                             'pedido', v_pedido, 'hora_referencia', v_caso.hora_recepcion));

  return jsonb_build_object('caso', p_caso, 'salida', v_salida, 'pedido', v_pedido,
                            'motivos', coalesce(v_motivos, '[]'::jsonb));
end;
$$;

-- ============================================================
-- Permisos: solo evaluar_caso, y solo para el rol de la automatización
-- ============================================================

revoke execute on all functions in schema intake, erp from public, anon, authenticated, service_role;
alter default privileges in schema intake, erp revoke execute on functions from public;

grant usage on schema intake to service_role;
grant execute on function intake.evaluar_caso(bigint) to service_role;
