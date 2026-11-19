-- App de revisión: la gestora necesita nombres (cliente, producto, comercial, teléfono), no códigos, y ver
-- producto y tarifa aunque el cliente aún no esté confirmado. Las funciones de adv los devuelven; la app
-- sigue sin leer tablas. Mismas firmas para cola y detalle_caso; una función nueva para buscar clientes.

-- El cliente con el que se puede adelantar producto y tarifa: el del caso; si R02 lo paró, el que propone
-- su dominio o, si el remitente es contacto de un único cliente (DMARC falla), ese.
create function intake.cliente_propuesto(p_caso bigint) returns text
language sql stable set search_path = '' as $$
  select coalesce(
    (select cliente from intake.casos where id = p_caso),
    (select m.detalle ->> 'sugerencia' from intake.motivos m
      where m.caso = p_caso and m.estado = 'abierto' and m.codigo = 'R02' and m.detalle ->> 'sugerencia' is not null
      limit 1),
    (select min(ct.cliente) from intake.correos c join erp.contactos ct on ct.email = lower(btrim(c.remitente))
      where c.caso = p_caso and c.direccion = 'entrada'
      having count(distinct ct.cliente) = 1)
  );
$$;

-- Los clientes de los que el remitente es contacto (para un email compartido: "¿de cuál es este pedido?").
create function intake.clientes_del_remitente(p_caso bigint) returns jsonb
language sql stable set search_path = '' as $$
  select coalesce(jsonb_agg(distinct ct.cliente), '[]')
  from intake.correos c join erp.contactos ct on ct.email = lower(btrim(c.remitente))
  where c.caso = p_caso and c.direccion = 'entrada';
$$;

-- Los nombres de todo lo que aparece en el caso, para que la app no muestre códigos.
create function intake.nombres(p_caso bigint) returns jsonb
language sql stable set search_path = '' as $$
  with clientes as (
    select intake.cliente_propuesto(p_caso) as codigo
    union select jsonb_array_elements_text(intake.clientes_del_remitente(p_caso))
    union select m.detalle ->> 'sugerencia' from intake.motivos m where m.caso = p_caso
  ),
  productos as (
    select l.producto as codigo from intake.lineas_caso l where l.caso = p_caso
    union select intake.resolver_producto(intake.cliente_propuesto(p_caso), l.referencia)
          from intake.lineas_caso l where l.caso = p_caso
    union select jsonb_array_elements_text(m.detalle -> 'candidatos') from intake.motivos m
          where m.caso = p_caso and m.codigo = 'R08' and m.detalle ? 'candidatos'
  ),
  comerciales as (
    select m.detalle ->> 'comercial' as id from intake.motivos m where m.caso = p_caso and m.codigo = 'R11'
  )
  select jsonb_build_object(
    'clientes', coalesce((select jsonb_object_agg(c.codigo, jsonb_build_object('razon_social', c.razon_social,
                                                                                 'telefono', c.telefono))
                          from erp.clientes c where c.codigo in (select codigo from clientes)), '{}'),
    'productos', coalesce((select jsonb_object_agg(p.codigo, p.descripcion)
                           from erp.productos p where p.codigo in (select codigo from productos)), '{}'),
    'comerciales', coalesce((select jsonb_object_agg(co.id, co.nombre)
                             from erp.comerciales co where co.id in (select id from comerciales)), '{}')
  );
$$;

create or replace function adv.cola() returns jsonb
language plpgsql stable security definer set search_path = '' as $$
declare
  v_ahora timestamp := now() at time zone 'Europe/Madrid';
begin
  perform intake.exigir_adv();
  return coalesce((
    select jsonb_agg(fila order by (fila ->> 'prioridad')::int, fila ->> 'recibido')
    from (
      select jsonb_build_object(
        'caso', c.id,
        'recibido', c.hora_recepcion,
        'prioridad', case when c.tipo = 'reclamacion' then 1
                          when (c.hora_recepcion at time zone 'Europe/Madrid')::date = v_ahora::date
                               and v_ahora::time < time '13:00' then 2
                          else 3 end,
        'cliente', c.cliente,
        'razon_social', cl.razon_social,
        'cliente_propuesto', (select razon_social from erp.clientes
                              where codigo = intake.cliente_propuesto(c.id) and c.cliente is null),
        'remitente', co.remitente,
        'asunto', co.asunto,
        'configuracion', c.configuracion,
        'motivos', (select coalesce(jsonb_agg(jsonb_build_object('codigo', m.codigo, 'linea', m.linea,
                                                                 'detalle', m.detalle) order by m.codigo, m.linea), '[]')
                    from intake.motivos m where m.caso = c.id and m.estado = 'abierto')
      ) as fila
      from intake.casos c
      left join erp.clientes cl on cl.codigo = c.cliente
      left join lateral (select remitente, asunto from intake.correos
                         where caso = c.id and direccion = 'entrada' order by id limit 1) co on true
      where c.estado = 'en_revision'
    ) t
  ), '[]'::jsonb);
end;
$$;

create or replace function adv.detalle_caso(p_caso bigint) returns jsonb
language plpgsql stable security definer set search_path = '' as $$
declare
  v_propuesto text;
  v_fecha date;
begin
  perform intake.exigir_adv();
  v_propuesto := intake.cliente_propuesto(p_caso);
  select (hora_recepcion at time zone 'Europe/Madrid')::date into v_fecha from intake.casos where id = p_caso;
  return (
    select jsonb_build_object(
      'caso', c.id, 'estado', c.estado, 'tipo', c.tipo, 'configuracion', c.configuracion,
      'recibido', c.hora_recepcion, 'cliente', c.cliente, 'razon_social', cl.razon_social,
      'cliente_propuesto', v_propuesto,
      'clientes_del_remitente', intake.clientes_del_remitente(c.id),
      'nombres', intake.nombres(c.id),
      'correo', (select jsonb_build_object('remitente', remitente, 'asunto', asunto, 'autenticacion', autenticacion)
                 from intake.correos where caso = c.id and direccion = 'entrada' order by id limit 1),
      'lineas', (select coalesce(jsonb_agg(jsonb_build_object(
                    'linea', l.linea, 'texto', l.texto_original, 'referencia', l.referencia,
                    'cantidad', l.cantidad, 'unidad', l.unidad, 'precio', l.precio,
                    'producto', l.producto, 'precio_referencia', l.precio_referencia, 'fuente', l.fuente,
                    'referencia_determinista', l.referencia_determinista,
                    'cantidad_determinista', l.cantidad_determinista,
                    -- Si el cliente no está confirmado, lo que serían producto y tarifa con el propuesto.
                    'producto_propuesto', case when c.cliente is null and v_propuesto is not null
                                               then intake.resolver_producto(v_propuesto, l.referencia) end,
                    'precio_propuesto', case when c.cliente is null and v_propuesto is not null
                                             then intake.precio_referencia(v_propuesto,
                                                    intake.resolver_producto(v_propuesto, l.referencia), v_fecha) end)
                    order by l.linea), '[]')
                 from intake.lineas_caso l where l.caso = c.id),
      'motivos', (select coalesce(jsonb_agg(jsonb_build_object(
                     'codigo', m.codigo, 'linea', m.linea, 'salida', m.salida, 'detalle', m.detalle,
                     'estado', m.estado, 'accion', intake.accion_motivo(m.codigo, m.detalle))
                     order by m.codigo, m.linea), '[]')
                  from intake.motivos m where m.caso = c.id and m.estado in ('abierto', 'forzado')),
      'eventos', (select coalesce(jsonb_agg(jsonb_build_object('tipo', e.tipo, 'actor', e.actor, 'fecha', e.fecha)
                                             order by e.id), '[]')
                  from intake.eventos e where e.caso = c.id))
    from intake.casos c
    left join erp.clientes cl on cl.codigo = c.cliente
    where c.id = p_caso
  );
end;
$$;

-- Buscar un cliente por nombre o código, para confirmar un remitente desconocido sin sugerencia.
create function adv.buscar_clientes(p_texto text) returns jsonb
language plpgsql stable security definer set search_path = '' as $$
begin
  perform intake.exigir_adv();
  return coalesce((
    select jsonb_agg(jsonb_build_object('codigo', codigo, 'razon_social', razon_social) order by razon_social)
    from (select codigo, razon_social from erp.clientes
          where razon_social ilike '%' || btrim(p_texto) || '%' or codigo ilike btrim(p_texto) || '%'
          order by razon_social limit 20) t
  ), '[]'::jsonb);
end;
$$;

revoke execute on function intake.cliente_propuesto(bigint), intake.clientes_del_remitente(bigint),
                           intake.nombres(bigint)
  from public, anon, authenticated, service_role;
revoke execute on function adv.buscar_clientes(text) from public, anon, service_role;
grant execute on function adv.buscar_clientes(text) to authenticated;
