-- App de revisión mínima: el esquema adv, la puerta de las personas de ADV (04, secciones 2.4 y 5.2).
-- La automatización entra por api; las personas, por adv. Cada rol ve solo su puerta, y en cada esquema
-- todas las funciones tienen permiso para el rol que lo usa.
-- Las restricciones se comprueban aquí, no en la pantalla: el rol de quien llama, qué motivos se pueden
-- forzar y la verificación por teléfono.
-- Los errores usan el código por defecto (P0001), nunca 42501: con un rol reservado, supautils trata mal los
-- errores de permiso (tests/test_entorno_supautils.py).

create schema adv;
revoke all on schema adv from public, anon, authenticated, service_role;
grant usage on schema adv to authenticated;
alter default privileges in schema adv revoke execute on functions from public;

-- ============================================================
-- Quién llama
-- ============================================================

-- El rol de ADV va en app_metadata, que solo escribe un administrador. user_metadata lo puede cambiar el
-- propio usuario, así que nunca se mira.
create function intake.rol_adv() returns text
language sql stable set search_path = '' as $$
  select auth.jwt() -> 'app_metadata' ->> 'rol';
$$;

-- Devuelve el identificador del usuario (para los eventos: nunca su email, 04 sección 5.4) o se niega.
create function intake.exigir_adv() returns text
language plpgsql stable set search_path = '' as $$
declare
  v_rol text := intake.rol_adv();
begin
  if v_rol is null or v_rol not in ('adv', 'adv_responsable') then
    raise exception 'Solo administración de ventas puede hacer esto (rol: %)', coalesce(v_rol, 'ninguno');
  end if;
  return auth.uid()::text;
end;
$$;

-- ============================================================
-- evaluar_caso respeta los motivos forzados
-- ============================================================

-- Un motivo forzado sigue valiendo al volver a evaluar mientras sea el mismo: mismo código, misma línea y
-- mismo detalle. Si los datos cambian (otra cantidad, otro precio), el detalle cambia y hay que decidir otra
-- vez, como una aprobación que solo vale para lo que se aprobó (04, sección 2.4).
create function intake.aplicar_forzados(p_caso bigint) returns void
language sql set search_path = '' as $$
  update intake.motivos nuevo
  set estado = 'forzado', razon_forzado = previo.razon_forzado, actor = previo.actor
  from (select distinct on (codigo, linea, detalle) codigo, linea, detalle, razon_forzado, actor
        from intake.motivos
        where caso = p_caso and estado = 'forzado'
        order by codigo, linea, detalle, id desc) previo
  where nuevo.caso = p_caso and nuevo.estado = 'abierto'
    and nuevo.codigo = previo.codigo
    and nuevo.linea is not distinct from previo.linea
    and nuevo.detalle = previo.detalle;
$$;

-- El mismo cuerpo que en 20261120000006, con dos cambios:
-- 1. R02 forzado: si todos sus motivos están forzados, se sigue con el cliente que confirmó ADV.
-- 2. Los motivos de R05–R14 forzados no cuentan para decidir la salida.
create or replace function intake.evaluar_caso(p_caso bigint) returns jsonb
language plpgsql security definer set search_path = '' as $$
declare
  v_caso intake.casos%rowtype;
  v_cliente text;
  v_fecha date;
  v_salida text;
  v_pedido bigint;
  v_motivos jsonb;
  v_forzados jsonb;
  v_marca bigint;
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
  -- Los forzados se conservan: son decisiones de ADV.
  update intake.motivos set estado = 'resuelto', actor = 'evaluar_caso'
  where caso = p_caso and estado = 'abierto';

  -- Los motivos con id mayor que la marca son los de esta evaluación.
  select coalesce(max(id), 0) into v_marca from intake.motivos where caso = p_caso;

  -- R01–R04 cortan el flujo. Por ahora, solo R02.
  insert into intake.motivos (caso, linea, codigo, salida, detalle)
  select p_caso, r.linea, r.codigo, r.salida, r.detalle from intake.r02_remitente(p_caso) r;
  perform intake.aplicar_forzados(p_caso);

  if exists (select 1 from intake.motivos where caso = p_caso and id > v_marca and estado = 'abierto' and codigo = 'R02') then
    v_salida := 'revision';
  else
    if exists (select 1 from intake.motivos where caso = p_caso and id > v_marca and estado = 'forzado' and codigo = 'R02') then
      -- R02 forzado: el cliente es el que confirmó ADV al forzarlo.
      v_cliente := v_caso.cliente;
    else
      select ct.cliente into v_cliente
      from intake.correos c join erp.contactos ct on ct.email = lower(btrim(c.remitente))
      where c.caso = p_caso and c.direccion = 'entrada'
      order by c.id limit 1;
      update intake.casos set cliente = v_cliente where id = p_caso;
    end if;

    update intake.lineas_caso l
    set producto = r.producto,
        precio_referencia = intake.precio_referencia(v_cliente, r.producto, v_fecha)
    from (select l2.id, intake.resolver_producto(v_cliente, l2.referencia) as producto
          from intake.lineas_caso l2 where l2.caso = p_caso) r
    where l.id = r.id;

    -- R05–R14 se evalúan todas y acumulan motivos. Por ahora, R08, R11 y R12.
    insert into intake.motivos (caso, linea, codigo, salida, detalle)
    select p_caso, r.linea, r.codigo, r.salida, r.detalle from intake.r08_referencias(p_caso, v_cliente) r
    union all
    select p_caso, r.linea, r.codigo, r.salida, r.detalle from intake.r11_precios(p_caso, v_cliente, v_fecha) r
    union all
    select p_caso, r.linea, r.codigo, r.salida, r.detalle from intake.r12_extractores(p_caso) r;
    perform intake.aplicar_forzados(p_caso);

    -- Algún motivo de revisión → revisión; si solo faltan datos → pedir datos; ninguno → automático.
    -- Los forzados no cuentan.
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

  select jsonb_agg(distinct jsonb_build_object('codigo', m.codigo, 'linea', m.linea))
    into v_forzados
  from intake.motivos m where m.caso = p_caso and m.estado = 'forzado';

  -- El evento solo lleva códigos e identificadores, sin datos personales (04, sección 5.4).
  insert into intake.eventos (caso, tipo, actor, carga)
  values (p_caso, 'reglas_evaluadas', 'evaluar_caso',
          jsonb_build_object('salida', v_salida, 'motivos', coalesce(v_motivos, '[]'::jsonb),
                             'forzados', coalesce(v_forzados, '[]'::jsonb),
                             'pedido', v_pedido, 'hora_referencia', v_caso.hora_recepcion));

  return jsonb_build_object('caso', p_caso, 'salida', v_salida, 'pedido', v_pedido,
                            'motivos', coalesce(v_motivos, '[]'::jsonb));
end;
$$;

-- ============================================================
-- Funciones de la app (todas exigen el rol de ADV)
-- ============================================================

-- La cola: casos en revisión, con la prioridad calculada al consultar, nunca guardada (D21, 04 sección 2.2):
-- 1, reclamaciones; 2, los que todavía llegan al corte de las 13:00 de hoy; 3, el resto. Dentro, por antigüedad.
create function adv.cola() returns jsonb
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
        'remitente', co.remitente,
        'asunto', co.asunto,
        'configuracion', c.configuracion,
        'motivos', (select coalesce(jsonb_agg(distinct m.codigo), '[]')
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

-- Qué se puede hacer con cada motivo en la versión mínima de la app.
create function intake.accion_motivo(p_codigo text, p_detalle jsonb) returns text
language sql immutable set search_path = '' as $$
  select case
    when p_codigo in ('R04', 'R09', 'R11', 'R13') then 'bloqueado_otro_dueno'   -- 04, sección 2.4
    when p_codigo = 'R02' and p_detalle ->> 'tipo' = 'remitente_no_verificado' then 'forzar_con_telefono'
    when p_codigo in ('R02', 'R12') then 'forzar'
    when p_codigo = 'R08' then 'corregir_linea'                                -- fuera de la versión mínima
    when p_codigo like 'M%' then 'solo_cerrar'                                 -- sin líneas que convertir
    else 'forzar'
  end;
$$;

create function adv.detalle_caso(p_caso bigint) returns jsonb
language plpgsql stable security definer set search_path = '' as $$
begin
  perform intake.exigir_adv();
  return (
    select jsonb_build_object(
      'caso', c.id, 'estado', c.estado, 'tipo', c.tipo, 'configuracion', c.configuracion,
      'recibido', c.hora_recepcion, 'cliente', c.cliente, 'razon_social', cl.razon_social,
      'correo', (select jsonb_build_object('remitente', remitente, 'asunto', asunto, 'autenticacion', autenticacion)
                 from intake.correos where caso = c.id and direccion = 'entrada' order by id limit 1),
      'lineas', (select coalesce(jsonb_agg(jsonb_build_object(
                    'linea', l.linea, 'texto', l.texto_original, 'referencia', l.referencia,
                    'cantidad', l.cantidad, 'unidad', l.unidad, 'precio', l.precio,
                    'producto', l.producto, 'precio_referencia', l.precio_referencia, 'fuente', l.fuente,
                    'referencia_determinista', l.referencia_determinista,
                    'cantidad_determinista', l.cantidad_determinista) order by l.linea), '[]')
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

-- Crear el pedido desde la revisión: fuerza los motivos indicados, con su razón, y vuelve a pasar todas las
-- reglas (CA-25). O se crea el pedido, o no cambia nada: si queda algún motivo, se deshace todo.
-- p_forzados: [{"codigo", "linea", "razon": verificado_telefono|cliente_confirmado|lectura_comprobada|otra,
--               "texto": opcional}]
-- p_cliente: obligatorio si se fuerza R02 (hay que decir de quién es el pedido).
create function adv.crear_pedido(p_caso bigint, p_forzados jsonb, p_cliente text default null) returns jsonb
language plpgsql security definer set search_path = '' as $$
declare
  v_actor text := intake.exigir_adv();
  v_estado text;
  v_forzado jsonb;
  v_motivo intake.motivos%rowtype;
  v_accion text;
  v_razon text;
  v_resultado jsonb;
begin
  select estado into v_estado from intake.casos where id = p_caso for update;
  if not found then
    raise exception 'El caso % no existe', p_caso;
  end if;
  if v_estado <> 'en_revision' then
    raise exception 'El caso % no está en revisión (%)', p_caso, v_estado;
  end if;

  for v_forzado in select value from jsonb_array_elements(coalesce(p_forzados, '[]')) loop
    select * into v_motivo from intake.motivos
    where caso = p_caso and estado = 'abierto' and codigo = v_forzado ->> 'codigo'
      and linea is not distinct from (v_forzado ->> 'linea')::int
    order by id desc limit 1;
    if not found then
      raise exception 'El caso % no tiene abierto el motivo % (línea %)', p_caso,
        v_forzado ->> 'codigo', coalesce(v_forzado ->> 'linea', '-');
    end if;

    v_razon := v_forzado ->> 'razon';
    if v_razon is null or v_razon not in ('verificado_telefono', 'cliente_confirmado', 'lectura_comprobada', 'otra') then
      raise exception 'Razón de forzado no válida: %', coalesce(v_razon, 'ninguna');
    end if;

    v_accion := intake.accion_motivo(v_motivo.codigo, v_motivo.detalle);
    if v_accion = 'bloqueado_otro_dueno' then
      raise exception '% no se puede forzar: lo resuelve su dueño (04, sección 2.4)', v_motivo.codigo;
    elsif v_accion in ('corregir_linea', 'solo_cerrar') then
      raise exception '% no se puede forzar en esta versión (%)', v_motivo.codigo, v_accion;
    elsif v_accion = 'forzar_con_telefono' and v_razon <> 'verificado_telefono' then
      raise exception 'Forzar un remitente no verificado exige verificarlo por teléfono con el cliente';
    end if;

    if v_motivo.codigo = 'R02' then
      if p_cliente is null or not exists (select 1 from erp.clientes where codigo = p_cliente) then
        raise exception 'Para forzar R02 hay que confirmar un cliente que exista';
      end if;
      update intake.casos set cliente = p_cliente where id = p_caso;
    end if;

    update intake.motivos
    set estado = 'forzado', actor = v_actor,
        razon_forzado = v_razon || coalesce(': ' || nullif(btrim(v_forzado ->> 'texto'), ''), '')
    where id = v_motivo.id;

    -- El evento lleva el código de la razón, no el texto libre (04, sección 8).
    insert into intake.eventos (caso, tipo, actor, carga)
    values (p_caso, 'motivo_forzado', v_actor,
            jsonb_build_object('codigo', v_motivo.codigo, 'linea', v_motivo.linea, 'razon', v_razon));
  end loop;

  v_resultado := intake.evaluar_caso(p_caso);
  if v_resultado ->> 'salida' <> 'automatico' then
    raise exception 'No se puede crear el pedido: quedan motivos sin resolver: %', v_resultado -> 'motivos';
  end if;

  update erp.pedidos set origen = 'revision' where id = (v_resultado ->> 'pedido')::bigint;
  insert into intake.eventos (caso, tipo, actor, carga)
  values (p_caso, 'pedido_creado_en_revision', v_actor, jsonb_build_object('pedido', v_resultado -> 'pedido'));
  return v_resultado;
end;
$$;

-- Cerrar sin crear pedido: descartado, o procesado a mano (por ejemplo, un PDF que ADV ha tecleado en el ERP).
create function adv.cerrar_caso(p_caso bigint, p_resultado text, p_texto text default null) returns jsonb
language plpgsql security definer set search_path = '' as $$
declare
  v_actor text := intake.exigir_adv();
  v_estado text;
begin
  if p_resultado is null or p_resultado not in ('descartado', 'procesado a mano') then
    raise exception 'Resultado de cierre no válido: %', coalesce(p_resultado, 'ninguno');
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

-- Reevaluar: las mismas reglas, con los datos maestros como están ahora (por ejemplo, tras un desbloqueo).
create function adv.reevaluar(p_caso bigint) returns jsonb
language plpgsql security definer set search_path = '' as $$
declare
  v_actor text := intake.exigir_adv();
  v_resultado jsonb;
begin
  v_resultado := intake.evaluar_caso(p_caso);
  insert into intake.eventos (caso, tipo, actor, carga)
  values (p_caso, 'reevaluado', v_actor, jsonb_build_object('salida', v_resultado -> 'salida'));
  return v_resultado;
end;
$$;

-- ============================================================
-- Permisos
-- ============================================================

revoke execute on function intake.rol_adv(), intake.exigir_adv(), intake.aplicar_forzados(bigint),
                           intake.accion_motivo(text, jsonb)
  from public, anon, authenticated, service_role;

revoke execute on all functions in schema adv from public, anon, service_role;
grant execute on all functions in schema adv to authenticated;
