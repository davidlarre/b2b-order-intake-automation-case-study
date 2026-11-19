import { useState, type FormEvent } from 'react';
import { supabase } from './supabase';

export function Acceso() {
  const [email, setEmail] = useState('');
  const [contrasena, setContrasena] = useState('');
  const [error, setError] = useState<string | null>(null);

  async function entrar(e: FormEvent) {
    e.preventDefault();
    setError(null);
    // Supabase Auth devuelve un token firmado; supabase-js lo guarda y lo envía en cada llamada.
    const { error } = await supabase.auth.signInWithPassword({ email, password: contrasena });
    if (error) setError(error.message === 'Invalid login credentials' ? 'El email o la contraseña no son correctos.' : error.message);
  }

  return (
    <main className="acceso">
      <form onSubmit={entrar}>
        <h1>Revisión de pedidos</h1>
        <p className="secundario">Entra con tu usuario de administración de ventas.</p>
        <label htmlFor="email">Email</label>
        <input id="email" type="email" autoComplete="username" value={email} onChange={(e) => setEmail(e.target.value)} required />
        <label htmlFor="contrasena">Contraseña</label>
        <input id="contrasena" type="password" autoComplete="current-password" value={contrasena} onChange={(e) => setContrasena(e.target.value)} required />
        <button type="submit" className="boton boton-principal">Entrar</button>
        {error && <p className="aviso-texto" role="alert">{error}</p>}
      </form>
    </main>
  );
}
