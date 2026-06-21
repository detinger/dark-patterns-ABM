import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    // Fail loudly if 5173 is taken instead of silently hopping to 5174 (which the
    // launch scripts and README don't tell the user to open).
    strictPort: true,
  },
  optimizeDeps: {
    exclude: ['react-force-graph-2d'],
  },
})
