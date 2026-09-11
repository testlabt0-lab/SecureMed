import { Suspense, lazy } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import Layout from './components/Layout';
import ProtectedRoute from './components/ProtectedRoute';
import {
  ADMIN_ROLES, CARE_TEAM_ROLES, OVERSIGHT_ROLES, REPORTING_ROLES,
  REPORT_EXPORT_ROLES, PHARMACY_ROLES, BILLING_ROLES, LAB_ROLES, WARD_ROLES,
  TELEMEDICINE_ROLES, PLATFORM_OWNER_ROLES, PERMISSIONS_MANAGER_ROLES,
} from './constants/roles';

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
const PermissionsManagement = lazy(() => import('./pages/Permissions'));
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
          <Route path="/channels" element={<ProtectedRoute requiredRole={CARE_TEAM_ROLES}><Channels /></ProtectedRoute>} />
          <Route path="/channels/:id" element={<ProtectedRoute requiredRole={CARE_TEAM_ROLES}><ChannelDetail /></ProtectedRoute>} />
          <Route path="/patients" element={<ProtectedRoute requiredRole={CARE_TEAM_ROLES}><Patients /></ProtectedRoute>} />
          <Route path="/patients/:id" element={<ProtectedRoute requiredRole={CARE_TEAM_ROLES}><PatientProfile /></ProtectedRoute>} />

          <Route path="/security" element={<ProtectedRoute requiredRole={OVERSIGHT_ROLES}><SecurityDashboard /></ProtectedRoute>} />
          <Route path="/security/devices" element={<ProtectedRoute requiredRole={OVERSIGHT_ROLES}><DeviceManagement /></ProtectedRoute>} />
          <Route path="/security/permissions" element={<ProtectedRoute requiredRole={PERMISSIONS_MANAGER_ROLES}><PermissionsManagement /></ProtectedRoute>} />
          <Route path="/security/login-history" element={<ProtectedRoute requiredRole={OVERSIGHT_ROLES}><LoginHistory /></ProtectedRoute>} />
          {/* Self-service: every signed-in user manages their own password, 2FA and
              biometrics here, so this route is deliberately role-free — the outer
              ProtectedRoute still requires authentication. */}
          <Route path="/security/settings" element={<SecuritySettings />} />
          <Route path="/audit" element={<ProtectedRoute requiredRole={OVERSIGHT_ROLES}><AuditLogs /></ProtectedRoute>} />
          <Route path="/users" element={<ProtectedRoute requiredRole={ADMIN_ROLES}><Users /></ProtectedRoute>} />
          <Route path="/basins" element={<ProtectedRoute requiredRole={ADMIN_ROLES}><Basins /></ProtectedRoute>} />
          <Route path="/backups" element={<ProtectedRoute requiredRole={PLATFORM_OWNER_ROLES}><Backups /></ProtectedRoute>} />

          <Route path="/profile" element={<Profile />} />
          <Route path="/analytics" element={<ProtectedRoute requiredRole={REPORTING_ROLES}><AnalyticsDashboard /></ProtectedRoute>} />
          <Route path="/notifications" element={<NotificationsCenter />} />
          <Route path="/appointments" element={<Appointments />} />
          <Route path="/reports" element={<ProtectedRoute requiredRole={REPORT_EXPORT_ROLES}><Reports /></ProtectedRoute>} />
          <Route path="/telemedicine" element={<ProtectedRoute requiredRole={TELEMEDICINE_ROLES}><Telemedicine /></ProtectedRoute>} />
          <Route path="/pharmacy" element={<ProtectedRoute requiredRole={PHARMACY_ROLES}><PharmacyDashboard /></ProtectedRoute>} />
          <Route path="/billing" element={<ProtectedRoute requiredRole={BILLING_ROLES}><BillingDashboard /></ProtectedRoute>} />
          <Route path="/lab" element={<ProtectedRoute requiredRole={LAB_ROLES}><LabDashboard /></ProtectedRoute>} />
          <Route path="/wards" element={<ProtectedRoute requiredRole={WARD_ROLES}><WardManagement /></ProtectedRoute>} />
          <Route path="/settings" element={<SettingsPage />} />
        </Route>

        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Routes>
    </Suspense>
  );
}

export default App;
