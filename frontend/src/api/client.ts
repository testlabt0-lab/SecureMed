import axios from 'axios';
import { useAuthStore } from '../store/authStore';

const API_BASE_URL = '/api/v1';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: true,
});

api.interceptors.request.use(
  (config) => {
    const tokens = useAuthStore.getState().tokens;
    if (tokens?.access) {
      config.headers.Authorization = `Bearer ${tokens.access}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

let isRefreshing = false;
let failedQueue: Array<{ resolve: Function; reject: Function }> = [];

const processQueue = (error: any, token: string | null = null) => {
  failedQueue.forEach((prom) => {
    if (error) prom.reject(error);
    else prom.resolve(token);
  });
  failedQueue = [];
};

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    const tokens = useAuthStore.getState().tokens;

    if (error.response?.status === 401 && !originalRequest._retry && tokens?.refresh) {
      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject });
        })
          .then((token) => {
            originalRequest.headers.Authorization = `Bearer ${token}`;
            return api(originalRequest);
          })
          .catch((err) => Promise.reject(err));
      }

      originalRequest._retry = true;
      isRefreshing = true;

      try {
        const response = await axios.post(`${API_BASE_URL}/auth/refresh/`, {
          refresh: tokens.refresh,
        });
        const newAccessToken = response.data.access;

        useAuthStore.getState().setAuth(
          useAuthStore.getState().user!,
          { access: newAccessToken, refresh: tokens.refresh }
        );

        processQueue(null, newAccessToken);
        originalRequest.headers.Authorization = `Bearer ${newAccessToken}`;
        return api(originalRequest);
      } catch (err) {
        processQueue(err, null);
        useAuthStore.getState().logout();
        window.location.href = '/login';
        return Promise.reject(err);
      } finally {
        isRefreshing = false;
      }
    }

    return Promise.reject(error);
  }
);

export default api;

export const authAPI = {
  login: (email: string, password: string) =>
    api.post('/auth/login/', { email, password }),
  logout: (refresh: string) => api.post('/auth/logout/', { refresh }),
  refresh: (refresh: string) => api.post('/auth/refresh/', { refresh }),
  me: () => api.get('/auth/users/me/'),
  changePassword: (data: { old_password: string; new_password: string; confirm_password: string }) =>
    api.post('/auth/users/change_password/', data),
  // Password reset (forgot password) — anonymous, no auth header needed
  requestPasswordReset: (email: string) =>
    api.post('/auth/password/reset/', { email }),
  confirmPasswordReset: (data: { uid: string; token: string; new_password: string; confirm_password: string }) =>
    api.post('/auth/password/reset/confirm/', data),
  enrollBiometric: (data: { device_id: string; device_name: string; platform: string; biometric_template: string }) =>
    api.post('/auth/biometric/enroll/', data),
  biometricChallenge: (email: string, device_id: string) =>
    api.post('/auth/biometric/challenge/', { email, device_id }),
  biometricLogin: (data: { challenge_id: string; biometric_response: string; biometric_template: string }) =>
    api.post('/auth/biometric/login/', data),
};

export const usersAPI = {
  list: (params?: any) => api.get('/auth/users/', { params }),
  get: (id: string) => api.get(`/auth/users/${id}/`),
  create: (data: any) => api.post('/auth/users/', data),
  update: (id: string, data: any) => api.patch(`/auth/users/${id}/`, data),
  delete: (id: string) => api.delete(`/auth/users/${id}/`),
  deactivate: (id: string) => api.post(`/auth/users/${id}/deactivate/`),
  activate: (id: string) => api.post(`/auth/users/${id}/activate/`),
  byRole: (role: string) => api.get(`/auth/users/by_role/?role=${role}`),
};

// ============== Basins (الأحواز الصحية) ==============
export const basinsAPI = {
  list: (params?: any) => api.get('/basins/', { params }),
  get: (id: string) => api.get(`/basins/${id}/`),
  create: (data: any) => api.post('/basins/', data),
  update: (id: string, data: any) => api.patch(`/basins/${id}/`, data),
  delete: (id: string) => api.delete(`/basins/${id}/`),
  modules: () => api.get('/basins/modules/'),
  myBasin: () => api.get('/basins/my_basin/'),
  overview: () => api.get('/basins/overview/'),
  toggleModule: (id: string, module: string, enabled: boolean) =>
    api.post(`/basins/${id}/toggle_module/`, { module, enabled }),
  applyTypeDefaults: (id: string, basinType?: string) =>
    api.post(`/basins/${id}/apply_type_defaults/`, basinType ? { basin_type: basinType } : {}),
};

// ============== Backups (النسخ الاحتياطي) ==============
export const backupsAPI = {
  list: (params?: any) => api.get('/backups/', { params }),
  create: (note?: string) => api.post('/backups/create_backup_action/', { note: note || '' }),
  download: (id: string) => api.get(`/backups/${id}/download/`, { responseType: 'blob' }),
  verify: (id: string) => api.get(`/backups/${id}/verify/`),
  delete: (id: string) => api.delete(`/backups/${id}/`),
};

export const channelsAPI = {
  list: (params?: any) => api.get('/channels/', { params }),
  get: (id: string) => api.get(`/channels/${id}/`),
  create: (data: any) => api.post('/channels/', data),
  update: (id: string, data: any) => api.patch(`/channels/${id}/`, data),
  delete: (id: string) => api.delete(`/channels/${id}/`),
  members: (id: string) => api.get(`/channels/${id}/members/`),
  grantPermission: (id: string, data: any) => api.post(`/channels/${id}/grant_permission/`, data),
  modifyPermission: (id: string, data: any) => api.post(`/channels/${id}/modify_permission/`, data),
  revokePermission: (id: string, data: any) => api.post(`/channels/${id}/revoke_permission/`, data),
  removeMember: (id: string, data: any) => api.post(`/channels/${id}/remove_member/`, data),
  close: (id: string) => api.post(`/channels/${id}/close/`),
};

export const patientsAPI = {
  list: (params?: any) => api.get('/patients/', { params }),
  get: (id: string) => api.get(`/patients/${id}/`),
  create: (data: any) => api.post('/patients/', data),
  update: (id: string, data: any) => api.patch(`/patients/${id}/`, data),
  channels: (id: string) => api.get(`/patients/${id}/channels/`),
  records: (params?: any) => api.get('/patients/records/', { params }),
  createRecord: (data: any) => api.post('/patients/records/', data),
  files: (params?: any) => api.get('/patients/files/', { params }),
  uploadFile: (data: FormData) => api.post('/patients/files/', data, {
    headers: { 'Content-Type': 'multipart/form-data' },
  }),
  downloadFile: (id: string) => api.get(`/patients/files/${id}/download/`, { responseType: 'blob' }),
  filesByChannel: (channelId: string) => api.get(`/patients/files/by_channel/?channel_id=${channelId}`),
};

export const securityAPI = {
  portScan: (data: { target?: string; ports?: number[] }) =>
    api.post('/security/port-scanner/', data),
  vulnScan: () => api.post('/security/vulnerability-scanner/'),
  dashboard: () => api.get('/security/dashboard/'),
  stats: () => api.get('/security/stats/'),
  activity: () => api.get('/security/activity/'),
};

export const auditAPI = {
  list: (params?: any) => api.get('/audit/logs/', { params }),
};
