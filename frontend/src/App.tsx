import { Routes, Route, Navigate } from 'react-router-dom';
import { useAuthStore } from './store/authStore';
import Login from './pages/Login';
import ForgotPassword from './pages/ForgotPassword';
import Dashboard from './pages/Dashboard';
import Channels from './pages/Channels';
import ChannelDetail from './pages/ChannelDetail';
import Patients from './pages/Patients';
import PatientProfile from './pages/PatientProfile';
import SecurityDashboard from './pages/SecurityDashboard';
import AuditLogs from './pages/AuditLogs';
import Users from './pages/Users';
import Basins from './pages/Basins';
import Backups from './pages/Backups';
import Profile from './pages/Profile';
import AnalyticsDashboard from './pages/AnalyticsDashboard';
import NotificationsCenter from './pages/NotificationsCenter';
import Appointments from './pages/Appointments';
import Reports from './pages/Reports';
import SettingsPage from './pages/SettingsPage';
import { DeviceManagement } from './pages/DeviceManagement';
import { LoginHistory } from './pages/LoginHistory';
import { SecuritySettings } from './pages/SecuritySettings';
import PharmacyDashboard from './pages/PharmacyDashboard';
import BillingDashboard from './pages/BillingDashboard';
import LabDashboard from './pages/LabDashboard';
import WardManagement from './pages/WardManagement';
import Telemedicine from './pages/Telemedicine';
import Layout from './components/Layout';
import ProtectedRoute from './components/ProtectedRoute';

function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
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
        <Route path="/channels" element={<Channels />} />
        <Route path="/channels/:id" element={<ChannelDetail />} />
        <Route path="/patients" element={<Patients />} />
        <Route path="/patients/:id" element={<PatientProfile />} />
        <Route path="/security" element={<SecurityDashboard />} />
        <Route path="/security/devices" element={<DeviceManagement />} />
        <Route path="/security/login-history" element={<LoginHistory />} />
        <Route path="/security/settings" element={<SecuritySettings />} />
        <Route path="/audit" element={<AuditLogs />} />
        <Route path="/users" element={<Users />} />
        <Route path="/basins" element={<Basins />} />
        <Route path="/backups" element={<Backups />} />
        <Route path="/profile" element={<Profile />} />
        <Route path="/analytics" element={<AnalyticsDashboard />} />
        <Route path="/notifications" element={<NotificationsCenter />} />
        <Route path="/appointments" element={<Appointments />} />
        <Route path="/reports" element={<Reports />} />
        <Route path="/telemedicine" element={<Telemedicine />} />
        <Route path="/pharmacy" element={<PharmacyDashboard />} />
        <Route path="/billing" element={<BillingDashboard />} />
        <Route path="/lab" element={<LabDashboard />} />
        <Route path="/wards" element={<WardManagement />} />
        <Route path="/settings" element={<SettingsPage />} />
      </Route>

      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  );
}

export default App;
