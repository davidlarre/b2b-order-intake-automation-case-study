-- Segunda capa: RLS en todas las tablas de erp e intake, sin políticas (todo denegado por defecto).
-- Sin FORCE: el propietario de las tablas lo omite, así que las funciones SECURITY DEFINER del paso 2
-- siguen entrando con sus propios permisos. Un test comprueba que ninguna tabla nueva se quede sin RLS.

do $$
declare
  t record;
begin
  for t in
    select schemaname, tablename from pg_tables where schemaname in ('erp', 'intake')
  loop
    execute format('alter table %I.%I enable row level security', t.schemaname, t.tablename);
  end loop;
end;
$$;
