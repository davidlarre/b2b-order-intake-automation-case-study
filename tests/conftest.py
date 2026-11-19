import json
import os
from decimal import Decimal
from functools import partial
from pathlib import Path

import psycopg
import pytest
from psycopg.types.json import set_json_loads

ENV = Path(__file__).resolve().parent.parent / ".env"


def _leer_env():
    if not ENV.exists():
        return {}
    pares = (l.split("=", 1) for l in ENV.read_text().splitlines() if "=" in l and not l.lstrip().startswith("#"))
    return {k.strip(): v.strip().strip('"').strip("'") for k, v in pares}


@pytest.fixture(scope="session")
def db_url():
    url = os.environ.get("SUPABASE_DB_URL") or _leer_env().get("SUPABASE_DB_URL")
    if not url:
        pytest.exit("Falta SUPABASE_DB_URL en .env (es el valor DB_URL de `supabase status -o env`).", returncode=2)
    return url


@pytest.fixture
def cur(db_url):
    """Cursor en una transacción que se deshace al acabar el test: la base queda como estaba."""
    with psycopg.connect(db_url) as conn:
        # Importes de dinero: los números de jsonb se leen como Decimal, nunca como float.
        set_json_loads(partial(json.loads, parse_float=Decimal), conn)
        with conn.cursor() as c:
            yield c
        conn.rollback()
