import { useEffect, useState } from 'react';
import type { Session } from '@supabase/supabase-js';
import { adv, supabase } from './supabase';
import { Acceso } from './Acceso';
import { Cola } from './Cola';
import { DetalleCaso } from './DetalleCaso';
import { NoSonPedidos } from './NoSonPedidos';
import type { FilaCola } from './tipos';

export function App() {
  const [sesion, setSesion] = useState<Session | null>(null);
  const [caso, setCaso] = useState<number | null>(null);
  const [vista, setVista] = useState<'cola' | 'no_son_pedidos'>('cola');
  const [aviso, setAviso] = useState<string | null>(null);

  useEffect(() => {
    supabase.auth.getSession().then(({ data }) => setSesion(data.session));
    const { data } = supabase.auth.onAuthStateChange((_evento, nueva) => setSesion(nueva));
    return () => data.subscription.unsubscribe();
  }, []);

  function volver(mensaje?: string) {
    setAviso(mensaje ?? null);
    setCaso(null);
    setVista('cola');
  }

  function irA(v: typeof vista) {
    setAviso(null);
    setCaso(null);
    setVista(v);
  }

  // El siguiente de la cola, en su orden de prioridad (el que se acaba de decidir ya no está en ella).
  async function siguiente(actual: number) {
    const cola = await adv<FilaCola[]>('cola');
    const otro = cola.find((f) => f.caso !== actual);
    if (otro) { setAviso(null); setCaso(otro.caso); }
    else volver('No quedan pedidos pendientes de revisión.');
  }

  if (!sesion) return <Acceso />;

  return (
    <div className="app">
      <header className="cabecera">
        <span className="marca">Orvalle · Revisión de pedidos</span>
        <span className="secundario pequeno">{sesion.user.email}</span>
        <button className="boton boton-neutro" onClick={() => supabase.auth.signOut()}>Salir</button>
      </header>
      <nav className="pestanas" aria-label="Listas">
        <button className="pestana" aria-current={caso === null && vista === 'cola' ? 'page' : undefined} onClick={() => irA('cola')}>Pendientes de revisión</button>
        <button className="pestana" aria-current={caso === null && vista === 'no_son_pedidos' ? 'page' : undefined} onClick={() => irA('no_son_pedidos')}>No son pedidos</button>
      </nav>
      {caso === null
        ? (vista === 'cola'
          ? <Cola alAbrir={(c) => { setAviso(null); setCaso(c); }} aviso={aviso} />
          : <NoSonPedidos alAbrir={(c) => { setAviso(null); setCaso(c); }} />)
        : <DetalleCaso caso={caso} alVolver={volver} alSiguiente={siguiente} />}
    </div>
  );
}
