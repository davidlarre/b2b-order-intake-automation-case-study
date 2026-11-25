-- Clasificación del correo (04, secciones 2.2 paso 3 y 6.1) y R01 (sección 3.1).
-- n8n clasifica con Gemini y llama a api.registrar_clasificacion, que guarda el resultado y encamina el caso:
--   pedido_nuevo → sigue (extracción y reglas); consulta, reclamación y modificación o anulación → R01;
--   otros → derivado (factura a contabilidad, spam archivado); dudoso → M01.
-- Vuelta atrás: drop de las funciones nuevas y volver a crear intake.evaluar_caso (20261120000009),
-- intake.accion_motivo (20261120000009) y adv.cerrar_caso (20261120000011).

-- ============================================================
-- R01: es un pedido nuevo
-- ============================================================

-- Sin tipo (solo reglas, que no clasifica), R01 no se aplica: lo cubre M01 cuando no hay líneas.
create function intake.r01_tipo(p_caso bigint)
returns table (linea integer, codigo text, salida text, detalle jsonb)
language sql stable set search_path = '' as $$
  select null::integer, 'R01', 'revision', jsonb_build_object('tipo', c.tipo)
  from intake.casos c
  where c.id = p_caso and c.tipo in ('consulta', 'reclamacion', 'modificacion_anulacion');
$$;

-- El mismo cuerpo que en 20261120000009, con R01 delante de R02: las dos cortan el flujo.
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

  -- R01–R04 cortan el flujo. Por ahora, R01 y R02.
  insert into intake.motivos (caso, linea, codigo, salida, detalle)
  select p_caso, r.linea, r.codigo, r.salida, r.detalle from intake.r01_tipo(p_caso) r;
  if not found then
    insert into intake.motivos (caso, linea, codigo, salida, detalle)
    select p_caso, r.linea, r.codigo, r.salida, r.detalle from intake.r02_remitente(p_caso) r;
    perform intake.aplicar_forzados(p_caso);
  end if;

  if exists (select 1 from intake.motivos where caso = p_caso and id > v_marca and estado = 'abierto'
             and codigo in ('R01', 'R02')) then
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
-- Registrar la clasificación
-- ============================================================

create function intake.registrar_clasificacion(
  p_caso bigint, p_configuracion text, p_clasificacion jsonb, p_prompt_hash text, p_modelo text,
  p_tokens_entrada integer default null, p_tokens_salida integer default null)
returns jsonb
language plpgsql security definer set search_path = '' as $$
declare
  v_version intake.prompt_versiones%rowtype;
  v_estado text;
  v_tipo text := p_clasificacion ->> 'tipo';
  v_destino text := p_clasificacion ->> 'destino';
  v_resultado jsonb;
begin
  if p_configuracion is null or p_configuracion not in ('solo_ia', 'hibrido') then
    raise exception 'La clasificación con IA no se usa en la configuración %', coalesce(p_configuracion, 'ninguna');
  end if;
  select * into v_version from intake.prompt_versiones where hash = p_prompt_hash and prompt = 'clasificacion';
  if not found then
    raise exception 'No existe ninguna versión del prompt de clasificación con el hash %', p_prompt_hash;
  end if;
  if not extensions.jsonb_matches_schema(v_version.esquema::json, p_clasificacion) then
    raise exception 'Clasificación no válida para el caso %: no cumple el esquema de la versión %',
      p_caso, v_version.version;
  end if;

  select estado into v_estado from intake.casos where id = p_caso for update;
  if not found then
    raise exception 'El caso % no existe', p_caso;
  end if;
  if v_estado <> 'recibido' then
    raise exception 'El caso % ya se ha clasificado (%)', p_caso, v_estado;
  end if;

  insert into intake.extracciones (caso, prompt, version, prompt_version_id, modelo, configuracion,
                                   resultado, valido, tokens_entrada, tokens_salida)
  values (p_caso, v_version.prompt, v_version.version::text, v_version.id, p_modelo, p_configuracion,
          p_clasificacion, true, p_tokens_entrada, p_tokens_salida);

  -- Dudoso no es un tipo del caso: el caso se queda sin tipo hasta que lo decida una persona.
  update intake.casos
  set estado = 'clasificado', configuracion = p_configuracion, tipo = nullif(v_tipo, 'dudoso')
  where id = p_caso;

  insert into intake.eventos (caso, tipo, actor, carga)
  values (p_caso, 'clasificado', 'automatizacion',
          jsonb_build_object('tipo', v_tipo, 'destino', v_destino, 'version', v_version.version, 'modelo', p_modelo));

  if v_tipo = 'pedido_nuevo' then
    return jsonb_build_object('caso', p_caso, 'tipo', v_tipo, 'sigue', true);
  elsif v_tipo = 'otros' and v_destino in ('contabilidad', 'archivo') then
    -- El reenvío a contabilidad sale con los envíos (04, sección 2.7), que todavía no existen: queda en el registro.
    update intake.casos set estado = 'derivado' where id = p_caso;
    insert into intake.eventos (caso, tipo, actor, carga)
    values (p_caso, 'derivado', 'automatizacion', jsonb_build_object('destino', v_destino));
    v_resultado := jsonb_build_object('caso', p_caso, 'salida', 'derivado', 'pedido', null, 'motivos', '[]'::jsonb);
  elsif v_tipo in ('dudoso', 'otros') then
    -- "Otros" sin destino no se puede encaminar: lo decide una persona, nunca se archiva (D13).
    v_resultado := intake.enviar_a_revision(p_caso, 'M01', jsonb_build_object('tipo', 'clasificacion_dudosa'));
  else
    v_resultado := intake.evaluar_caso(p_caso);   -- R01
  end if;
  return v_resultado || jsonb_build_object('tipo', v_tipo, 'sigue', false);
end;
$$;

create function api.registrar_clasificacion(
  caso bigint, configuracion text, clasificacion jsonb, prompt_hash text, modelo text,
  tokens_entrada integer default null, tokens_salida integer default null)
returns jsonb
language sql security definer set search_path = '' as $$
  select intake.registrar_clasificacion(caso, configuracion, clasificacion, prompt_hash, modelo,
                                        tokens_entrada, tokens_salida);
$$;

-- ============================================================
-- App de revisión: qué se hace con R01, y los cierres de 04, sección 2.5
-- ============================================================

-- R01 se puede forzar según 04 (tratarlo como pedido), pero forzarlo exige extraer las líneas, y todavía no se
-- puede desde la revisión: sin líneas, se crearía un pedido vacío. Por ahora, solo se cierra.
create or replace function intake.accion_motivo(p_codigo text, p_detalle jsonb) returns text
language sql immutable set search_path = '' as $$
  select case
    when p_codigo in ('R04', 'R09', 'R11', 'R13') then 'bloqueado_otro_dueno'   -- 04, sección 2.4
    when p_codigo = 'R02' and p_detalle ->> 'tipo' = 'remitente_no_verificado' then 'forzar_con_telefono'
    when p_codigo in ('R02', 'R12') then 'forzar'
    when p_codigo = 'R08' then 'corregir_linea'                                -- fuera de la versión mínima
    when p_codigo = 'R01' or p_codigo like 'M%' then 'solo_cerrar'             -- sin líneas que convertir
    else 'forzar'
  end;
$$;

create or replace function adv.cerrar_caso(p_caso bigint, p_resultado text, p_texto text default null) returns jsonb
language plpgsql security definer set search_path = '' as $$
declare
  v_actor text := intake.exigir_adv();
  v_estado text;
  v_tipo text;
begin
  if p_resultado is null or p_resultado not in ('descartado', 'procesado a mano', 'consulta atendida',
      'reclamación atendida', 'modificación aplicada', 'anulación aplicada') then
    raise exception 'Resultado de cierre no válido: %', coalesce(p_resultado, 'ninguno');
  end if;
  if p_resultado = 'descartado' and nullif(btrim(coalesce(p_texto, '')), '') is null then
    raise exception 'Para descartar un pedido hay que indicar por qué';
  end if;
  select estado, tipo into v_estado, v_tipo from intake.casos where id = p_caso for update;
  if not found then
    raise exception 'El caso % no existe', p_caso;
  end if;
  if v_estado in ('pedido_creado', 'derivado', 'cerrado') then
    raise exception 'El caso % ya está en un estado final (%)', p_caso, v_estado;
  end if;
  if (p_resultado = 'consulta atendida' and v_tipo is distinct from 'consulta')
     or (p_resultado = 'reclamación atendida' and v_tipo is distinct from 'reclamacion')
     or (p_resultado in ('modificación aplicada', 'anulación aplicada')
         and v_tipo is distinct from 'modificacion_anulacion') then
    raise exception 'El resultado «%» no corresponde al tipo del caso (%)', p_resultado, coalesce(v_tipo, 'sin tipo');
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
-- Permisos
-- ============================================================

revoke execute on function intake.r01_tipo(bigint),
                           intake.registrar_clasificacion(bigint, text, jsonb, text, text, integer, integer)
  from public, anon, authenticated, service_role;
revoke execute on function api.registrar_clasificacion(bigint, text, jsonb, text, text, integer, integer)
  from public, anon, authenticated;
grant execute on function api.registrar_clasificacion(bigint, text, jsonb, text, text, integer, integer)
  to service_role;
