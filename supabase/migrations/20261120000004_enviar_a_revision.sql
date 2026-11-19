-- Extracción completa, paso 3b: motivos que n8n detecta antes de evaluar_caso (04, sección 3.1).
-- M01 clasificación dudosa, M02 formato no soportado, M03 fallo técnico: el caso va a revisión sin pasar
-- por las reglas. El resto de motivos los ponen las reglas (evaluar_caso) o el envío (M05).

create function intake.enviar_a_revision(p_caso bigint, p_codigo text, p_detalle jsonb default '{}')
returns jsonb
language plpgsql security definer set search_path = '' as $$
declare
  v_estado text;
begin
  if p_codigo not in ('M01', 'M02', 'M03') then
    raise exception 'enviar_a_revision solo admite M01, M02 y M03, no %', p_codigo;
  end if;

  select estado into v_estado from intake.casos where id = p_caso for update;
  if not found then
    raise exception 'El caso % no existe', p_caso;
  end if;
  if v_estado in ('pedido_creado', 'derivado', 'cerrado') then
    raise exception 'El caso % ya está en un estado final (%)', p_caso, v_estado;
  end if;

  insert into intake.motivos (caso, linea, codigo, salida, detalle)
  values (p_caso, null, p_codigo, 'revision', coalesce(p_detalle, '{}'));

  update intake.casos set estado = 'en_revision' where id = p_caso;

  -- El evento lleva solo el código: el detalle puede contener nombres de ficheros del cliente.
  insert into intake.eventos (caso, tipo, actor, carga)
  values (p_caso, 'enviado_a_revision', 'automatizacion', jsonb_build_object('codigo', p_codigo));

  -- La misma forma que devuelve evaluar_caso, para que n8n y el script la traten igual.
  return jsonb_build_object('caso', p_caso, 'salida', 'revision', 'pedido', null,
                            'motivos', jsonb_build_array(
                              jsonb_build_object('codigo', p_codigo, 'linea', null, 'salida', 'revision')));
end;
$$;

revoke execute on function intake.enviar_a_revision(bigint, text, jsonb)
  from public, anon, authenticated, service_role;

create function api.enviar_a_revision(caso bigint, codigo text, detalle jsonb default '{}')
returns jsonb
language sql security definer set search_path = '' as $$
  select intake.enviar_a_revision(caso, codigo, detalle);
$$;

revoke execute on function api.enviar_a_revision(bigint, text, jsonb) from public, anon, authenticated;
grant execute on function api.enviar_a_revision(bigint, text, jsonb) to service_role;
