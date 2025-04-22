import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: { // Optional: Define server options like port
    port: 5173, // Default Vite port
    strictPort: true, // Don't fallback if port is used
   }
})