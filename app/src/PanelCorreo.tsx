import { useEffect, useRef, useState } from 'react';
import type { Email } from 'postal-mime';
import { cuerpoLegible, descargarAdjunto, leerCorreo } from './correo';
import { Icono } from './Icono';

const direccion = (a: { name?: string; address?: string } | undefined) =>
  a ? (a.name ? `${a.name} <${a.address ?? ''}>` : a.address ?? '') : '';

const tamano = (bytes: number) => (bytes < 1024 ? `${bytes} bytes` : `${Math.round(bytes / 1024)} KB`);

export function PanelCorreo({ ruta, noLegibles, alCerrar }: { ruta: string; noLegibles: string[]; alCerrar: () => void }) {
  const [correo, setCorreo] = useState<Email | null>(null);
  const [error, setError] = useState<string | null>(null);
  const cerrar = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    leerCorreo(ruta).then(setCorreo).catch((e) => setError((e as Error).message));
    cerrar.current?.focus();
    const tecla = (e: KeyboardEvent) => e.key === 'Escape' && alCerrar();
    window.addEventListener('keydown', tecla);
    return () => window.removeEventListener('keydown', tecla);
  }, [ruta, alCerrar]);

  return (
    <div className="velo" onClick={alCerrar}>
      <aside className="panel-correo" role="dialog" aria-modal="true" aria-label="Correo original" onClick={(e) => e.stopPropagation()}>
        <div className="panel-cabecera">
          <h2>{correo?.subject ?? 'Correo original'}</h2>
          <button ref={cerrar} className="boton-icono" aria-label="Cerrar el correo" onClick={alCerrar}><Icono nombre="cerrar" /></button>
        </div>
        {error && <p className="aviso-texto panel-relleno">{error}</p>}
        {!correo && !error && <p className="secundario panel-relleno">Abriendo el correo…</p>}
        {correo && (
          <>
            <dl className="cabeceras-correo">
              <dt>De</dt><dd>{direccion(correo.from)}</dd>
              <dt>Para</dt><dd>{(correo.to ?? []).map(direccion).join(', ')}</dd>
              <dt>Fecha</dt><dd>{correo.date ? new Date(correo.date).toLocaleString('es-ES', { dateStyle: 'full', timeStyle: 'short' }) : ''}</dd>
            </dl>
            <div className="cuerpo-correo">{cuerpoLegible(correo)}</div>
            {correo.attachments.length > 0 && (
              <div className="adjuntos">
                <h3>Adjuntos</h3>
                <ul>
                  {correo.attachments.map((a, i) => {
                    const bytes = typeof a.content === 'string' ? a.content.length : a.content.byteLength;
                    const ilegible = !!a.filename && noLegibles.includes(a.filename);
                    return (
                      <li key={i}>
                        <Icono nombre="documento" />
                        <div className="adjunto-texto">
                          <strong>{a.filename ?? 'Adjunto sin nombre'}</strong>
                          <span className="secundario">{tamano(bytes)}{ilegible ? '. El sistema no lo puede leer.' : ''}</span>
                        </div>
                        <button className="boton-enlace" onClick={() => descargarAdjunto(a)}>Descargar</button>
                      </li>
                    );
                  })}
                </ul>
              </div>
            )}
          </>
        )}
      </aside>
    </div>
  );
}
