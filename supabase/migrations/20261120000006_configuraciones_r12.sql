-- Extracción completa, paso 5a: las tres configuraciones (04, sección 6.3) y R12 (sección 3.2).
-- registrar_extraccion recibe la extracción de la IA, la del extractor determinista o las dos, según la
-- configuración; guarda cada una tal como llegó; junta las líneas, y R12 compara las dos lecturas.

-- La configuración con la que se procesó el caso: R12 solo compara en el híbrido.
alter table intake.casos
  add column configuracion text check (configuracion in ('solo_reglas', 'solo_ia', 'hibrido'));

-- Lo que leyó el extractor determinista en cada línea, para que R12 lo compare con lo que leyó la IA.
alter table intake.lineas_caso
  add column referencia_determinista text,
  add column cantidad_determinista numeric(12, 3);

-- La extracción del determinista no tiene versión de prompt: su versión es la del módulo.
-- (extracciones.prompt = 'determinista', version = la del paquete orvalle-extractor).

create function intake.normalizar_referencia(p text) returns text
language sql immutable set search_path = '' as $$
  select upper(regexp_replace(btrim(p), '\s+', ' ', 'g'));
$$;

-- ============================================================
-- R12: los dos extractores coinciden (solo en el híbrido)
-- ============================================================

-- discrepancia: los dos leen la línea y no coinciden en la cantidad o en la referencia.
-- omision_ia: el determinista lee una línea (código del catálogo y cantidad limpia) que la IA no leyó.
-- Las líneas que solo lee la IA (equivalencias, descripciones) no son motivo: el determinista no puede leerlas.
create function intake.r12_extractores(p_caso bigint)
returns table (linea integer, codigo text, salida text, detalle jsonb)
language sql stable set search_path = '' as $$
  select l.linea, 'R12', 'revision',
         case when l.fuente = 'determinista'
              then jsonb_build_object('tipo', 'omision_ia', 'referencia', l.referencia, 'cantidad', l.cantidad)
              else jsonb_build_object('tipo', 'discrepancia',
                                      'ia', jsonb_build_object('referencia', l.referencia, 'cantidad', l.cantidad),
                                      'determinista', jsonb_build_object('referencia', l.referencia_determinista,
                                                                         'cantidad', l.cantidad_determinista))
         end
  from intake.lineas_caso l
  join intake.casos c on c.id = l.caso
  where l.caso = p_caso
    and c.configuracion = 'hibrido'
    and (l.fuente = 'determinista'
         or (l.fuente = 'ambas'
             and (l.cantidad is distinct from l.cantidad_determinista
                  or intake.normalizar_referencia(l.referencia)
                     is distinct from intake.normalizar_referencia(l.referencia_determinista))));
$$;

-- ============================================================
-- Auxiliares
-- ============================================================

-- Forma mínima de la extracción del determinista: puede no tener líneas (en "solo reglas" eso es M01).
create function intake.esquema_determinista() returns json
language sql immutable set search_path = '' as $$
  select '{
    "type": "object",
    "required": ["lineas"],
    "properties": {
      "lineas": {
        "type": "array",
        "items": {
          "type": "object",
          "required": ["texto", "referencia", "cantidad", "unidad", "precio"],
          "properties": {
            "texto": {"type": "string"},
            "referencia": {"type": "string"},
            "cantidad": {"type": "integer"},
            "unidad": {"type": ["string", "null"]},
            "precio": {"type": ["number", "null"]}
          }
        }
      }
    }
  }'::json;
$$;

-- ============================================================
-- registrar_extraccion con configuración
-- ============================================================

drop function api.registrar_extraccion(bigint, jsonb, text, text, text, integer, integer);
drop function intake.registrar_extraccion(bigint, jsonb, text, text, text, integer, integer);

create function intake.registrar_extraccion(
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

  -- 4. "Solo reglas" sin ninguna línea: no hay clasificador, así que es una duda de clasificación (M01).
  if p_configuracion = 'solo_reglas' and jsonb_array_length(p_extraccion_determinista -> 'lineas') = 0 then
    insert into intake.eventos (caso, tipo, actor, carga)
    values (p_caso, 'extraido', 'automatizacion',
            jsonb_build_object('configuracion', p_configuracion, 'version_determinista', p_version_determinista,
                               'lineas', 0));
    return intake.enviar_a_revision(p_caso, 'M01', jsonb_build_object('tipo', 'sin_lineas_determinista'));
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

-- ============================================================
-- evaluar_caso: el mismo cuerpo, con R12 entre las reglas que acumulan motivos
-- ============================================================

create or replace function intake.evaluar_caso(p_caso bigint) returns jsonb
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

  -- R01–R04 cortan el flujo. Por ahora, solo R02.
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

    -- R05–R14 se evalúan todas y acumulan motivos. Por ahora, R08, R11 y R12.
    insert into intake.motivos (caso, linea, codigo, salida, detalle)
    select p_caso, r.linea, r.codigo, r.salida, r.detalle from intake.r08_referencias(p_caso, v_cliente) r
    union all
    select p_caso, r.linea, r.codigo, r.salida, r.detalle from intake.r11_precios(p_caso, v_cliente, v_fecha) r
    union all
    select p_caso, r.linea, r.codigo, r.salida, r.detalle from intake.r12_extractores(p_caso) r;

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
-- Permisos y puerta
-- ============================================================

revoke execute on function intake.r12_extractores(bigint), intake.normalizar_referencia(text),
                           intake.esquema_determinista(),
                           intake.registrar_extraccion(bigint, text, jsonb, text, text, integer, integer, jsonb, text)
  from public, anon, authenticated, service_role;

create function api.registrar_extraccion(
  caso bigint,
  configuracion text,
  extraccion_ia jsonb default null,
  prompt_hash text default null,
  modelo text default null,
  tokens_entrada integer default null,
  tokens_salida integer default null,
  extraccion_determinista jsonb default null,
  version_determinista text default null)
returns jsonb
language sql security definer set search_path = '' as $$
  select intake.registrar_extraccion(caso, configuracion, extraccion_ia, prompt_hash, modelo,
                                     tokens_entrada, tokens_salida, extraccion_determinista, version_determinista);
$$;

revoke execute on function api.registrar_extraccion(bigint, text, jsonb, text, text, integer, integer, jsonb, text)
  from public, anon, authenticated;
grant execute on function api.registrar_extraccion(bigint, text, jsonb, text, text, integer, integer, jsonb, text)
  to service_role;
