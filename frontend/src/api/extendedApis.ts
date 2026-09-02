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

// ============== Reports API (binary downloads — legacy) ==============
export const reportsApi = {
  channelPdf: (channelId: string) =>
    api.get(`/reports/channel/${channelId}/pdf/`, { responseType: 'blob' }),
  auditExcel: (params?: any) =>
    api.get('/reports/audit/excel/', { responseType: 'blob', params }),
  auditJson: (params?: any) =>
    api.get('/audit/export/', { responseType: 'blob', params }),
  monthlyPdf: (month?: string) =>
    api.get('/reports/monthly/pdf/', { responseType: 'blob', params: month ? { month } : {} }),
  emailMonthly: (month?: string) =>
    api.post('/reports/monthly/email/', month ? { month } : {}),
};

// ============== Extended Reports API (unified) ==============
export const reportsAPI = {
  download: (reportId: string, format: 'pdf' | 'excel', startDate: string, endDate: string) =>
    api.get(`/reports/${reportId}/`, {
      responseType: 'blob',
      params: { format, start_date: startDate, end_date: endDate },
    }),
  list: () => api.get('/reports/list/'),
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

// ============== AI API ==============
export const aiApi = {
  ask: (
    question: string,
    context?: any,
    history?: Array<{ role: 'user' | 'assistant'; content: string }>,
  ) => api.post('/appointments/ai/ask/', { question, context, history }),
  health: () => api.get('/appointments/ai/health/'),
};

// ============== Appointments API ==============
export const appointmentsAPI = {
  list: (params?: any) => api.get('/appointments/', { params }),
  get: (id: string) => api.get(`/appointments/${id}/`),
  create: (data: any) => api.post('/appointments/', data),
  update: (id: string, data: any) => api.patch(`/appointments/${id}/`, data),
  delete: (id: string) => api.delete(`/appointments/${id}/`),
  calendar: (start: string, end: string) =>
    api.get('/appointments/calendar/', { params: { start, end } }),
  today: () => api.get('/appointments/today/'),
  upcoming: () => api.get('/appointments/upcoming/'),
  stats: () => api.get('/appointments/stats/'),
  confirm: (id: string) => api.post(`/appointments/${id}/confirm/`),
  start: (id: string) => api.post(`/appointments/${id}/start/`),
  complete: (id: string, data: { summary?: string; follow_up_needed?: boolean; follow_up_date?: string }) =>
    api.post(`/appointments/${id}/complete/`, data),
  cancel: (id: string, data: { reason?: string }) =>
    api.post(`/appointments/${id}/cancel/`, data),
  noShow: (id: string) => api.post(`/appointments/${id}/no-show/`),
  doctorAvailability: (doctorId: string, date: string) =>
    api.get('/appointments/doctor-availability/', { params: { doctor_id: doctorId, date } }),
  slots: (params?: any) => api.get('/appointments/slots/', { params }),
  createSlot: (data: any) => api.post('/appointments/slots/', data),
  updateSlot: (id: string, data: any) => api.patch(`/appointments/slots/${id}/`, data),
  deleteSlot: (id: string) => api.delete(`/appointments/slots/${id}/`),
};

// ============== Settings API ==============
export const settingsAPI = {
  totpStatus: () => api.get('/auth/2fa/status/'),
  totpSetup: () => api.post('/auth/2fa/setup/'),
  totpVerify: (code: string) => api.post('/auth/2fa/verify/', { code }),
  totpDisable: (code: string) => api.post('/auth/2fa/disable/', { code }),
  sessions: () => api.get('/auth/sessions/'),
  revokeSession: (sessionId: string) => api.post(`/auth/sessions/${sessionId}/revoke/`),
  revokeAllSessions: () => api.post('/auth/sessions/revoke_all/'),
  notificationPrefs: () => api.get('/notifications/preferences/'),
  updateNotificationPrefs: (data: any) => api.patch('/notifications/preferences/', data),
};

// ============== Pharmacy API ==============
export const pharmacyAPI = {
  // Medications
  medications: (params?: any) => api.get('/pharmacy/medications/', { params }),
  getMedication: (id: string) => api.get(`/pharmacy/medications/${id}/`),
  createMedication: (data: any) => api.post('/pharmacy/medications/', data),
  updateMedication: (id: string, data: any) => api.patch(`/pharmacy/medications/${id}/`, data),
  deleteMedication: (id: string) => api.delete(`/pharmacy/medications/${id}/`),
  lowStock: () => api.get('/pharmacy/medications/low_stock/'),
  expired: () => api.get('/pharmacy/medications/expired/'),
  expiringSoon: () => api.get('/pharmacy/medications/expiring_soon/'),
  adjustStock: (id: string, data: any) => api.post(`/pharmacy/medications/${id}/adjust_stock/`, data),

  // Prescriptions
  prescriptions: (params?: any) => api.get('/pharmacy/prescriptions/', { params }),
  getPrescription: (id: string) => api.get(`/pharmacy/prescriptions/${id}/`),
  createPrescription: (data: any) => api.post('/pharmacy/prescriptions/', data),
  dispensePrescription: (id: string, data?: any) => api.post(`/pharmacy/prescriptions/${id}/dispense/`, data || {}),
  cancelPrescription: (id: string) => api.post(`/pharmacy/prescriptions/${id}/cancel/`),

  // Drug Interactions
  interactions: () => api.get('/pharmacy/interactions/'),
  checkInteractions: (medicationIds: string[]) => api.post('/pharmacy/interactions/check/', { medication_ids: medicationIds }),

  // Stats
  stats: () => api.get('/pharmacy/stats/'),
};

// ============== Billing API ==============
export const billingAPI = {
  // Invoices
  invoices: (params?: any) => api.get('/billing/invoices/', { params }),
  getInvoice: (id: string) => api.get(`/billing/invoices/${id}/`),
  createInvoice: (data: any) => api.post('/billing/invoices/', data),
  payInvoice: (id: string, data: any) => api.post(`/billing/invoices/${id}/pay/`, data),
  cancelInvoice: (id: string) => api.post(`/billing/invoices/${id}/cancel/`),

  // Insurance
  insuranceProviders: () => api.get('/billing/insurance-providers/'),
  createInsuranceProvider: (data: any) => api.post('/billing/insurance-providers/', data),
  patientInsurance: (params?: any) => api.get('/billing/patient-insurance/', { params }),
  createPatientInsurance: (data: any) => api.post('/billing/patient-insurance/', data),

  // Stats
  stats: () => api.get('/billing/stats/'),
};

// ============== Lab API ==============
export const labAPI = {
  // Tests
  tests: (params?: any) => api.get('/lab/tests/', { params }),
  getTest: (id: string) => api.get(`/lab/tests/${id}/`),
  createTest: (data: any) => api.post('/lab/tests/', data),
  
  // Orders
  orders: (params?: any) => api.get('/lab/orders/', { params }),
  getOrder: (id: string) => api.get(`/lab/orders/${id}/`),
  createOrder: (data: any) => api.post('/lab/orders/', data),
  collectSample: (id: string) => api.post(`/lab/orders/${id}/collect_sample/`),
  startProcessing: (id: string) => api.post(`/lab/orders/${id}/start_processing/`),
  cancelOrder: (id: string) => api.post(`/lab/orders/${id}/cancel/`),
  
  // Results
  results: (params?: any) => api.get('/lab/results/', { params }),
  createResult: (data: any) => api.post('/lab/results/', data),
  validateResult: (id: string) => api.post(`/lab/results/${id}/validate/`),
  criticalResults: () => api.get('/lab/results/critical/'),
  abnormalResults: () => api.get('/lab/results/abnormal/'),
  
  // Stats
  stats: () => api.get('/lab/stats/'),
};

// ============== Wards API ==============
export const wardsAPI = {
  // Wards
  wards: () => api.get('/wards/wards/'),
  createWard: (data: any) => api.post('/wards/wards/', data),
  updateWard: (id: string, data: any) => api.patch(`/wards/wards/${id}/`, data),
  
  // Rooms
  rooms: (wardId?: string) => api.get('/wards/rooms/', { params: { ward: wardId } }),
  createRoom: (data: any) => api.post('/wards/rooms/', data),
  
  // Beds
  beds: (wardId?: string, status?: string) => api.get('/wards/beds/', { params: { ward: wardId, status } }),
  createBed: (data: any) => api.post('/wards/beds/', data),
  changeBedStatus: (id: string, status: string) => api.post(`/wards/beds/${id}/change_status/`, { status }),
  
  // Assignments (Admissions)
  assignments: (activeOnly: boolean = true) => api.get('/wards/assignments/', { params: { active: activeOnly } }),
  createAssignment: (data: any) => api.post('/wards/assignments/', data),
  discharge: (id: string) => api.post(`/wards/assignments/${id}/discharge/`),
  
  // Stats
  stats: () => api.get('/wards/stats/'),
};

// ============== Telemedicine API ==============
export const telemedicineAPI = {
  consultations: (params?: any) => api.get('/telemedicine/consultations/', { params }),
  getConsultation: (id: string) => api.get(`/telemedicine/consultations/${id}/`),
  createConsultation: (data: any) => api.post('/telemedicine/consultations/', data),
  joinConsultation: (id: string) => api.post(`/telemedicine/consultations/${id}/join/`),
  completeConsultation: (id: string, data?: any) => api.post(`/telemedicine/consultations/${id}/complete/`, data || {}),
  
  messages: (consultationId: string) => api.get('/telemedicine/messages/', { params: { consultation: consultationId } }),
  sendMessage: (data: any) => api.post('/telemedicine/messages/', data),
};
