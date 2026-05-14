import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5174,
    hmr: false,  // Disable HMR — prevents state reset on file save
  }
})