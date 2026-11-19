import { createClient } from '@supabase/supabase-js';

// La URL y la clave publicable son públicas por diseño: no dan acceso a nada sin un usuario con rol de ADV.
// Se leen de app/.env.local (no se versiona).
const url = import.meta.env.VITE_SUPABASE_URL as string | undefined;
const clave = import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY as string | undefined;
if (!url || !clave) {
  throw new Error('Faltan VITE_SUPABASE_URL y VITE_SUPABASE_PUBLISHABLE_KEY en app/.env.local');
}

export const supabase = createClient(url, clave);

// Todas las llamadas van a funciones del esquema adv: la app no lee ni escribe tablas.
export async function adv<T>(funcion: string, args: Record<string, unknown> = {}): Promise<T> {
  const { data, error } = await supabase.schema('adv').rpc(funcion, args);
  if (error) throw new Error(error.message);
  return data as T;
}
