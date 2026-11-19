"""Crea (o actualiza) los usuarios de ADV en Supabase Auth local, con su rol en app_metadata.

Uso:
    uv run scripts/crear_usuarios_adv.py

- El rol va en app_metadata, que solo puede escribir un administrador; user_metadata lo puede cambiar el
  propio usuario y la base de datos nunca lo mira (supabase/migrations/20261120000009_esquema_adv.sql).
- Las contraseñas salen de .env (ADV_GESTORA_PASSWORD, ADV_RESPONSABLE_PASSWORD). Si faltan, se generan y se
  añaden a .env sin mostrarlas.
- La clave secreta se lee de `supabase status` en el momento: no se guarda en ningún fichero.
- Se puede ejecutar varias veces: si el usuario existe, actualiza su rol y su contraseña.
"""

import json
import secrets
import subprocess
import sys
import urllib.error
import urllib.request

from entorno import RAIZ, leer_env

USUARIOS = [
    {"email": "gestora@orvalle.example", "rol": "adv", "variable": "ADV_GESTORA_PASSWORD"},
    {"email": "responsable.adv@orvalle.example", "rol": "adv_responsable", "variable": "ADV_RESPONSABLE_PASSWORD"},
]


def estado_supabase():
    salida = subprocess.run(["supabase", "status", "-o", "env"], capture_output=True, text=True, cwd=RAIZ)
    if salida.returncode != 0:
        sys.exit("Supabase local no está en marcha (supabase start)")
    valores = dict(l.split("=", 1) for l in salida.stdout.splitlines() if "=" in l)
    return valores["API_URL"].strip('"'), valores["SECRET_KEY"].strip('"')


def peticion(api_url, clave, metodo, ruta, cuerpo=None):
    datos = json.dumps(cuerpo).encode() if cuerpo is not None else None
    req = urllib.request.Request(f"{api_url}/auth/v1{ruta}", data=datos, method=metodo, headers={
        "apikey": clave, "Authorization": f"Bearer {clave}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        sys.exit(f"{metodo} {ruta}: HTTP {e.code} {e.read().decode(errors='replace')[:200]}")


def contrasena(variable, env):
    if env.get(variable):
        return env[variable]
    nueva = secrets.token_urlsafe(18)
    with open(RAIZ / ".env", "a") as f:
        f.write(f"\n{variable}={nueva}\n")
    print(f"  {variable} generada y añadida a .env")
    return nueva


def main():
    api_url, clave = estado_supabase()
    env = leer_env()
    existentes = {u["email"]: u for u in peticion(api_url, clave, "GET", "/admin/users?per_page=1000")["users"]}
    for u in USUARIOS:
        datos = {"password": contrasena(u["variable"], env), "email_confirm": True,
                 "app_metadata": {"rol": u["rol"]}}
        if u["email"] in existentes:
            peticion(api_url, clave, "PUT", f"/admin/users/{existentes[u['email']]['id']}", datos)
            print(f"{u['email']}: actualizado (rol {u['rol']})")
        else:
            peticion(api_url, clave, "POST", "/admin/users", {"email": u["email"], **datos})
            print(f"{u['email']}: creado (rol {u['rol']})")


if __name__ == "__main__":
    main()
