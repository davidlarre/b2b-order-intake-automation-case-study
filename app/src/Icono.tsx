// Iconos de trazo, decorativos (el texto de al lado dice lo mismo).
const TRAZOS = {
  aviso: <><path d="M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z" /><path d="M12 9v4" /><path d="M12 17h.01" /></>,
  cerrar: <><path d="M18 6 6 18" /><path d="m6 6 12 12" /></>,
  documento: <><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" /><path d="M14 2v6h6" /></>,
  hecho: <path d="M20 6 9 17l-5-5" />,
};

export function Icono({ nombre, tamano = 18 }: { nombre: keyof typeof TRAZOS; tamano?: number }) {
  return (
    <svg width={tamano} height={tamano} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"
      strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" className="icono">
      {TRAZOS[nombre]}
    </svg>
  );
}
