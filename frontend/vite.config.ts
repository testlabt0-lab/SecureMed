import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig(({ mode }) => ({
  plugins: [react()],
  // Production build serves the SPA from Django under /static/ (whitenoise),
  // so hashed assets resolve to /static/assets/... . Dev server keeps '/'.
  base: mode === 'production' ? '/static/' : '/',
  server: {
    port: 3000,
    host: '0.0.0.0',
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/ws': {
        target: 'http://localhost:8000',
        ws: true,
        changeOrigin: true,
      },
      // There is no '/ai' entry any more. It forwarded to the retired Node
      // sidecar on :8100; every AI call the SPA makes now goes to
      // /api/v1/ai/* (see src/api/extendedApis.ts), which the '/api' rule
      // above already covers. Keeping the old rule only meant a developer
      // running the sidecar could reach an unauthenticated copy of these
      // endpoints while believing they were testing the real ones.
    },
  },
  build: {
    outDir: 'dist',
    sourcemap: false,
  },
}));
