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
      '/ai': {
        target: 'http://localhost:8100',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/ai/, ''),
      },
    },
  },
  build: {
    outDir: 'dist',
    sourcemap: false,
  },
}));
