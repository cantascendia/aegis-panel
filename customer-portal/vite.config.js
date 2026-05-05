import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// Customer self-service portal — P1 static prototype
// base: '/portal/' so it can be mounted under nilou.network/portal/
// or wherever the operator chooses. Adjust if served at root.
export default defineConfig({
  plugins: [react()],
  base: '/portal/',
  server: {
    port: 5174,
    strictPort: false,
  },
  build: {
    outDir: 'dist',
    sourcemap: false,
  },
});
