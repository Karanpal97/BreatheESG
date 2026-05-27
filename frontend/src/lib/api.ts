import axios from 'axios';

const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api',
  headers: { 'Content-Type': 'application/json' },
});

api.interceptors.request.use((config) => {
  if (typeof window !== 'undefined') {
    const token = localStorage.getItem('auth_token');
    if (token) config.headers.Authorization = `Token ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401 && typeof window !== 'undefined') {
      localStorage.removeItem('auth_token');
      localStorage.removeItem('auth_user');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// Auth
export const login = (email: string, password: string) =>
  api.post('/auth/login/', { email, password });
export const logout = () => api.post('/auth/logout/');
export const getMe = () => api.get('/auth/me/');

// Dashboard
export const getDashboard = () => api.get('/dashboard/');

// Jobs
export const getJobs = (params?: Record<string, string>) =>
  api.get('/jobs/', { params });
export const getJob = (id: string) => api.get(`/jobs/${id}/`);
export const getJobRows = (id: string, params?: Record<string, string>) =>
  api.get(`/jobs/${id}/rows/`, { params });
export const uploadFile = (formData: FormData) =>
  api.post('/jobs/upload/', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });

// Records
export const getRecords = (params?: Record<string, string>) =>
  api.get('/records/', { params });
export const getRecord = (id: string) => api.get(`/records/${id}/`);
export const patchRecord = (id: string, data: Record<string, unknown>) =>
  api.patch(`/records/${id}/`, data);
export const approveRecord = (id: string, note?: string) =>
  api.post(`/records/${id}/approve/`, { note });
export const rejectRecord = (id: string, note: string) =>
  api.post(`/records/${id}/reject/`, { note });
export const bulkApprove = (ids: string[], note?: string) =>
  api.post('/records/bulk-approve/', { ids, note });
export const getAuditLog = (id: string) => api.get(`/records/${id}/audit/`);

export default api;
