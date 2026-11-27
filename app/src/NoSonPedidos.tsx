import { useCallback, useEffect, useState } from 'react';
import { adv } from './supabase';
import { describirAdjuntos, haceCuanto, motivoClasificacion } from './textos';
import { Icono } from './Icono';
import { PanelCorreo } from './PanelCorreo';
import type { FilaNoPedido } from './tipos';

// Los correos que la clasificación ha sacado de la cola (factura a contabilidad, publicidad archivada).
// Ninguno desaparece: se ven aquí, y si alguno es un pedido, vuelve a la cola de revisión.
export function NoSonPedidos({ alAbrir }: { alAbrir: (caso: number) => void }) {
  const [filas, setFilas] = useState<FilaNoPedido[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pasado, setPasado] = useState<number | null>(null);
  const [correo, setCorreo] = useState<string | null>(null);
  const cerrarCorreo = useCallback(() => setCorreo(null), []);

  async function cargar() {
    setError(null);
    try {
      setFilas(await adv<FilaNoPedido[]>('no_son_pedidos'));
    } catch (e) {
      setError((e as Error).message);
    }
  }

  useEffect(() => { cargar(); }, []);

  async function pasarARevision(caso: number) {
    setError(null);
    try {
      await adv('pasar_a_revision', { p_caso: caso });
      setPasado(caso);
      await cargar();
    } catch (e) {
      setError((e as Error).message);
    }
  }

  return (
    <main className="contenido ancho">
      <div className="titulo-cola">
        <div>
          <h1>No son pedidos</h1>
          <p className="secundario">Correos que el sistema ha clasificado como facturas o publicidad y no ha puesto en la cola. Si alguno es un pedido, pásalo a revisión.</p>
        </div>
        {filas && <span className="secundario">{filas.length === 1 ? '1 correo' : `${filas.length} correos`}</span>}
        <button className="boton boton-neutro" onClick={cargar}>Actualizar</button>
      </div>

      {pasado !== null && (
        <p className="confirmacion" aria-live="polite">
          <Icono nombre="hecho" /> El correo nº {pasado} está ahora en los pedidos pendientes de revisión.
          <button className="boton-enlace" onClick={() => alAbrir(pasado)}>Abrirlo</button>
        </p>
      )}
      {error && <p className="aviso-texto" role="alert">{error}</p>}

      {filas && filas.length === 0 && (
        <div className="vacio">
          <p><strong>No hay correos apartados.</strong></p>
          <p className="secundario">Las facturas y la publicidad que detecte el sistema aparecerán aquí.</p>
        </div>
      )}

      {filas && filas.length > 0 && (
        <div className="tabla-caja">
          <table className="tabla">
            <thead>
              <tr><th>Nº</th><th>Recibido</th><th>Remitente</th><th>Asunto del correo</th><th>Por qué no es un pedido</th><th><span className="oculto">Acciones</span></th></tr>
            </thead>
            <tbody>
              {filas.map((f) => (
                <tr key={f.caso}>
                  <td className="numero">{f.caso}</td>
                  <td className="sin-salto" title={new Date(f.recibido).toLocaleString('es-ES')}>{haceCuanto(f.recibido)}</td>
                  <td>
                    {f.remitente_nombre && <div>{f.remitente_nombre}</div>}
                    <div className="secundario pequeno">{f.remitente}</div>
                  </td>
                  <td>
                    {f.asunto ?? <span className="secundario">Sin asunto</span>}
                    <div className="secundario pequeno">{describirAdjuntos(f.adjuntos ?? [])}</div>
                  </td>
                  <td>
                    {motivoClasificacion(f.clasificacion)}
                    <div className="secundario pequeno">Clasificado por {f.clasificacion.modelo ?? 'la IA'}{f.clasificacion.version ? `, prompt v${f.clasificacion.version}` : ''}</div>
                  </td>
                  <td>
                    <div className="acciones-fila">
                      {f.ruta_eml && <button className="boton boton-neutro" onClick={() => setCorreo(f.ruta_eml)}>Ver correo</button>}
                      <button className="boton boton-secundario" onClick={() => pasarARevision(f.caso)}>Es un pedido: pasar a revisión</button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {correo && <PanelCorreo ruta={correo} noLegibles={[]} alCerrar={cerrarCorreo} />}
    </main>
  );
}
