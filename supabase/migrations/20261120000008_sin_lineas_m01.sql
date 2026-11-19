-- Prompt v2: la IA puede devolver 0 líneas (antes, minItems: 1 la obligaba a inventarse una).
-- Un caso sin líneas va a revisión con M01 en las tres configuraciones, no solo en "solo reglas".
-- M01 y no "pedir datos" (D22) mientras no haya clasificación: sin ella, 0 líneas puede ser un pedido
-- incompleto o un correo que no es un pedido. Declarado en 04, sección 6.3, y en eval/registro-de-cambios.md.
--
-- Mismo cuerpo que en 20261120000006 salvo el paso 4. Misma firma: no cambia nada en n8n ni en la API.

create or replace function intake.registrar_extraccion(
  p_caso bigint,
  p_configuracion text,
  p_extraccion_ia jsonb default null,
  p_prompt_hash text default null,
  p_modelo text default null,
  p_tokens_entrada integer default null,
  p_tokens_salida integer default null,
  p_extraccion_determinista jsonb default null,
  p_version_determinista text default null)
returns jsonb
language plpgsql security definer set search_path = '' as $$
declare
  v_usa_ia boolean := p_configuracion in ('solo_ia', 'hibrido');
  v_usa_det boolean := p_configuracion in ('solo_reglas', 'hibrido');
  v_version intake.prompt_versiones%rowtype;
  v_ia jsonb;
  v_det jsonb;
  v_libres jsonb := '[]';   -- líneas del determinista todavía sin pareja
  v_n integer := 0;
  v_i integer;
  v_pareja integer;
  v_lineas_ia integer;
  v_lineas_det integer;
begin
  -- 1. Cada interruptor exige su extracción, y nada más.
  if p_configuracion is null or p_configuracion not in ('solo_reglas', 'solo_ia', 'hibrido') then
    raise exception 'Configuración desconocida: %', p_configuracion;
  end if;
  if v_usa_ia <> (p_extraccion_ia is not null) then
    raise exception 'La configuración % % extracción de la IA', p_configuracion,
      case when v_usa_ia then 'necesita' else 'no admite' end;
  end if;
  if v_usa_det <> (p_extraccion_determinista is not null) then
    raise exception 'La configuración % % extracción del determinista', p_configuracion,
      case when v_usa_det then 'necesita' else 'no admite' end;
  end if;

  -- 2. Validación de cada extracción, con su esquema.
  if v_usa_ia then
    select * into v_version from intake.prompt_versiones where hash = p_prompt_hash;
    if not found then
      raise exception 'No existe ninguna versión de prompt con el hash %', p_prompt_hash;
    end if;
    if not extensions.jsonb_matches_schema(v_version.esquema::json, p_extraccion_ia) then
      raise exception 'Extracción no válida para el caso %: no cumple el esquema de la versión %',
        p_caso, v_version.version;
    end if;
  end if;
  if v_usa_det then
    if p_version_determinista is null then
      raise exception 'Falta la versión del extractor determinista';
    end if;
    if not extensions.jsonb_matches_schema(intake.esquema_determinista(), p_extraccion_determinista) then
      raise exception 'Extracción del determinista no válida para el caso %', p_caso;
    end if;
  end if;

  update intake.casos set configuracion = p_configuracion where id = p_caso;

  -- 3. Cada extracción se guarda tal como llegó (análisis de errores, D25).
  if v_usa_ia then
    insert into intake.extracciones (caso, prompt, version, prompt_version_id, modelo, configuracion,
                                     resultado, valido, tokens_entrada, tokens_salida)
    values (p_caso, v_version.prompt, v_version.version::text, v_version.id, p_modelo, p_configuracion,
            p_extraccion_ia, true, p_tokens_entrada, p_tokens_salida);
  end if;
  if v_usa_det then
    insert into intake.extracciones (caso, prompt, version, configuracion, resultado, valido)
    values (p_caso, 'determinista', p_version_determinista, p_configuracion, p_extraccion_determinista, true);
  end if;

  -- 4. Sin ninguna línea, en cualquier configuración: revisión con M01 (ver la cabecera). En el híbrido,
  -- si la IA no lee nada pero el determinista sí, no es este caso: son omisiones de la IA (R12).
  v_lineas_ia := coalesce(jsonb_array_length(p_extraccion_ia -> 'lineas'), 0);
  v_lineas_det := coalesce(jsonb_array_length(p_extraccion_determinista -> 'lineas'), 0);
  if (p_configuracion = 'solo_reglas' and v_lineas_det = 0)
     or (p_configuracion = 'solo_ia' and v_lineas_ia = 0)
     or (p_configuracion = 'hibrido' and v_lineas_ia = 0 and v_lineas_det = 0) then
    insert into intake.eventos (caso, tipo, actor, carga)
    values (p_caso, 'extraido', 'automatizacion',
            jsonb_build_object('configuracion', p_configuracion, 'prompt', v_version.prompt,
                               'version', v_version.version, 'modelo', p_modelo,
                               'version_determinista', p_version_determinista, 'lineas', 0));
    return intake.enviar_a_revision(p_caso, 'M01',
                                    jsonb_build_object('tipo', 'sin_lineas', 'configuracion', p_configuracion));
  end if;

  -- 5. Las líneas del pedido según la configuración.
  if p_configuracion = 'solo_reglas' then
    insert into intake.lineas_caso (caso, linea, texto_original, referencia, cantidad, unidad, precio, fuente,
                                    referencia_determinista, cantidad_determinista)
    select p_caso, l.n, l.v ->> 'texto', l.v ->> 'referencia', (l.v ->> 'cantidad')::numeric, l.v ->> 'unidad',
           (l.v ->> 'precio')::numeric, 'determinista', l.v ->> 'referencia', (l.v ->> 'cantidad')::numeric
    from jsonb_array_elements(p_extraccion_determinista -> 'lineas') with ordinality as l (v, n);

  elsif p_configuracion = 'solo_ia' then
    insert into intake.lineas_caso (caso, linea, texto_original, referencia, cantidad, unidad, precio, fuente)
    select p_caso, l.n, l.v ->> 'texto', l.v ->> 'referencia', (l.v ->> 'cantidad')::numeric, l.v ->> 'unidad',
           (l.v ->> 'precio')::numeric, 'ia'
    from jsonb_array_elements(p_extraccion_ia -> 'lineas') with ordinality as l (v, n);

  else
    -- Híbrido: las líneas de la IA son la base. Cada una se empareja con la primera línea libre del
    -- determinista con la misma referencia; si no hay, con la que tenga el mismo texto (los dos leyeron la
    -- misma línea y no coinciden en la referencia). Las del determinista que quedan sin pareja son
    -- omisiones de la IA y se añaden al pedido, para que ADV las vea.
    v_libres := p_extraccion_determinista -> 'lineas';
    for v_ia in select value from jsonb_array_elements(p_extraccion_ia -> 'lineas') loop
      v_n := v_n + 1;
      v_pareja := null;
      for v_i in 0 .. jsonb_array_length(v_libres) - 1 loop
        if intake.normalizar_referencia(v_libres -> v_i ->> 'referencia')
           = intake.normalizar_referencia(v_ia ->> 'referencia') then
          v_pareja := v_i; exit;
        end if;
      end loop;
      if v_pareja is null then
        for v_i in 0 .. jsonb_array_length(v_libres) - 1 loop
          if btrim(v_libres -> v_i ->> 'texto') = btrim(v_ia ->> 'texto') then
            v_pareja := v_i; exit;
          end if;
        end loop;
      end if;
      v_det := case when v_pareja is null then null else v_libres -> v_pareja end;
      if v_pareja is not null then
        v_libres := v_libres - v_pareja;
      end if;
      insert into intake.lineas_caso (caso, linea, texto_original, referencia, cantidad, unidad, precio, fuente,
                                      referencia_determinista, cantidad_determinista)
      values (p_caso, v_n, v_ia ->> 'texto', v_ia ->> 'referencia', (v_ia ->> 'cantidad')::numeric,
              v_ia ->> 'unidad', (v_ia ->> 'precio')::numeric,
              case when v_det is null then 'ia' else 'ambas' end,
              v_det ->> 'referencia', (v_det ->> 'cantidad')::numeric);
    end loop;
    for v_det in select value from jsonb_array_elements(v_libres) loop
      v_n := v_n + 1;
      insert into intake.lineas_caso (caso, linea, texto_original, referencia, cantidad, unidad, precio, fuente,
                                      referencia_determinista, cantidad_determinista)
      values (p_caso, v_n, v_det ->> 'texto', v_det ->> 'referencia', (v_det ->> 'cantidad')::numeric,
              v_det ->> 'unidad', null, 'determinista', v_det ->> 'referencia', (v_det ->> 'cantidad')::numeric);
    end loop;
  end if;

  update intake.casos set tipo = 'pedido_nuevo', estado = 'clasificado' where id = p_caso;

  insert into intake.eventos (caso, tipo, actor, carga)
  values (p_caso, 'extraido', 'automatizacion',
          jsonb_build_object('configuracion', p_configuracion,
                             'prompt', v_version.prompt, 'version', v_version.version, 'modelo', p_modelo,
                             'version_determinista', p_version_determinista,
                             'lineas', (select count(*) from intake.lineas_caso where caso = p_caso)));

  return intake.evaluar_caso(p_caso);
end;
$$;
