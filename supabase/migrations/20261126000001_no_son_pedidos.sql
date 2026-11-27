-- Ningún correo "otros" desaparece: los derivados (factura a contabilidad, spam archivado) se ven en la app, en
-- una lista aparte, con el motivo de la clasificación, y ADV puede devolver cualquiera a revisión (D13).
-- Al pasar a revisión no se extraen las líneas (todavía no se puede desde la app): va con M01 y se teclea a mano
-- o se descarta, como un M01 de clasificación dudosa.
-- Vuelta atrás: drop function adv.no_son_pedidos(), adv.pasar_a_revision(bigint).

-- Los derivados, del más reciente al más antiguo. El motivo es lo que devolvió la clasificación (tipo y
-- destino), con el modelo y la versión del prompt: el clasificador no da una explicación en texto.
create function adv.no_son_pedidos() returns jsonb
language plpgsql stable security definer set search_path = '' as $$
begin
  perform intake.exigir_adv();
  return coalesce((
    select jsonb_agg(fila order by fila ->> 'recibido' desc, (fila ->> 'caso')::bigint desc)
    from (
      select jsonb_build_object(
        'caso', c.id,
        'recibido', c.hora_recepcion,
        'remitente', co.remitente,
        'remitente_nombre', co.remitente_nombre,
        'asunto', co.asunto,
        'adjuntos', co.adjuntos,
        'ruta_eml', co.ruta_eml,
        'clasificacion', jsonb_build_object('tipo', ex.resultado ->> 'tipo', 'destino', ex.resultado ->> 'destino',
                                            'modelo', ex.modelo, 'version', ex.version, 'fecha', ex.creada_en)
      ) as fila
      from intake.casos c
      left join lateral (select remitente, remitente_nombre, asunto, adjuntos, ruta_eml from intake.correos
                         where caso = c.id and direccion = 'entrada' order by id limit 1) co on true
      left join lateral (select resultado, modelo, version, creada_en from intake.extracciones
                         where caso = c.id and prompt = 'clasificacion' order by id desc limit 1) ex on true
      where c.estado = 'derivado'
    ) t
  ), '[]'::jsonb);
end;
$$;

-- "Es un pedido": el derivado vuelve a la cola de revisión, como pedido nuevo, con M01 y la clasificación que
-- se corrige. Solo desde derivado; el evento lleva solo códigos (04, sección 5.4).
create function adv.pasar_a_revision(p_caso bigint) returns jsonb
language plpgsql security definer set search_path = '' as $$
declare
  v_actor text := intake.exigir_adv();
  v_estado text;
  v_clasificacion jsonb;
begin
  select estado into v_estado from intake.casos where id = p_caso for update;
  if not found then
    raise exception 'El caso % no existe', p_caso;
  end if;
  if v_estado <> 'derivado' then
    raise exception 'El caso % no está entre los que no son pedidos (%)', p_caso, v_estado;
  end if;

  select jsonb_build_object('tipo', resultado ->> 'tipo', 'destino', resultado ->> 'destino')
    into v_clasificacion
  from intake.extracciones where caso = p_caso and prompt = 'clasificacion' order by id desc limit 1;

  insert into intake.motivos (caso, linea, codigo, salida, detalle)
  values (p_caso, null, 'M01', 'revision',
          jsonb_build_object('tipo', 'reclasificado_por_adv', 'clasificacion', v_clasificacion));
  update intake.casos set estado = 'en_revision', tipo = 'pedido_nuevo' where id = p_caso;
  insert into intake.eventos (caso, tipo, actor, carga)
  values (p_caso, 'pasado_a_revision', v_actor, jsonb_build_object('codigo', 'M01', 'de', 'derivado'));

  return jsonb_build_object('caso', p_caso, 'estado', 'en_revision');
end;
$$;

revoke execute on function adv.no_son_pedidos(), adv.pasar_a_revision(bigint) from public, anon, service_role;
grant execute on function adv.no_son_pedidos(), adv.pasar_a_revision(bigint) to authenticated;
