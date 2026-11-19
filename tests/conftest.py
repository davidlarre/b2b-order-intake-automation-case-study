import json
import sys
from decimal import Decimal
from functools import partial
from pathlib import Path

import psycopg
import pytest
from psycopg.types.json import set_json_loads

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "scripts"))

from cargar_prompts import EXTRACTION, cargar  # noqa: E402
from entorno import leer_env  # noqa: E402


@pytest.fixture(scope="session")
def db_url():
    url = leer_env().get("SUPABASE_DB_URL")
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


@pytest.fixture
def prompt_hash(cur):
    """Carga y activa la versión actual de extraction/extraccion dentro de la transacción del test."""
    return cargar(cur, EXTRACTION / "extraccion", activar=True)["hash"]
