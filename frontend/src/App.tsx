import { Suspense, lazy } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { useAuthStore } from './store/authStore';
import Layout from './components/Layout';
import ProtectedRoute from './components/ProtectedRoute';

// Lazy load pages
const Login = lazy(() => import('./pages/Login'));
const Blocked = lazy(() => import('./pages/Blocked'));
const ForgotPassword = lazy(() => import('./pages/ForgotPassword'));
const Dashboard = lazy(() => import('./pages/Dashboard'));
const Channels = lazy(() => import('./pages/Channels'));
const ChannelDetail = lazy(() => import('./pages/ChannelDetail'));
const Patients = lazy(() => import('./pages/Patients'));
const PatientProfile = lazy(() => import('./pages/PatientProfile'));
const SecurityDashboard = lazy(() => import('./pages/SecurityDashboard'));
const AuditLogs = lazy(() => import('./pages/AuditLogs'));
const Users = lazy(() => import('./pages/Users'));
const Basins = lazy(() => import('./pages/Basins'));
const Backups = lazy(() => import('./pages/Backups'));
const Profile = lazy(() => import('./pages/Profile'));
const AnalyticsDashboard = lazy(() => import('./pages/AnalyticsDashboard'));
const NotificationsCenter = lazy(() => import('./pages/NotificationsCenter'));
const Appointments = lazy(() => import('./pages/Appointments'));
const Reports = lazy(() => import('./pages/Reports'));
const SettingsPage = lazy(() => import('./pages/SettingsPage'));
const DeviceManagement = lazy(() => import('./pages/DeviceManagement').then(m => ({ default: m.DeviceManagement })));
const LoginHistory = lazy(() => import('./pages/LoginHistory').then(m => ({ default: m.LoginHistory })));
const SecuritySettings = lazy(() => import('./pages/SecuritySettings').then(m => ({ default: m.SecuritySettings })));
const PharmacyDashboard = lazy(() => import('./pages/PharmacyDashboard'));
const BillingDashboard = lazy(() => import('./pages/BillingDashboard'));
const LabDashboard = lazy(() => import('./pages/LabDashboard'));
const WardManagement = lazy(() => import('./pages/WardManagement'));
const Telemedicine = lazy(() => import('./pages/Telemedicine'));

// Loading fallback component
const PageLoader = () => (
  <div className="flex h-screen w-full items-center justify-center bg-gray-50 dark:bg-gray-900">
    <div className="h-10 w-10 animate-spin rounded-full border-4 border-indigo-600 border-t-transparent"></div>
  </div>
);

function App() {
  return (
    <Suspense fallback={<PageLoader />}>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/blocked" element={<Blocked />} />
        <Route path="/forgot-password" element={<ForgotPassword />} />

        <Route
          element={
            <ProtectedRoute>
              <Layout />
            </ProtectedRoute>
          }
        >
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/channels" element={<ProtectedRoute requiredRole={['SUPER_ADMIN', 'HOSPITAL_ADMIN', 'CENTER_ADMIN', 'DOCTOR', 'NURSE', 'RECEPTIONIST']}><Channels /></ProtectedRoute>} />
          <Route path="/channels/:id" element={<ProtectedRoute requiredRole={['SUPER_ADMIN', 'HOSPITAL_ADMIN', 'CENTER_ADMIN', 'DOCTOR', 'NURSE', 'RECEPTIONIST']}><ChannelDetail /></ProtectedRoute>} />
          <Route path="/patients" element={<ProtectedRoute requiredRole={['SUPER_ADMIN', 'HOSPITAL_ADMIN', 'CENTER_ADMIN', 'DOCTOR', 'NURSE', 'RECEPTIONIST']}><Patients /></ProtectedRoute>} />
          <Route path="/patients/:id" element={<ProtectedRoute requiredRole={['SUPER_ADMIN', 'HOSPITAL_ADMIN', 'CENTER_ADMIN', 'DOCTOR', 'NURSE', 'RECEPTIONIST']}><PatientProfile /></ProtectedRoute>} />
          
          <Route path="/security" element={<ProtectedRoute requiredRole={['SUPER_ADMIN', 'HOSPITAL_ADMIN', 'CENTER_ADMIN', 'AUDITOR']}><SecurityDashboard /></ProtectedRoute>} />
          <Route path="/security/devices" element={<ProtectedRoute requiredRole={['SUPER_ADMIN', 'HOSPITAL_ADMIN', 'CENTER_ADMIN', 'AUDITOR']}><DeviceManagement /></ProtectedRoute>} />
          <Route path="/security/login-history" element={<ProtectedRoute requiredRole={['SUPER_ADMIN', 'HOSPITAL_ADMIN', 'CENTER_ADMIN', 'AUDITOR']}><LoginHistory /></ProtectedRoute>} />
          <Route path="/security/settings" element={<SecuritySettings />} />
          <Route path="/audit" element={<ProtectedRoute requiredRole={['SUPER_ADMIN', 'HOSPITAL_ADMIN', 'CENTER_ADMIN', 'AUDITOR']}><AuditLogs /></ProtectedRoute>} />
          <Route path="/users" element={<ProtectedRoute requiredRole={['SUPER_ADMIN', 'HOSPITAL_ADMIN', 'CENTER_ADMIN']}><Users /></ProtectedRoute>} />
          <Route path="/basins" element={<ProtectedRoute requiredRole={['SUPER_ADMIN', 'HOSPITAL_ADMIN', 'CENTER_ADMIN']}><Basins /></ProtectedRoute>} />
          <Route path="/backups" element={<ProtectedRoute requiredRole={['SUPER_ADMIN']}><Backups /></ProtectedRoute>} />
          
          <Route path="/profile" element={<Profile />} />
          <Route path="/analytics" element={<ProtectedRoute requiredRole={['SUPER_ADMIN', 'HOSPITAL_ADMIN', 'CENTER_ADMIN', 'AUDITOR', 'DOCTOR', 'ACCOUNTANT']}><AnalyticsDashboard /></ProtectedRoute>} />
          <Route path="/notifications" element={<NotificationsCenter />} />
          <Route path="/appointments" element={<Appointments />} />
          <Route path="/reports" element={<ProtectedRoute requiredRole={['SUPER_ADMIN', 'HOSPITAL_ADMIN', 'CENTER_ADMIN', 'AUDITOR', 'DOCTOR', 'ACCOUNTANT']}><Reports /></ProtectedRoute>} />
          <Route path="/telemedicine" element={<ProtectedRoute requiredRole={['SUPER_ADMIN', 'HOSPITAL_ADMIN', 'CENTER_ADMIN', 'DOCTOR']}><Telemedicine /></ProtectedRoute>} />
          <Route path="/pharmacy" element={<ProtectedRoute requiredRole={['SUPER_ADMIN', 'HOSPITAL_ADMIN', 'CENTER_ADMIN', 'PHARMACIST', 'DOCTOR']}><PharmacyDashboard /></ProtectedRoute>} />
          <Route path="/billing" element={<ProtectedRoute requiredRole={['SUPER_ADMIN', 'HOSPITAL_ADMIN', 'CENTER_ADMIN', 'AUDITOR', 'ACCOUNTANT', 'RECEPTIONIST']}><BillingDashboard /></ProtectedRoute>} />
          <Route path="/lab" element={<ProtectedRoute requiredRole={['SUPER_ADMIN', 'HOSPITAL_ADMIN', 'CENTER_ADMIN', 'LAB_TECH', 'DOCTOR']}><LabDashboard /></ProtectedRoute>} />
          <Route path="/wards" element={<ProtectedRoute requiredRole={['SUPER_ADMIN', 'HOSPITAL_ADMIN', 'CENTER_ADMIN', 'NURSE', 'DOCTOR']}><WardManagement /></ProtectedRoute>} />
          <Route path="/settings" element={<SettingsPage />} />
        </Route>

        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Routes>
    </Suspense>
  );
}

export default App;
