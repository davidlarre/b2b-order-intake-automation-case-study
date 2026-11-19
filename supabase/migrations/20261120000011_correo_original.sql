-- App de revisión: el correo original, sus adjuntos y los mensajes de las decisiones.
-- - El .eml se guarda en un bucket PRIVADO de Storage ("correos"). Lo sube n8n al recibirlo (con la clave de
--   la automatización); solo lo pueden leer los usuarios con rol de ADV, con la misma comprobación que las
--   funciones de adv: app_metadata, nunca user_metadata. Plazo de conservación: 04, sección 8.
-- - De cada correo se guardan los adjuntos (nombre, tipo y tamaño) y el nombre del remitente, para que la cola
--   y el detalle los muestren sin abrir el .eml.
-- - Descartar exige una razón; el detalle devuelve el pedido creado (su número) y el correo con sus adjuntos.

-- ============================================================
-- Storage: bucket privado y lectura solo para ADV
-- ============================================================

insert into storage.buckets (id, name, public) values ('correos', 'correos', false)
on conflict (id) do nothing;

create policy "ADV lee los correos originales" on storage.objects
  for select to authenticated
  using (bucket_id = 'correos'
         and (auth.jwt() -> 'app_metadata' ->> 'rol') in ('adv', 'adv_responsable'));

-- ============================================================
-- Correos: adjuntos y nombre del remitente
-- ============================================================

alter table intake.correos
  add column remitente_nombre text,
  add column adjuntos jsonb not null default '[]'
    check (jsonb_typeof(adjuntos) = 'array');

drop function api.recibir_correo(text, text, text, text, timestamptz, text, text, text);
drop function intake.recibir_correo(text, text, text, text, timestamptz, text, text, text);

create function intake.recibir_correo(
  p_message_id text, p_remitente text, p_asunto text, p_autenticacion text,
  p_hora_recepcion timestamptz, p_origen text, p_hilo text default null, p_ruta_eml text default null,
  p_remitente_nombre text default null, p_adjuntos jsonb default '[]')
returns jsonb
language plpgsql security definer set search_path = '' as $$
declare
  v_caso bigint;
begin
  select c.caso into v_caso from intake.correos c where c.message_id = p_message_id;
  if found then
    return jsonb_build_object('caso', v_caso, 'duplicado', true);
  end if;

  insert into intake.casos (hora_recepcion, origen, hilo)
  values (p_hora_recepcion, p_origen, p_hilo)
  returning id into v_caso;

  insert into intake.correos (caso, direccion, message_id, hilo, remitente, asunto, autenticacion, ruta_eml,
                              remitente_nombre, adjuntos)
  values (v_caso, 'entrada', p_message_id, p_hilo, p_remitente, p_asunto, p_autenticacion, p_ruta_eml,
          nullif(btrim(coalesce(p_remitente_nombre, '')), ''), coalesce(p_adjuntos, '[]'));

  insert into intake.eventos (caso, tipo, actor, carga)
  values (v_caso, 'recibido', 'automatizacion',
          jsonb_build_object('origen', p_origen, 'adjuntos', jsonb_array_length(coalesce(p_adjuntos, '[]'))));

  return jsonb_build_object('caso', v_caso, 'duplicado', false);
end;
$$;

create function api.recibir_correo(
  message_id text, remitente text, asunto text, autenticacion text,
  hora_recepcion timestamptz, origen text, hilo text default null, ruta_eml text default null,
  remitente_nombre text default null, adjuntos jsonb default '[]')
returns jsonb
language sql security definer set search_path = '' as $$
  select intake.recibir_correo(message_id, remitente, asunto, autenticacion, hora_recepcion, origen, hilo, ruta_eml,
                               remitente_nombre, adjuntos);
$$;

revoke execute on function intake.recibir_correo(text, text, text, text, timestamptz, text, text, text, text, jsonb)
  from public, anon, authenticated, service_role;
revoke execute on function api.recibir_correo(text, text, text, text, timestamptz, text, text, text, text, jsonb)
  from public, anon, authenticated;
grant execute on function api.recibir_correo(text, text, text, text, timestamptz, text, text, text, text, jsonb)
  to service_role;

-- ============================================================
-- Descartar exige una razón
-- ============================================================

create or replace function adv.cerrar_caso(p_caso bigint, p_resultado text, p_texto text default null) returns jsonb
language plpgsql security definer set search_path = '' as $$
declare
  v_actor text := intake.exigir_adv();
  v_estado text;
begin
  if p_resultado is null or p_resultado not in ('descartado', 'procesado a mano') then
    raise exception 'Resultado de cierre no válido: %', coalesce(p_resultado, 'ninguno');
  end if;
  if p_resultado = 'descartado' and nullif(btrim(coalesce(p_texto, '')), '') is null then
    raise exception 'Para descartar un pedido hay que indicar por qué';
  end if;
  select estado into v_estado from intake.casos where id = p_caso for update;
  if not found then
    raise exception 'El caso % no existe', p_caso;
  end if;
  if v_estado in ('pedido_creado', 'derivado', 'cerrado') then
    raise exception 'El caso % ya está en un estado final (%)', p_caso, v_estado;
  end if;

  update intake.motivos set estado = 'resuelto', actor = v_actor,
         razon_forzado = nullif(btrim(coalesce(p_texto, '')), '')
  where caso = p_caso and estado = 'abierto';
  update intake.casos set estado = 'cerrado', resultado_cierre = p_resultado where id = p_caso;
  insert into intake.eventos (caso, tipo, actor, carga)
  values (p_caso, 'cerrado', v_actor, jsonb_build_object('resultado', p_resultado));
  return jsonb_build_object('caso', p_caso, 'estado', 'cerrado', 'resultado', p_resultado);
end;
$$;

-- ============================================================
-- Cola y detalle: adjuntos, correo original y pedido creado
-- ============================================================

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
        'cliente_por_remitente', c.cliente is null
                                 and not exists (select 1 from intake.motivos m
                                                 where m.caso = c.id and m.estado = 'abierto' and m.codigo = 'R02'),
        'remitente', co.remitente,
        'asunto', co.asunto,
        'adjuntos', co.adjuntos,
        'configuracion', c.configuracion,
        'motivos', (select coalesce(jsonb_agg(jsonb_build_object('codigo', m.codigo, 'linea', m.linea,
                                                                 'detalle', m.detalle) order by m.codigo, m.linea), '[]')
                    from intake.motivos m where m.caso = c.id and m.estado = 'abierto')
      ) as fila
      from intake.casos c
      left join erp.clientes cl on cl.codigo = c.cliente
      left join lateral (select remitente, asunto, adjuntos from intake.correos
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
      'resultado_cierre', c.resultado_cierre,
      'recibido', c.hora_recepcion, 'cliente', c.cliente, 'razon_social', cl.razon_social,
      'cliente_propuesto', v_propuesto,
      'cliente_por_remitente', c.cliente is null
                               and not exists (select 1 from intake.motivos m
                                               where m.caso = c.id and m.estado = 'abierto' and m.codigo = 'R02'),
      'clientes_del_remitente', intake.clientes_del_remitente(c.id),
      'nombres', intake.nombres(c.id),
      'pedido', (select jsonb_build_object('id', p.id, 'numero', p.numero) from erp.pedidos p
                 where p.caso = c.id order by p.id desc limit 1),
      'correo', (select jsonb_build_object('remitente', remitente, 'remitente_nombre', remitente_nombre,
                                           'asunto', asunto, 'autenticacion', autenticacion,
                                           'adjuntos', adjuntos, 'ruta_eml', ruta_eml)
                 from intake.correos where caso = c.id and direccion = 'entrada' order by id limit 1),
      'lineas', (select coalesce(jsonb_agg(jsonb_build_object(
                    'linea', l.linea, 'texto', l.texto_original, 'referencia', l.referencia,
                    'cantidad', l.cantidad, 'unidad', l.unidad, 'precio', l.precio,
                    'producto', l.producto, 'precio_referencia', l.precio_referencia, 'fuente', l.fuente,
                    'referencia_determinista', l.referencia_determinista,
                    'cantidad_determinista', l.cantidad_determinista,
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
