import { defineConfig } from 'vite';

export default defineConfig({
  server: {
    host: '127.0.0.1',
    port: 5173,
    strictPort: true,
    proxy: { '/api': 'http://127.0.0.1:8010' },
  },
  // Keep CSS readable; this build does not require an optional native minifier.
  build: { outDir: 'dist', sourcemap: false, cssMinify: false },
});
