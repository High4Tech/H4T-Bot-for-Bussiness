import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';
import path from 'node:path';
const proxy={ '/api': {target:'http://127.0.0.1:8871',changeOrigin:true} };
export default defineConfig({ plugins: [react(),tailwindcss()], resolve:{alias:{'@':path.resolve(__dirname,'src')}}, server: { host: '127.0.0.1', port: 5173, strictPort: true,proxy }, preview: { host: '127.0.0.1', port: 5173, strictPort: true,proxy } });
