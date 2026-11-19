import { useEffect, useState } from 'react';
import { adv } from './supabase';
import { PRIORIDAD, haceCuanto, porQueEnRevision } from './textos';
import { Icono } from './Icono';
import type { FilaCola } from './tipos';

export function Cola({ alAbrir, aviso }: { alAbrir: (caso: number) => void; aviso: string | null }) {
  const [filas, setFilas] = useState<FilaCola[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function cargar() {
    setError(null);
    try {
      setFilas(await adv<FilaCola[]>('cola'));
    } catch (e) {
      setError((e as Error).message);
    }
  }

  useEffect(() => { cargar(); }, []);

  return (
    <main className="contenido ancho">
      <div className="titulo-cola">
        <div>
          <h1>Pedidos pendientes de revisión</h1>
          <p className="secundario">Pedidos que el sistema no ha podido procesar solo. Ábrelos para decidir.</p>
        </div>
        {filas && <span className="secundario">{filas.length === 1 ? '1 pedido' : `${filas.length} pedidos`}</span>}
        <button className="boton boton-neutro" onClick={cargar}>Actualizar</button>
      </div>

      {aviso && <p className="confirmacion"><Icono nombre="hecho" /> {aviso}</p>}
      {error && <p className="aviso-texto">{error}</p>}

      {filas && filas.length === 0 && (
        <div className="vacio">
          <p><strong>No hay pedidos pendientes de revisión.</strong></p>
          <p className="secundario">Los pedidos nuevos que necesiten una decisión aparecerán aquí.</p>
        </div>
      )}

      {filas && filas.length > 0 && (
        <>
          <div className="tabla-caja">
            <table className="tabla tabla-cola">
              <thead>
                <tr>
                  <th>Nº</th><th>Recibido</th><th>Cliente</th><th>Remitente</th>
                  <th>Asunto del correo</th><th>Por qué está en revisión</th><th>Prioridad</th>
                </tr>
              </thead>
              <tbody>
                {filas.map((f) => {
                  const cliente = f.razon_social ?? (f.cliente_por_remitente ? f.cliente_propuesto : null);
                  const prioridad = PRIORIDAD[f.prioridad];
                  return (
                    <tr key={f.caso} tabIndex={0} aria-label={`Abrir el pedido nº ${f.caso}`}
                      onClick={() => alAbrir(f.caso)} onKeyDown={(e) => e.key === 'Enter' && alAbrir(f.caso)}>
                      <td className="numero">{f.caso}</td>
                      <td className="sin-salto" title={new Date(f.recibido).toLocaleString('es-ES')}>{haceCuanto(f.recibido)}</td>
                      <td>
                        {cliente
                          ? <strong>{cliente.replace(/,?\s+S\.(L|A|C\.P)\.$/, '')}</strong>
                          : <span className="en-duda"><Icono nombre="aviso" tamano={16} /> Sin confirmar</span>}
                      </td>
                      <td className="secundario pequeno">{f.remitente}</td>
                      <td>{f.asunto}</td>
                      <td>{porQueEnRevision(f)}</td>
                      <td>{prioridad && <span className={`etiqueta prioridad-${f.prioridad}`}>{prioridad}</span>}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          <p className="secundario pequeno">Primero las reclamaciones, después los pedidos que aún pueden salir hoy (si se resuelven antes de las 13:00) y el resto por antigüedad.</p>
        </>
      )}
    </main>
  );
}
