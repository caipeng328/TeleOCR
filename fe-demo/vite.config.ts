import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  // 线上部署在 /pdf/ 路径下
  base: process.env.NODE_ENV === 'production' ? '/pdf/' : '/',
  server: {
    port: 5173,
  },
  build: {
    outDir: 'dist',
  },
});
