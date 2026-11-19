-- Extracción completa, paso 1: prompt y esquema versionados (ADR 0002) y validación con pg_jsonschema
-- como segunda capa (04, sección 6.4).

create extension if not exists pg_jsonschema with schema extensions;

-- Cada versión es el contenido de extraction/<prompt>/ en un momento dado. La carga un script desde el
-- repositorio; nunca se edita a mano. Una sola versión activa por prompt.
create table intake.prompt_versiones (
  id         bigint generated always as identity primary key,
  prompt     text not null,
  version    integer not null,
  hash       text not null unique check (hash ~ '^[0-9a-f]{64}$'),
  texto      text not null,
  esquema    jsonb not null,
  ejemplos   jsonb not null default '[]',
  modelo     text not null,
  activa     boolean not null default false,
  creada_en  timestamptz not null default now(),
  unique (prompt, version)
);
create unique index prompt_versiones_una_activa on intake.prompt_versiones (prompt) where activa;
alter table intake.prompt_versiones enable row level security;

-- La versión de cada extracción apunta a su fila de prompt_versiones. Las del corte vertical, con el
-- prompt provisional dentro del nodo, se quedan sin versión.
alter table intake.extracciones
  add column prompt_version_id bigint references intake.prompt_versiones (id);

-- ============================================================
-- Lógica en intake
-- ============================================================

create function intake.prompt_activo(p_prompt text) returns jsonb
language sql stable security definer set search_path = '' as $$
  select jsonb_build_object('version', v.version, 'hash', v.hash, 'texto', v.texto,
                            'esquema', v.esquema, 'ejemplos', v.ejemplos, 'modelo', v.modelo)
  from intake.prompt_versiones v
  where v.prompt = p_prompt and v.activa;
$$;

-- registrar_extraccion cambia: recibe el hash de la versión del prompt, no un texto libre, y valida el
-- JSON contra el esquema de esa versión.
drop function api.registrar_extraccion(bigint, jsonb, text, text, text, integer, integer);
drop function intake.registrar_extraccion(bigint, jsonb, text, text, text, integer, integer);

create function intake.registrar_extraccion(
  p_caso bigint, p_extraccion jsonb, p_prompt_hash text, p_modelo text,
  p_configuracion text, p_tokens_entrada integer default null, p_tokens_salida integer default null)
returns jsonb
language plpgsql security definer set search_path = '' as $$
declare
  v_version intake.prompt_versiones%rowtype;
begin
  select * into v_version from intake.prompt_versiones where hash = p_prompt_hash;
  if not found then
    raise exception 'No existe ninguna versión de prompt con el hash %', p_prompt_hash;
  end if;

  -- Segunda capa: el mismo esquema que recibió la IA, comprobado en la base de datos.
  if not extensions.jsonb_matches_schema(v_version.esquema::json, p_extraccion) then
    raise exception 'Extracción no válida para el caso %: no cumple el esquema de la versión %',
      p_caso, v_version.version;
  end if;

  insert into intake.extracciones (caso, prompt, version, prompt_version_id, modelo, configuracion,
                                   resultado, valido, tokens_entrada, tokens_salida)
  values (p_caso, v_version.prompt, v_version.version::text, v_version.id, p_modelo, p_configuracion,
          p_extraccion, true, p_tokens_entrada, p_tokens_salida);

  insert into intake.lineas_caso (caso, linea, texto_original, referencia, cantidad, unidad, precio, fuente)
  select p_caso, l.n, l.v ->> 'texto', l.v ->> 'referencia', (l.v ->> 'cantidad')::numeric,
         l.v ->> 'unidad', (l.v ->> 'precio')::numeric, 'ia'
  from jsonb_array_elements(p_extraccion -> 'lineas') with ordinality as l (v, n);

  update intake.casos set tipo = 'pedido_nuevo', estado = 'clasificado' where id = p_caso;

  insert into intake.eventos (caso, tipo, actor, carga)
  values (p_caso, 'extraido', 'automatizacion',
          jsonb_build_object('prompt', v_version.prompt, 'version', v_version.version, 'modelo', p_modelo,
                             'configuracion', p_configuracion,
                             'lineas', jsonb_array_length(p_extraccion -> 'lineas')));

  return intake.evaluar_caso(p_caso);
end;
$$;

revoke execute on function intake.prompt_activo(text),
                           intake.registrar_extraccion(bigint, jsonb, text, text, text, integer, integer)
  from public, anon, authenticated, service_role;

-- ============================================================
-- La puerta: api
-- ============================================================

create function api.prompt_activo(prompt text) returns jsonb
language sql stable security definer set search_path = '' as $$
  select intake.prompt_activo(prompt);
$$;

create function api.registrar_extraccion(
  caso bigint, extraccion jsonb, prompt_hash text, modelo text, configuracion text,
  tokens_entrada integer default null, tokens_salida integer default null)
returns jsonb
language sql security definer set search_path = '' as $$
  select intake.registrar_extraccion(caso, extraccion, prompt_hash, modelo, configuracion,
                                     tokens_entrada, tokens_salida);
$$;

revoke execute on all functions in schema api from public, anon, authenticated;
grant execute on all functions in schema api to service_role;
