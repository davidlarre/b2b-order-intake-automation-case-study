import psycopg
import pytest


def test_datos_de_arranque(cur):
    cur.execute("select (select count(*) from erp.productos), (select count(*) from erp.clientes),"
                " (select count(*) from erp.tarifas where estado = 'activa')")
    assert cur.fetchone() == (10, 3, 5)


def test_eventos_solo_admite_inserciones(cur):
    cur.execute("insert into intake.eventos (tipo, actor) values ('prueba', 'test') returning id")
    evento = cur.fetchone()[0]
    with pytest.raises(psycopg.errors.RaiseException):
        cur.execute("update intake.eventos set tipo = 'otro' where id = %s", (evento,))


def test_tarifa_con_estado_invalido_se_rechaza(cur):
    with pytest.raises(psycopg.errors.CheckViolation):
        cur.execute("insert into erp.tarifas (cliente, producto, precio_neto, desde, estado, origen)"
                    " values ('C0002', 'TUE-M8-ZN', 0.03, '2026-01-01', 'dudosa', 'test')")


@pytest.mark.parametrize("rol", ["anon", "authenticated"])
def test_roles_de_la_api_no_leen_el_erp(cur, rol):
    cur.execute(f"set local role {rol}")
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        cur.execute("select * from erp.tarifas")


def test_todas_las_tablas_tienen_rls(cur):
    cur.execute("select n.nspname || '.' || c.relname from pg_class c"
                " join pg_namespace n on n.oid = c.relnamespace"
                " where n.nspname in ('erp', 'intake') and c.relkind = 'r' and not c.relrowsecurity")
    assert cur.fetchall() == []


def test_rls_niega_aunque_se_concedan_permisos_por_error(cur):
    # Simula el error: alguien da permisos de lectura a authenticated. RLS sin políticas sigue sin devolver filas.
    cur.execute("grant usage on schema erp to authenticated; grant select on erp.tarifas to authenticated")
    cur.execute("set local role authenticated")
    cur.execute("select count(*) from erp.tarifas")
    assert cur.fetchone()[0] == 0
