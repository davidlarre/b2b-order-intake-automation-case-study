import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// Solo en local: la app escucha en 127.0.0.1, no en la red.
export default defineConfig({
  plugins: [react()],
  server: { host: '127.0.0.1', port: 5173, strictPort: true },
});
