import axios from 'axios';
import { useAuthStore } from '../store/authStore';
import { getDeviceFingerprint } from '../utils/deviceFingerprint';
import toast from 'react-hot-toast';

const API_BASE_URL = '/api/v1';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: true,
});

api.interceptors.request.use(
  async (config) => {
    const accessToken = useAuthStore.getState().accessToken;
    if (accessToken) {
      config.headers.Authorization = `Bearer ${accessToken}`;
    }

    // Attach device fingerprint to every request
    try {
      const deviceInfo = await getDeviceFingerprint();
      config.headers['X-Device-Fingerprint'] = deviceInfo.device_fingerprint;
      config.headers['X-Mac-Address'] = deviceInfo.mac_address || '';
      config.headers['X-OS-Info'] = deviceInfo.os_info;
      config.headers['X-Browser-Info'] = deviceInfo.browser_info;
      config.headers['X-Screen-Resolution'] = deviceInfo.screen_resolution;
      config.headers['X-Timezone-Offset'] = deviceInfo.timezone_offset;
    } catch (e) {
      console.warn("Failed to get device fingerprint", e);
    }

    return config;
  },
  (error) => Promise.reject(error)
);

let isRefreshing = false;
let failedQueue: Array<{ resolve: (token: string | null) => void; reject: (err: unknown) => void }> = [];

const processQueue = (error: any, token: string | null = null) => {
  failedQueue.forEach((prom) => {
    if (error) prom.reject(error);
    else prom.resolve(token);
  });
  failedQueue = [];
};

// Machine-readable codes the server attaches to blocking responses
// (security/middleware.py, accounts/views.py) so the client never has to
// pattern-match localized Arabic text.
const BLOCK_CODES = ['DEVICE_BLOCKED', 'IP_BLOCKED'] as const;

export const getErrorCode = (data: any): string | undefined => {
  if (!data) return undefined;
  const code = (data as any).code;
  return Array.isArray(code) ? code[0] : code;
};

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    const errorCode = getErrorCode(error.response?.data);

    if (
      error.response?.status === 403 &&
      BLOCK_CODES.includes(errorCode as any)
    ) {
      window.location.href = '/blocked';
      return Promise.reject(error);
    }

    if (
      error.response?.status === 403 &&
      (errorCode === 'ZTNA_BLOCKED' || String(error.response?.data?.error).includes('ZTNA'))
    ) {
      window.location.reload();
      return Promise.reject(error);
    }

    // A dead access token. The refresh credential is the HttpOnly cookie the
    // server set at login — the body is intentionally empty. The call goes
    // through the same `api` instance so the device-fingerprint headers the
    // refresh token is bound to (accounts/views.py client_fingerprint check)
    // are attached, and withCredentials ships the cookie.
    if (
      error.response?.status === 401 &&
      !originalRequest._retry &&
      !originalRequest._isRefresh
    ) {
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
        // `_isRefresh` marks this request so its own 401 never re-enters this
        // branch — a dead cookie must land in the catch below, not loop.
        const response = await api.post('/auth/refresh/', {}, { _isRefresh: true } as any);
        const newAccessToken = response.data.access;

        // The server rotates the refresh token and re-sets the HttpOnly cookie
        // itself; the client only keeps the new access token in memory.
        useAuthStore.getState().setAccessToken(newAccessToken);

        processQueue(null, newAccessToken);
        originalRequest.headers.Authorization = `Bearer ${newAccessToken}`;
        return api(originalRequest);
      } catch (err: any) {
        processQueue(err, null);
        useAuthStore.getState().logout();
        const detail = err?.response?.data?.detail;
        if (detail) {
          toast.error(detail, { duration: 5000 });
        } else {
          toast.error('انتهت الجلسة، يرجى تسجيل الدخول مجدداً');
        }
        // Short delay to allow the toast to be seen if possible before redirect
        setTimeout(() => {
          window.location.href = '/login';
        }, 1500);
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
  // The refresh credential is the HttpOnly cookie; the server identifies the
  // session from it, so no body is needed.
  logout: () => api.post('/auth/logout/'),
  me: () => api.get('/auth/users/me/'),
  changePassword: (data: { old_password: string; new_password: string; confirm_password: string }) =>
    api.post('/auth/users/change_password/', data),
  // Password reset (forgot password) — anonymous, no auth header needed
  requestPasswordReset: (email: string) =>
    api.post('/auth/password/reset/', { email }),
  confirmPasswordReset: (data: { uid: string; token: string; new_password: string; confirm_password: string }) =>
    api.post('/auth/password/reset/confirm/', data),
  // Biometric (WebAuthn). The server issues the challenge for both ceremonies;
  // enrollment sends a public key and login sends a signature over that challenge.
  biometricRegistrationOptions: () => api.get('/auth/biometric/enroll/'),
  enrollBiometric: (data: {
    device_id: string;
    device_name: string;
    platform: string;
    public_key: string;
    credential_id?: string;
    client_data_json?: string;
  }) => api.post('/auth/biometric/enroll/', data),
  biometricChallenge: (email: string, device_id: string) =>
    api.post('/auth/biometric/challenge/', { email, device_id }),
  biometricLogin: (data: {
    challenge_id: string;
    signature: string;
    client_data_json?: string;
    authenticator_data?: string;
  }) => api.post('/auth/biometric/login/', data),
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
  create: (note?: string, scope?: string) =>
    api.post('/backups/create_backup_action/', { note: note || '', scope: scope || 'FULL' }),
  download: (id: string) => api.get(`/backups/${id}/download/`, { responseType: 'blob' }),
  verify: (id: string) => api.get(`/backups/${id}/verify/`),
  restore: (id: string, force: boolean) => api.post(`/backups/${id}/restore/`, { force }),
  delete: (id: string) => api.delete(`/backups/${id}/`),
  deliverOffsite: (id: string) => api.post(`/backups/${id}/deliver_offsite/`),
  deliveryStatus: () => api.get('/backups/delivery_status/'),
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
  checkDevice: (data: { email?: string; device_fingerprint?: string; mac_address?: string }) =>
    api.post('/security/check-device/', data),
  // Enhanced Security features
  devices: {
    list: () => api.get('/security/devices/'),
    trust: (id: string) => api.post(`/security/devices/${id}/trust/`),
    deactivate: (id: string) => api.post(`/security/devices/${id}/deactivate/`),
  },
  // تراخيص الأجهزة (متطلب د. مجد): شاشة القفل لا تُرفع إلا للأجهزة المرخصة،
  // والتفعيل/إلغاء التفعيل مرتبط بتلجرام ولوحة التحكم معاً.
  licenses: {
    list: () => api.get('/security/licenses/'),
    issue: (deviceId: string, days?: number | null, notes?: string) =>
      api.post('/security/licenses/issue/', {
        device_id: deviceId,
        ...(days ? { days } : {}),
        notes: notes || '',
      }),
    deactivate: (id: string) => api.post(`/security/licenses/${id}/deactivate/`),
  },
  sessions: {
    list: () => api.get('/security/sessions/'),
    end: (sessionId: string) =>
      api.delete('/security/sessions/', { data: { session_id: sessionId } }),
  },
  deviceTypes: {
    list: () => api.get('/security/device-types/'),
  },
  blockedDevices: {
    list: () => api.get('/security/blocked-devices/'),
    create: (data: any) => api.post('/security/blocked-devices/', data),
    unblock: (id: string) => api.post(`/security/blocked-devices/${id}/unblock/`),
  },
  blockedIps: {
    list: () => api.get('/security/blocked-ips/'),
    create: (data: any) => api.post('/security/blocked-ips/', data),
    unblock: (id: string) => api.post(`/security/blocked-ips/${id}/unblock/`),
  },
  loginHistory: {
    list: () => api.get('/security/login-history/'),
  },
  // The caller's own registered devices ("أجهزتي") — self-service listing and
  // removal keyed by the fingerprint each request already sends. Distinct
  // from `devices` above, which is the admin-facing registry view.
  myDevices: {
    list: () => api.get('/security/my-devices/'),
    remove: (deviceFingerprint?: string) =>
      api.delete('/security/my-devices/', {
        data: deviceFingerprint ? { device_fingerprint: deviceFingerprint } : {},
      }),
  },
  // Play-mandated self-service account deletion: password re-verification on
  // the server, deactivation instead of a physical delete, every session
  // force-ended, audited as USER_DEACTIVATED.
  account: {
    delete: (password: string) => api.delete('/auth/account/', { data: { password } }),
  },
};

export const auditAPI = {
  list: (params?: any) => api.get('/audit/logs/', { params }),
  export: (params?: any) => api.get('/audit/logs/export/', { params, responseType: 'blob' }),
};

// ============== إدارة الصلاحيات (مصفوفة الأدوار × الصلاحيات) ==============
export const permissionsAPI = {
  matrix: () => api.get('/auth/permissions/'),
  set: (role: string, permission: string, allowed: boolean) =>
    api.post('/auth/permissions/set/', { role, permission, allowed }),
  reset: (role: string, permission: string) =>
    api.post('/auth/permissions/reset/', { role, permission }),
};
