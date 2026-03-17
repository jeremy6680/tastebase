// src/api/client.js — Axios instance configured for TasteBase FastAPI backend
import axios from 'axios'

const apiClient = axios.create({
    // In dev, Vite proxies /api → http://localhost:8000
    // In production, set VITE_API_BASE_URL in .env
    baseURL: import.meta.env.VITE_API_BASE_URL || '/api',
    timeout: 10_000,
    headers: {
        'Content-Type': 'application/json',
        Accept: 'application/json',
    },
})

// Response interceptor — normalize error shape
apiClient.interceptors.response.use(
    (response) => response.data,
    (error) => {
        const message =
            error.response?.data?.detail ||
            error.response?.data?.message ||
            error.message ||
            'Unknown error'
        return Promise.reject(new Error(message))
    }
)

export default apiClient