"""Reproducción de un fallo del entorno local, no del proyecto. Se revisa en la fase 7.

En la imagen supabase/postgres:17.6.1.106 (Supabase CLI 2.90), ejecutar una función sin permiso
con un rol reservado de Supabase (anon, service_role) tumba el proceso del servidor
(signal 11) en lugar de dar "permission denied". Con un rol no reservado da el error normal.
Atribuido a la extensión supautils: https://github.com/supabase/postgres/issues/2124 (duplicado de #2112).

Con una imagen nueva, quitar el skip y ejecutar solo este test:
    uv run pytest tests/test_entorno_supautils.py
Si pasa, el fallo está corregido. Si no, Postgres se reinicia unos segundos.
"""

import psycopg
import pytest


@pytest.mark.skip(reason="Tumba Postgres local en la imagen 17.6.1.106 (supautils, supabase/postgres#2124). Revisar en la fase 7.")
def test_rol_reservado_sin_permiso_da_permission_denied(cur):
    cur.execute("create function public.p_sql() returns int language sql as 'select 1'")
    cur.execute("revoke execute on function public.p_sql() from public, anon, authenticated, service_role")
    cur.execute("set local role service_role")
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        cur.execute("select public.p_sql()")
