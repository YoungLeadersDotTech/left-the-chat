import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { viteSingleFile } from 'vite-plugin-singlefile'

export default defineConfig({
  base: './',
  plugins: [react(), viteSingleFile()],
  server: { port: 5173 },
  build: {
    target: 'es2020',
    assetsInlineLimit: Infinity,
    cssCodeSplit: false
  }
})
