-- api.codigos_producto devuelve un objeto {"codigos": [...]} en lugar de una lista: el nodo HTTP Request de
-- n8n convierte una respuesta que es una lista en un elemento por valor. Misma firma; nada la usaba todavía.

create or replace function intake.codigos_producto() returns jsonb
language sql stable security definer set search_path = '' as $$
  select jsonb_build_object('codigos',
                            coalesce(jsonb_agg(p.codigo order by p.codigo), '[]'::jsonb))
  from erp.productos p;
$$;
