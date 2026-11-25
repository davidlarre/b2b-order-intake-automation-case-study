import { useCallback, useEffect, useRef, useState } from 'react';
import { adv } from './supabase';
import { descargarAdjuntoPorNombre } from './correo';
import { Icono } from './Icono';
import { PanelCorreo } from './PanelCorreo';
import {
  NOMBRE_EVENTO, clienteDe, describirAdjuntos, etiquetaEstado, filaProducto, hoyALas, nombreCliente, notaPrecios,
  razonPorDefecto, sinProductos, situacion, type Accion,
} from './textos';
import type { Detalle } from './tipos';

type Props = { caso: number; alVolver: (aviso?: string) => void; alSiguiente: (actual: number) => void };

export function DetalleCaso({ caso, alVolver, alSiguiente }: Props) {
  const [detalle, setDetalle] = useState<Detalle | null>(null);
  const [hecho, setHecho] = useState<string | null>(null);   // confirmación tras decidir
  const [error, setError] = useState<string | null>(null);
  const [verCorreo, setVerCorreo] = useState(false);
  const [buscando, setBuscando] = useState(false);
  const [busqueda, setBusqueda] = useState('');
  const [encontrados, setEncontrados] = useState<{ codigo: string; razon_social: string }[]>([]);
  const [descartando, setDescartando] = useState(false);
  const [razon, setRazon] = useState('');
  const [faltaRazon, setFaltaRazon] = useState(false);
  const campoRazon = useRef<HTMLInputElement>(null);
  const cerrarCorreo = useCallback(() => setVerCorreo(false), []);

  async function cargar() {
    setDetalle(await adv<Detalle>('detalle_caso', { p_caso: caso }));
  }

  useEffect(() => {
    setHecho(null); setError(null); setBuscando(false); setDescartando(false); setRazon(''); setVerCorreo(false);
    cargar().catch((e) => setError((e as Error).message));
  }, [caso]);

  // Cada decisión la comprueba la base de datos; si no se puede, el motivo sale aquí, sin cambiar nada.
  async function decidir(funcion: string, args: Record<string, unknown>, mensaje: (d: Detalle) => string) {
    setError(null);
    try {
      await adv(funcion, { p_caso: caso, ...args });
      const d = await adv<Detalle>('detalle_caso', { p_caso: caso });
      setDetalle(d);
      setHecho(mensaje(d));
    } catch (e) {
      setError((e as Error).message);
    }
  }

  if (!detalle) return <main className="contenido">{error ? <p className="aviso-texto">{error}</p> : <p className="secundario">Cargando…</p>}</main>;

  const sit = situacion(detalle);
  const etiqueta = etiquetaEstado(detalle);
  const cliente = clienteDe(detalle);
  const abiertos = detalle.motivos.filter((m) => m.estado === 'abierto');
  const adjuntos = detalle.correo?.adjuntos ?? [];
  const m02 = detalle.motivos.find((m) => m.codigo === 'M02');
  const noLegibles: string[] = ((m02?.detalle as { adjuntos?: string[] })?.adjuntos) ?? [];

  function crear(clienteElegido: string | null, razonR02?: string) {
    const quien = clienteElegido ?? detalle!.cliente_propuesto;
    const confirmaR02 = abiertos.some((m) => m.codigo === 'R02');
    const forzados = abiertos.map((m) => ({
      codigo: m.codigo, linea: m.linea, razon: m.codigo === 'R02' && razonR02 ? razonR02 : razonPorDefecto(m), texto: '',
    }));
    decidir('crear_pedido', { p_forzados: forzados, p_cliente: confirmaR02 ? quien : null },
      (d) => `Pedido creado en el ERP: ${d.pedido?.numero ?? ''}${confirmaR02 && quien ? `, para ${nombreCliente(d.nombres, quien)}` : ''}.`);
  }

  function ejecutar(a: Accion) {
    switch (a.tipo) {
      case 'crear': return crear(a.cliente, a.razonR02);
      case 'buscar_cliente': return setBuscando(true);
      case 'descargar':
        return descargarAdjuntoPorNombre(detalle!.correo!.ruta_eml!, a.adjunto).catch((e) => setError((e as Error).message));
      case 'a_mano':
        return decidir('cerrar_caso', { p_resultado: 'procesado a mano', p_texto: null },
          () => `Pedido nº ${caso} marcado como tecleado a mano en el ERP.`);
      case 'atendido':
        return decidir('cerrar_caso', { p_resultado: a.resultado, p_texto: null }, () => `Caso nº ${caso}: ${a.resultado}.`);
      case 'descartar':
        setDescartando(true);
        setTimeout(() => campoRazon.current?.focus(), 0);
    }
  }

  function confirmarDescarte() {
    if (!razon.trim()) { setFaltaRazon(true); campoRazon.current?.focus(); return; }
    decidir('cerrar_caso', { p_resultado: 'descartado', p_texto: razon.trim() }, () => `Pedido nº ${caso} descartado.`);
  }

  async function buscar(texto: string) {
    setBusqueda(texto);
    setEncontrados(texto.trim().length < 2 ? [] : await adv('buscar_clientes', { p_texto: texto }));
  }

  const nota = notaPrecios(detalle);

  return (
    <main className="contenido">
      <button className="boton-enlace volver" onClick={() => alVolver()}>← Pedidos pendientes de revisión</button>

      <div className="titulo-detalle">
        <h1>Pedido nº {detalle.caso} · {detalle.correo?.asunto ?? 'Sin asunto'}</h1>
        {etiqueta && <span className="etiqueta">{etiqueta}</span>}
      </div>

      {hecho && (
        <section className="recuadro recuadro-hecho" aria-live="polite">
          <p className="problema"><Icono nombre="hecho" /> {hecho}</p>
          <div className="acciones">
            <button className="boton boton-principal" onClick={() => alSiguiente(caso)}>Siguiente pedido</button>
            <button className="boton boton-secundario" onClick={() => alVolver(hecho)}>Volver a la lista</button>
          </div>
        </section>
      )}

      {!hecho && sit && (
        <section className="recuadro" aria-labelledby="que-hacer">
          <h2 id="que-hacer" className="rotulo">Por qué está aquí y qué hacer</h2>
          <p className="problema">{sit.problema}</p>
          <p className="que-hacer">{sit.queHacer}</p>
          {sit.ademas.length > 0 && (
            <ul className="ademas">{sit.ademas.map((t) => <li key={t}>Además, {t}.</li>)}</ul>
          )}

          {!descartando && (
            <div className="acciones">
              {sit.acciones.map((a, i) => (
                <button key={a.etiqueta}
                  className={`boton ${i === 0 ? 'boton-principal' : a.tipo === 'descartar' ? 'boton-neutro' : 'boton-secundario'}`}
                  onClick={() => ejecutar(a)}>
                  {a.etiqueta}
                </button>
              ))}
            </div>
          )}

          {buscando && !descartando && (
            <div className="buscar-cliente">
              <label htmlFor="buscar">¿De qué cliente es?</label>
              <input id="buscar" autoFocus placeholder="Nombre o código del cliente" value={busqueda} onChange={(e) => buscar(e.target.value)} />
              {busqueda.trim().length >= 2 && encontrados.length === 0 && <p className="secundario pequeno">Ningún cliente coincide.</p>}
              <div className="acciones">
                {encontrados.map((c) => (
                  <button key={c.codigo} className="boton boton-secundario" onClick={() => crear(c.codigo)}>
                    Es de {c.razon_social}: crear el pedido
                  </button>
                ))}
              </div>
            </div>
          )}

          {descartando && (
            <div className="descartar">
              <label htmlFor="razon">¿Por qué descartas el pedido nº {caso}?</label>
              <input id="razon" ref={campoRazon} placeholder="Por ejemplo: es publicidad, es un duplicado…" value={razon}
                aria-describedby={faltaRazon ? 'falta-razon' : undefined}
                onChange={(e) => { setRazon(e.target.value); setFaltaRazon(false); }}
                onKeyDown={(e) => e.key === 'Enter' && confirmarDescarte()} />
              {faltaRazon && <p id="falta-razon" className="aviso-texto pequeno">Escribe una razón breve para poder descartarlo.</p>}
              <div className="acciones">
                <button className="boton boton-peligro" onClick={confirmarDescarte}>Descartar el pedido</button>
                <button className="boton boton-neutro" onClick={() => { setDescartando(false); setFaltaRazon(false); }}>Cancelar</button>
              </div>
            </div>
          )}
        </section>
      )}

      {error && <p className="aviso-texto" role="alert">{error}</p>}

      <section className="bloque" aria-labelledby="cliente">
        <h2 id="cliente" className="rotulo">Cliente</h2>
        {cliente.confirmado
          ? <p className="cliente-nombre">{cliente.nombre}</p>
          : <p className="cliente-nombre en-duda"><Icono nombre="aviso" tamano={22} /> {cliente.titulo ?? 'Sin confirmar'}</p>}
        {cliente.nota && <p className="secundario pequeno">{cliente.nota}</p>}
      </section>

      <section className="bloque" aria-labelledby="correo">
        <h2 id="correo" className="rotulo">Correo original</h2>
        <div className="fila-correo">
          {detalle.correo?.ruta_eml
            ? <button className="boton boton-neutro" onClick={() => setVerCorreo(true)}>Ver correo</button>
            : <span className="secundario">No hay copia del correo original de este pedido.</span>}
          <span className="secundario pequeno">
            De {detalle.correo?.remitente_nombre ?? detalle.correo?.remitente}, {hoyALas(detalle.recibido)}. {describirAdjuntos(adjuntos)}
          </span>
        </div>
      </section>

      <section className="bloque" aria-labelledby="productos">
        <h2 id="productos" className="rotulo">Productos pedidos</h2>
        {detalle.lineas.length === 0
          ? <p className="caja-texto">{sinProductos(detalle)}</p>
          : (
            <>
              {nota && <p className="nota-precios"><Icono nombre="aviso" tamano={16} /> {nota}</p>}
              <div className="tabla-caja">
                <table className="tabla">
                  <thead>
                    <tr><th>Producto</th><th className="derecha">Cantidad</th><th className="derecha">Precio en el correo</th><th className="derecha">Precio que se aplicará</th></tr>
                  </thead>
                  <tbody>
                    {detalle.lineas.map((l) => {
                      const f = filaProducto(l, detalle);
                      return (
                        <tr key={l.linea}>
                          <td>
                            {f.sinIdentificar
                              ? <span className="en-duda"><Icono nombre="aviso" tamano={16} /> Producto sin identificar: {f.nombre}</span>
                              : <strong>{f.nombre}</strong>}
                            {f.codigo && <div className="secundario pequeno">{f.codigo}</div>}
                          </td>
                          <td className="derecha sin-salto">
                            {f.cantidadDudosa ? <span className="en-duda"><Icono nombre="aviso" tamano={16} /> {f.cantidad}</span> : f.cantidad}
                            {f.cantidadDudosa && <div className="secundario pequeno">{f.cantidadDudosa}</div>}
                          </td>
                          <td className="derecha sin-salto">
                            {f.precioCorreo
                              ? (f.precioDudoso ? <span className="en-duda"><Icono nombre="aviso" tamano={16} /> {f.precioCorreo}</span> : f.precioCorreo)
                              : <span className="secundario">No indicado</span>}
                          </td>
                          <td className="derecha sin-salto">{f.precioAplicado ?? <span className="secundario">Se calculará al confirmar el cliente</span>}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </>
          )}
      </section>

      <details className="tecnico">
        <summary>Información técnica</summary>
        <dl>
          <dt>Estado interno</dt><dd><code>{detalle.estado}</code></dd>
          <dt>Motivos</dt><dd><code>{detalle.motivos.map((m) => `${m.codigo}${m.linea ? `/${m.linea}` : ''} (${m.estado})`).join(', ') || '—'}</code></dd>
          <dt>Configuración</dt><dd><code>{detalle.configuracion ?? '—'}</code></dd>
          <dt>Autenticación del remitente</dt><dd><code>{detalle.correo?.autenticacion ?? '—'}</code></dd>
          <dt>Historial</dt>
          <dd>
            <ol>
              {detalle.eventos.map((e, i) => (
                <li key={i}>{new Date(e.fecha).toLocaleString('es-ES')} · {NOMBRE_EVENTO[e.tipo] ?? e.tipo} · <code>{e.actor}</code></li>
              ))}
            </ol>
          </dd>
        </dl>
      </details>

      {verCorreo && detalle.correo?.ruta_eml && (
        <PanelCorreo ruta={detalle.correo.ruta_eml} noLegibles={noLegibles} alCerrar={cerrarCorreo} />
      )}
    </main>
  );
}
