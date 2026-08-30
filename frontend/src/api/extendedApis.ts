import api from './client';
import axios from 'axios';

// ============== Notifications API ==============
export const notificationsApi = {
  list: (params?: any) => api.get('/notifications/', { params }),
  unreadCount: () => api.get('/notifications/unread_count/'),
  markAllRead: () => api.post('/notifications/mark_all_read/'),
  markRead: (id: string) => api.post(`/notifications/${id}/mark_read/`),
  dismiss: (id: string) => api.delete(`/notifications/${id}/dismiss/`),
  preferences: () => api.get('/notifications/preferences/'),
  updatePreferences: (data: any) => api.patch('/notifications/preferences/', data),
  testEmail: () => api.post('/notifications/test_email/'),
};

// ============== Analytics API ==============
export const analyticsApi = {
  overview: () => api.get('/analytics/dashboard/overview/'),
  security: () => api.get('/analytics/dashboard/security/'),
  activityFeed: (limit?: number) =>
    api.get('/analytics/dashboard/activity_feed/', { params: { limit } }),
  activities: (params?: any) => api.get('/analytics/activities/', { params }),
  metrics: (params?: any) => api.get('/analytics/metrics/', { params }),
};

// ============== Medical Files API ==============
export const medicalFilesApi = {
  list: (params?: any) => api.get('/patients/files/', { params }),
  get: (id: string) => api.get(`/patients/files/${id}/`),
  upload: (formData: FormData) =>
    api.post('/patients/files/', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }),
  download: (id: string) =>
    api.get(`/patients/files/${id}/download/`, { responseType: 'blob' }),
  delete: (id: string) => api.delete(`/patients/files/${id}/`),
};

// ============== Channel Chat API ==============
export const chatApi = {
  list: (channelId: string, params?: any) =>
    api.get(`/channels/${channelId}/messages/`, { params }),
  send: (channelId: string, body: string) =>
    api.post(`/channels/${channelId}/messages/`, { body }),
};

// ============== Patient Profile API ==============
export const patientsExtendedApi = {
  profile: (id: string) => api.get(`/patients/${id}/profile/`),
  aiSummary: (id: string) => api.post(`/patients/${id}/ai-summary/`),
};

// ============== Global Search API ==============
export const searchApi = {
  query: (q: string) => api.get('/auth/search/', { params: { q } }),
};

// ============== Two-Factor Authentication API ==============
export const mfaApi = {
  status: () => api.get('/auth/2fa/status/'),
  setup: () => api.post('/auth/2fa/setup/'),
  verify: (code: string) => api.post('/auth/2fa/verify/', { code }),
  disable: (code: string) => api.post('/auth/2fa/disable/', { code }),
  login: (mfa_token: string, code: string) =>
    api.post('/auth/2fa/login/', { mfa_token, code }),
};

// ============== Biometric Devices API ==============
export const biometricDevicesApi = {
  list: () => api.get('/auth/biometric-profiles/'),
  revoke: (id: string) => api.post(`/auth/biometric-profiles/${id}/revoke/`),
  remove: (id: string) => api.delete(`/auth/biometric-profiles/${id}/remove/`),
};

// ============== Reports API (binary downloads) ==============
export const reportsApi = {
  channelPdf: (channelId: string) =>
    api.get(`/reports/channel/${channelId}/pdf/`, { responseType: 'blob' }),
  auditExcel: (params?: any) =>
    api.get('/reports/audit/excel/', { responseType: 'blob', params }),
  monthlyPdf: (month?: string) =>
    api.get('/reports/monthly/pdf/', { responseType: 'blob', params: month ? { month } : {} }),
  emailMonthly: (month?: string) =>
    api.post('/reports/monthly/email/', month ? { month } : {}),
};

/** Trigger a browser download from an axios blob response. */
export function downloadBlobResponse(
  response: { data: Blob; headers: any },
  fallbackName: string,
) {
  const disposition: string = response.headers?.['content-disposition'] || '';
  const match = disposition.match(/filename="?([^";]+)"?/);
  const filename = match ? match[1] : fallbackName;
  const url = URL.createObjectURL(response.data);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

// ============== AI Smart Assistant API ==============
// Dedicated axios instance: the AI microservice runs on :8100 and is
// exposed through the Vite dev-server proxy at /ai (same-origin).
const aiClient = axios.create({ baseURL: '/ai', timeout: 90000 });

export const aiApi = {
  ask: (
    question: string,
    context?: any,
    history?: Array<{ role: 'user' | 'assistant'; content: string }>,
  ) => aiClient.post('/ask', { question, context, history }),
  health: () => aiClient.get('/health'),
};

