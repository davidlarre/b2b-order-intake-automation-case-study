-- Corte vertical, paso 3 (preparación): esquema api, la única puerta de la automatización.
-- Buena práctica: la API expone lo mínimo. Las funciones de api son envoltorios de una línea; la lógica
-- vive en intake, que no se expone. Todas las funciones de api tienen permiso para service_role.

create schema api;
revoke all on schema api from public, anon, authenticated;
grant usage on schema api to service_role;
alter default privileges in schema api revoke execute on functions from public;

-- La automatización ya no entra directamente a intake: solo por api.
revoke execute on function intake.evaluar_caso(bigint) from service_role;
revoke usage on schema intake from service_role;

-- ============================================================
-- Lógica en intake
-- ============================================================

-- Paso 1 del flujo (04, sección 2.2): guardar el correo y crear el caso en `recibido`.
-- Si el Message-ID ya existe, no crea nada y devuelve el caso existente (CA-18).
create function intake.recibir_correo(
  p_message_id text, p_remitente text, p_asunto text, p_autenticacion text,
  p_hora_recepcion timestamptz, p_origen text, p_hilo text default null, p_ruta_eml text default null)
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

  insert into intake.correos (caso, direccion, message_id, hilo, remitente, asunto, autenticacion, ruta_eml)
  values (v_caso, 'entrada', p_message_id, p_hilo, p_remitente, p_asunto, p_autenticacion, p_ruta_eml);

  insert into intake.eventos (caso, tipo, actor, carga)
  values (v_caso, 'recibido', 'automatizacion', jsonb_build_object('origen', p_origen));

  return jsonb_build_object('caso', v_caso, 'duplicado', false);
end;
$$;

-- Pasos 4 y 5: guardar la extracción y sus líneas, y evaluar las reglas. Una sola transacción.
create function intake.registrar_extraccion(
  p_caso bigint, p_extraccion jsonb, p_prompt_version text, p_modelo text,
  p_configuracion text, p_tokens_entrada integer default null, p_tokens_salida integer default null)
returns jsonb
language plpgsql security definer set search_path = '' as $$
begin
  -- Comprobación mínima de la forma. La validación completa con pg_jsonschema llega con el esquema de
  -- extraction/ (04, sección 6.4).
  if jsonb_typeof(p_extraccion -> 'lineas') is distinct from 'array'
     or jsonb_array_length(p_extraccion -> 'lineas') = 0
     or exists (select 1 from jsonb_array_elements(p_extraccion -> 'lineas') l
                where l ->> 'referencia' is null or jsonb_typeof(l -> 'cantidad') is distinct from 'number') then
    raise exception 'Extracción no válida para el caso %', p_caso;
  end if;

  insert into intake.extracciones (caso, prompt, version, modelo, configuracion, resultado, valido,
                                   tokens_entrada, tokens_salida)
  values (p_caso, 'extraccion', p_prompt_version, p_modelo, p_configuracion, p_extraccion, true,
          p_tokens_entrada, p_tokens_salida);

  insert into intake.lineas_caso (caso, linea, texto_original, referencia, cantidad, unidad, precio, fuente)
  select p_caso, l.n, l.v ->> 'texto', l.v ->> 'referencia', (l.v ->> 'cantidad')::numeric,
         l.v ->> 'unidad', (l.v ->> 'precio')::numeric, 'ia'
  from jsonb_array_elements(p_extraccion -> 'lineas') with ordinality as l (v, n);

  update intake.casos set tipo = 'pedido_nuevo', estado = 'clasificado' where id = p_caso;

  insert into intake.eventos (caso, tipo, actor, carga)
  values (p_caso, 'extraido', 'automatizacion',
          jsonb_build_object('version', p_prompt_version, 'modelo', p_modelo, 'configuracion', p_configuracion,
                             'lineas', jsonb_array_length(p_extraccion -> 'lineas')));

  return intake.evaluar_caso(p_caso);
end;
$$;

revoke execute on function intake.recibir_correo(text, text, text, text, timestamptz, text, text, text),
                           intake.registrar_extraccion(bigint, jsonb, text, text, text, integer, integer)
  from public, anon, authenticated, service_role;

-- ============================================================
-- La puerta: api
-- ============================================================

create function api.recibir_correo(
  message_id text, remitente text, asunto text, autenticacion text,
  hora_recepcion timestamptz, origen text, hilo text default null, ruta_eml text default null)
returns jsonb
language sql security definer set search_path = '' as $$
  select intake.recibir_correo(message_id, remitente, asunto, autenticacion, hora_recepcion, origen, hilo, ruta_eml);
$$;

create function api.registrar_extraccion(
  caso bigint, extraccion jsonb, prompt_version text, modelo text, configuracion text,
  tokens_entrada integer default null, tokens_salida integer default null)
returns jsonb
language sql security definer set search_path = '' as $$
  select intake.registrar_extraccion(caso, extraccion, prompt_version, modelo, configuracion,
                                     tokens_entrada, tokens_salida);
$$;

revoke execute on all functions in schema api from public, anon, authenticated;
grant execute on all functions in schema api to service_role;
