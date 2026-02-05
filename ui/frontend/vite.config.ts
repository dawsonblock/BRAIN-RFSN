import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Dev proxy: frontend on :5173 proxies /api and /ws to FastAPI backend on :8000
export default defineConfig({
    plugins: [react()],
    server: {
        port: 5173,
        proxy: {
            // REST API proxy
            '/api': {
                target: 'http://localhost:8000',
                changeOrigin: true,
            },
            // WebSocket proxy for real-time streaming
            '/ws': {
                target: 'ws://localhost:8000',
                ws: true,
                changeOrigin: true,
            },
        },
    },
})
