import PostalMime, { type Email } from 'postal-mime';
import { supabase } from './supabase';

// El .eml original está en el bucket privado "correos". Storage solo lo entrega a usuarios con rol de ADV
// (la política mira app_metadata, como las funciones de adv); la sesión de supabase-js va en la petición.
const cache = new Map<string, Promise<Email>>();

export function leerCorreo(ruta: string): Promise<Email> {
  if (!cache.has(ruta)) {
    cache.set(ruta, (async () => {
      const { data, error } = await supabase.storage.from('correos').download(ruta);
      if (error || !data) throw new Error('No se ha podido abrir el correo original.');
      return PostalMime.parse(await data.arrayBuffer());
    })());
    cache.get(ruta)!.catch(() => cache.delete(ruta));
  }
  return cache.get(ruta)!;
}

// Descarga un adjunto tal como llegó, sin tocarlo.
export function descargarAdjunto(adjunto: Email['attachments'][number]) {
  const bytes = typeof adjunto.content === 'string'
    ? new TextEncoder().encode(adjunto.content)
    : new Uint8Array(adjunto.content).slice();   // copia a un ArrayBuffer propio, que es lo que acepta Blob
  const url = URL.createObjectURL(new Blob([bytes], { type: adjunto.mimeType || 'application/octet-stream' }));
  const enlace = document.createElement('a');
  enlace.href = url;
  enlace.download = adjunto.filename ?? 'adjunto';
  enlace.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export async function descargarAdjuntoPorNombre(ruta: string, nombre: string) {
  const correo = await leerCorreo(ruta);
  const adjunto = correo.attachments.find((a) => a.filename === nombre);
  if (!adjunto) throw new Error(`El correo no tiene el adjunto ${nombre}.`);
  descargarAdjunto(adjunto);
}

// El cuerpo legible: el texto plano; si solo hay HTML, el texto sin etiquetas (nunca se pinta HTML del correo).
export function cuerpoLegible(correo: Email): string {
  if (correo.text?.trim()) return correo.text.trim();
  if (!correo.html) return '';
  const doc = new DOMParser().parseFromString(correo.html, 'text/html');
  return (doc.body.textContent ?? '').replace(/\n{3,}/g, '\n\n').trim();
}
