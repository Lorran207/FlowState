import axios, { AxiosError, InternalAxiosRequestConfig } from 'axios';
import type { Token } from '../types';

export const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

let accessToken: string | null = localStorage.getItem('access_token');
let refreshToken: string | null = localStorage.getItem('refresh_token');

export const setTokens = (tokens: Token) => {
  accessToken = tokens.access_token;
  refreshToken = tokens.refresh_token;
  localStorage.setItem('access_token', tokens.access_token);
  localStorage.setItem('refresh_token', tokens.refresh_token);
};

export const clearTokens = () => {
  accessToken = null;
  refreshToken = null;
  localStorage.removeItem('access_token');
  localStorage.removeItem('refresh_token');
};

api.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  if (accessToken) {
    config.headers.Authorization = `Bearer ${accessToken}`;
  }
  return config;
});

let isRefreshing = false;
let failedQueue: Array<{
  resolve: (value: string) => void;
  reject: (reason: Error) => void;
}> = [];

const processQueue = (error: Error | null, token: string | null = null) => {
  failedQueue.forEach((prom) => {
    if (error) {
      prom.reject(error);
    } else {
      prom.resolve(token!);
    }
  });
  failedQueue = [];
};

api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & { _retry?: boolean };

    if (error.response?.status === 401 && !originalRequest._retry && refreshToken) {
      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject });
        }).then((token) => {
          originalRequest.headers.Authorization = `Bearer ${token}`;
          return api(originalRequest);
        }).catch((err) => {
          return Promise.reject(err);
        });
      }

      originalRequest._retry = true;
      isRefreshing = true;

      try {
        const response = await axios.post(`${API_URL}/auth/refresh`, null, {
          params: { refresh_token: refreshToken },
        });
        const { access_token, refresh_token } = response.data;
        setTokens({ access_token, refresh_token, token_type: 'bearer' });
        processQueue(null, access_token);
        originalRequest.headers.Authorization = `Bearer ${access_token}`;
        return api(originalRequest);
      } catch (err) {
        processQueue(err as Error, null);
        clearTokens();
        window.location.href = '/login';
        return Promise.reject(err);
      } finally {
        isRefreshing = false;
      }
    }

    return Promise.reject(error);
  }
);

export const authApi = {
  register: (email: string, name: string, password: string) =>
    api.post('/auth/register', { email, name, password }),
  login: (email: string, password: string) =>
    api.post('/auth/login', { email, password }),
  refresh: (refresh_token: string) =>
    api.post('/auth/refresh', null, { params: { refresh_token } }),
  me: () => api.get('/auth/me'),
};

export const tasksApi = {
  list: () => api.get('/tasks'),
  create: (data: { title: string; description?: string }) => api.post('/tasks', data),
  get: (id: number) => api.get(`/tasks/${id}`),
  update: (id: number, data: Partial<{ title: string; description: string | null; status: string; position: number }>) =>
    api.patch(`/tasks/${id}`, data),
  delete: (id: number) => api.delete(`/tasks/${id}`),
  reorder: (status: string, task_ids: number[]) => api.post(`/tasks/reorder/${status}`, task_ids),
};

export const sessionsApi = {
  list: (limit = 10) => api.get('/sessions', { params: { limit } }),
  start: (data: { task_id?: number }) => api.post('/sessions', data),
  complete: (id: number, duration_min: number) => api.post(`/sessions/${id}/complete`, { duration_min }),
};

export const journalApi = {
  create: (data: { session_id: number; content: string }) => api.post('/journal', data),
};

export const dashboardApi = {
  get: () => api.get('/dashboard'),
};

export const githubApi = {
  status: () => api.get('/github/status'),
  sync: () => api.post('/github/sync'),
  disconnect: () => api.delete('/github/disconnect'),
  commits: (limit = 10) => api.get('/github/commits', { params: { limit } }),
  authorizeUrl: (accessToken?: string | null) => {
    const params = accessToken ? `?t=${encodeURIComponent(accessToken)}` : '';
    return `${API_URL}/auth/github/authorize${params}`;
  },
};

export const activityApi = {
  feed: (days = 14, limit = 50) => api.get('/activity/feed', { params: { days, limit } }),
  heatmap: (days = 182) => api.get('/activity/heatmap', { params: { days } }),
};

export default api;