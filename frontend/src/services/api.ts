import axios from 'axios';

const API_BASE = '/api/v1';

const api = axios.create({
  baseURL: API_BASE,
  headers: { 'Content-Type': 'application/json' },
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export const auth = {
  login: (username: string, password: string) =>
    api.post('/auth/login', { username, password }),
  register: (username: string, email: string, password: string) =>
    api.post('/auth/register', { username, email, password }),
};

export const signals = {
  list: (params?: { limit?: number; direction?: string; min_confidence?: number }) =>
    api.get('/signals/', { params }),
  active: () => api.get('/signals/active'),
  get: (id: string) => api.get(`/signals/${id}`),
};

export const trades = {
  list: (params?: { limit?: number; status?: string; symbol?: string }) =>
    api.get('/trades/', { params }),
  open: () => api.get('/trades/open'),
  get: (id: string) => api.get(`/trades/${id}`),
};

export const scanner = {
  scan: (exchange = 'BINANCE', limit = 30) =>
    api.get('/scanner/scan', { params: { exchange, limit } }),
  pairs: (exchange = 'BINANCE') =>
    api.get('/scanner/pairs', { params: { exchange } }),
};

export const backtest = {
  run: (data: { symbol: string; exchange?: string; initial_capital?: number }) =>
    api.post('/backtest/run', data),
  history: (limit = 20) => api.get('/backtest/history', { params: { limit } }),
  get: (id: string) => api.get(`/backtest/${id}`),
};

export const risk = {
  metrics: () => api.get('/risk/metrics'),
};

export default api;
