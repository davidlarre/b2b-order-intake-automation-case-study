-- Extracción completa, paso 4b: el extractor determinista solo reconoce en el texto códigos que existen
-- en el catálogo (04, sección 6.3). n8n le pasa la lista de códigos. Solo códigos: nada de clientes ni precios.
-- Incluye los descatalogados: si un cliente pide uno, la línea se lee y R09 decide.

create function intake.codigos_producto() returns jsonb
language sql stable security definer set search_path = '' as $$
  select coalesce(jsonb_agg(p.codigo order by p.codigo), '[]'::jsonb) from erp.productos p;
$$;

revoke execute on function intake.codigos_producto() from public, anon, authenticated, service_role;

create function api.codigos_producto() returns jsonb
language sql stable security definer set search_path = '' as $$
  select intake.codigos_producto();
$$;

revoke execute on function api.codigos_producto() from public, anon, authenticated;
grant execute on function api.codigos_producto() to service_role;
