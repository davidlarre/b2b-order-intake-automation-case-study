"""La prueba congelada (tag prueba-v2.1) no cambia, y nadie la ejecuta por descuido."""

import json
import shutil
import subprocess
import sys

import pytest

import congelar_prueba as c


def test_la_prueba_es_la_del_manifiesto():
    assert c.diferencias(json.loads(c.MANIFIESTO.read_text()), c.ficheros()) == []


def test_la_correccion_de_p23_queda_en_el_manifiesto():
    m = json.loads(c.MANIFIESTO.read_text())
    assert m["tag"] == "prueba-v2.1"
    assert [(x["de"], x["a"], x["cambios"]) for x in m["correcciones"]] == [
        ("prueba-v2", "prueba-v2.1", ["cambiado data/synthetic/evaluacion-v2/prueba/etiquetas/P23.yaml"])]


def test_el_manifiesto_cubre_los_60_casos():
    rutas = json.loads(c.MANIFIESTO.read_text())["ficheros"]
    por_carpeta = {k: sum(f"/prueba/{k}/" in r for r in rutas) for k in ("fichas", "correos", "etiquetas")}
    assert por_carpeta == {"fichas": 60, "correos": 66, "etiquetas": 60}
    assert len(rutas) == 60 + 66 + 60 + len(c.SUELTOS)


@pytest.fixture
def copia(tmp_path):
    for r in json.loads(c.MANIFIESTO.read_text())["ficheros"]:
        (tmp_path / r).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(c.RAIZ / r, tmp_path / r)
    return tmp_path


@pytest.mark.parametrize("cambio", ["cambiado", "falta", "nuevo"])
def test_detecta_cualquier_cambio(copia, cambio):
    carpeta = copia / "data/synthetic/evaluacion-v2/prueba/etiquetas"
    if cambio == "cambiado":
        (carpeta / "P01.yaml").write_text((carpeta / "P01.yaml").read_text() + " ")
    elif cambio == "falta":
        (carpeta / "P01.yaml").unlink()
    else:
        (carpeta / "P61.yaml").write_text("id: P61\n")
    dif = c.diferencias(json.loads(c.MANIFIESTO.read_text()), c.ficheros(copia))
    assert len(dif) == 1 and dif[0].startswith(cambio)


def test_enviar_eml_se_niega_a_enviar_la_prueba():
    for ruta in ("prueba/correos", "prueba/correos/P01.eml"):
        p = subprocess.run([sys.executable, str(c.RAIZ / "scripts/enviar_eml.py"), str(c.EVALUACION / ruta)],
                           capture_output=True, text=True)
        assert p.returncode != 0 and "congelada" in p.stderr
