import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { User, Fingerprint, Lock, Shield, Mail, Phone, MapPin, CheckCircle, AlertCircle, Smartphone, KeyRound, Trash2, MonitorSmartphone, AlertTriangle } from 'lucide-react';
import { useAuthStore } from '../store/authStore';
import { authAPI, securityAPI } from '../api/client';
import { mfaApi, biometricDevicesApi } from '../api/extendedApis';
import toast from 'react-hot-toast';
import {
  isWebAuthnAvailable,
  enrollBiometric, describeDevice, getDeviceId, forgetEnrolledEmail,
} from '../utils/webauthn';
import { roleLabel } from '../constants/roles';

export default function Profile() {
  const { user, updateUser, logout } = useAuthStore();
  const navigate = useNavigate();
  const [showPasswordForm, setShowPasswordForm] = useState(false);
  const [showBiometricForm, setShowBiometricForm] = useState(false);
  const [loading, setLoading] = useState(false);
  const [passwordData, setPasswordData] = useState({
    old_password: '',
    new_password: '',
    confirm_password: '',
  });
  const [biometricData, setBiometricData] = useState({
    device_name: describeDevice(),
  });

  // ===== 2FA state =====
  const [mfaEnabled, setMfaEnabled] = useState(false);
  const [mfaSetup, setMfaSetup] = useState<any>(null); // { secret, qr_image }
  const [mfaCode, setMfaCode] = useState('');
  const [mfaDisableCode, setMfaDisableCode] = useState('');
  const [showMfaDisable, setShowMfaDisable] = useState(false);

  // ===== Biometric devices =====
  const [devices, setDevices] = useState<any[]>([]);

  // ===== My registered devices (session devices) =====
  const [myDevices, setMyDevices] = useState<any[]>([]);
  const [removingDevice, setRemovingDevice] = useState<string | null>(null);

  // ===== Account deletion (danger zone) =====
  const [showDeleteAccount, setShowDeleteAccount] = useState(false);
  const [deletePassword, setDeletePassword] = useState('');
  const [deleting, setDeleting] = useState(false);

  const loadMyDevices = async () => {
    try {
      const { data } = await securityAPI.myDevices.list();
      setMyDevices(Array.isArray(data?.devices) ? data.devices : []);
    } catch { /* ignore — the section just stays hidden on failure */ }
  };

  const loadMfaStatus = async () => {
    try {
      const { data } = await mfaApi.status();
      setMfaEnabled(data.mfa_enabled);
    } catch { /* ignore */ }
  };

  const loadDevices = async () => {
    try {
      const { data } = await biometricDevicesApi.list();
      setDevices(Array.isArray(data) ? data : data?.results || []);
    } catch { /* ignore */ }
  };

  useEffect(() => {
    loadMfaStatus();
    loadDevices();
    loadMyDevices();
  }, []);

  const handleMfaSetup = async () => {
    try {
      const { data } = await mfaApi.setup();
      setMfaSetup(data);
      setMfaCode('');
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'فشل بدء الإعداد');
    }
  };

  const handleMfaVerify = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await mfaApi.verify(mfaCode);
      toast.success('تم تفعيل التحقق بخطوتين بنجاح');
      setMfaSetup(null);
      setMfaCode('');
      setMfaEnabled(true);
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'الرمز غير صحيح');
    }
  };

  const handleMfaDisable = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await mfaApi.disable(mfaDisableCode);
      toast.success('تم تعطيل التحقق بخطوتين');
      setShowMfaDisable(false);
      setMfaDisableCode('');
      setMfaEnabled(false);
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'الرمز غير صحيح');
    }
  };

  const handleRemoveDevice = async (id: string, deviceId?: string) => {
    try {
      await biometricDevicesApi.remove(id);
      // Drop the local hint too, otherwise the login screen keeps offering a
      // fingerprint button for a credential the server no longer knows.
      if (user && deviceId && deviceId === getDeviceId()) {
        forgetEnrolledEmail(user.email);
      }
      toast.success('تم حذف الجهاز');
      loadDevices();
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'فشل حذف الجهاز');
    }
  };

  const handleRemoveMyDevice = async (fingerprint: string) => {
    setRemovingDevice(fingerprint);
    try {
      await securityAPI.myDevices.remove(fingerprint);
      toast.success('تمت إزالة الجهاز');
      await loadMyDevices();
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'فشل إزالة الجهاز');
    } finally {
      setRemovingDevice(null);
    }
  };

  const handleDeleteAccount = async () => {
    if (!deletePassword) return;
    setDeleting(true);
    try {
      // The server deactivates the account and force-ends every session.
      await securityAPI.account.delete(deletePassword);
      toast.success('تم حذف الحساب بنجاح');
      // The local session is dead on the server — clear the client side and
      // route to login. The navigate happens after logout so guards settle.
      logout();
      navigate('/login');
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'تعذر حذف الحساب — تحقق من كلمة المرور');
    } finally {
      setDeleting(false);
      setDeletePassword('');
    }
  };

  const handleChangePassword = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await authAPI.changePassword(passwordData);
      toast.success('تم تغيير كلمة المرور بنجاح');
      setPasswordData({ old_password: '', new_password: '', confirm_password: '' });
      setShowPasswordForm(false);
    } catch (err: any) {
      toast.error(err.response?.data?.detail || err.response?.data?.new_password?.[0] || 'فشل');
    }
  };

  const handleEnrollBiometric = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!user) return;

    if (!isWebAuthnAvailable()) {
      toast.error('متصفحك لا يدعم WebAuthn. استخدم Chrome أو Edge أو Safari حديث');
      return;
    }

    setLoading(true);
    try {
      // One call: the server issues the challenge, the device signs it, the public
      // key is stored. There is no second "notify the backend" step any more — the
      // old one sent a different device_id than the login screen used and swallowed
      // its own failure, so the UI reported success while the server had nothing.
      const result = await enrollBiometric(biometricData.device_name);

      if (!result.success) {
        toast.error(result.error || 'فشل تسجيل البصمة');
        return;
      }

      updateUser({ is_biometric_enabled: true });
      toast.success('تم تسجيل البصمة بنجاح عبر WebAuthn');
      setShowBiometricForm(false);
      loadDevices();
    } catch (err: any) {
      toast.error(err.message || 'فشل تسجيل البصمة');
    } finally {
      setLoading(false);
    }
  };

  if (!user) return null;

  return (
    <div className="space-y-6 max-w-4xl mx-auto">
      <div>
        <h1 className="text-2xl font-bold">الملف الشخصي</h1>
        <p className="text-gray-600 text-sm mt-1">إدارة حسابك وإعدادات الأمان</p>
      </div>

      {/* Profile Info */}
      <div className="card">
        <div className="flex items-center gap-4 mb-6">
          <div className="w-20 h-20 bg-gradient-to-br from-primary-500 to-medical-500 rounded-2xl flex items-center justify-center">
            <span className="text-white text-3xl font-bold">
              {user.full_name?.charAt(0) || '?'}
            </span>
          </div>
          <div>
            <h2 className="text-xl font-bold">{user.full_name}</h2>
            <p className="text-gray-600">{roleLabel(user.role)}</p>
            <div className="flex items-center gap-2 mt-1">
              {user.is_biometric_enabled ? (
                <span className="badge badge-success">
                  <Fingerprint className="w-3 h-3 ml-1" />
                  البصمة مفعلة
                </span>
              ) : (
                <span className="badge badge-warning">البصمة غير مفعلة</span>
              )}
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg">
            <Mail className="w-5 h-5 text-gray-400" />
            <div>
              <p className="text-xs text-gray-500">البريد الإلكتروني</p>
              <p className="font-medium">{user.email}</p>
            </div>
          </div>
          <div className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg">
            <Phone className="w-5 h-5 text-gray-400" />
            <div>
              <p className="text-xs text-gray-500">الهاتف</p>
              <p className="font-medium">{user.phone || 'غير محدد'}</p>
            </div>
          </div>
          {user.license_number && (
            <div className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg">
              <Shield className="w-5 h-5 text-gray-400" />
              <div>
                <p className="text-xs text-gray-500">رقم الترخيص</p>
                <p className="font-medium">{user.license_number}</p>
              </div>
            </div>
          )}
          {user.department && (
            <div className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg">
              <MapPin className="w-5 h-5 text-gray-400" />
              <div>
                <p className="text-xs text-gray-500">القسم</p>
                <p className="font-medium">{user.department}</p>
              </div>
            </div>
          )}
          {user.specialization && (
            <div className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg">
              <User className="w-5 h-5 text-gray-400" />
              <div>
                <p className="text-xs text-gray-500">التخصص</p>
                <p className="font-medium">{user.specialization}</p>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Security Settings */}
      <div className="card">
        <h2 className="font-bold mb-4 flex items-center gap-2">
          <Shield className="w-5 h-5 text-primary-600" />
          إعدادات الأمان
        </h2>

        <div className="space-y-4">
          {/* Biometric Authentication */}
          <div className="flex items-center justify-between p-4 border border-gray-200 rounded-lg">
            <div className="flex items-center gap-3">
              <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${
                user.is_biometric_enabled ? 'bg-green-100' : 'bg-gray-100'
              }`}>
                <Fingerprint className={`w-5 h-5 ${
                  user.is_biometric_enabled ? 'text-green-600' : 'text-gray-400'
                }`} />
              </div>
              <div>
                <h3 className="font-medium">المصادقة البيومترية</h3>
                <p className="text-sm text-gray-500">
                  {user.is_biometric_enabled
                    ? 'البصمة مفعلة - يمكنك تسجيل الدخول بالبصمة'
                    : 'فعّل البصمة لتسجيل دخول آمن إضافي'}
                </p>
              </div>
            </div>
            {!user.is_biometric_enabled && (
              <button
                onClick={() => setShowBiometricForm(true)}
                className="btn-primary text-sm"
              >
                تفعيل
              </button>
            )}
          </div>

          {/* Two-Factor Authentication (TOTP) */}
          <div className="p-4 border border-gray-200 rounded-lg">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${
                  mfaEnabled ? 'bg-green-100' : 'bg-gray-100'
                }`}>
                  <Smartphone className={`w-5 h-5 ${
                    mfaEnabled ? 'text-green-600' : 'text-gray-400'
                  }`} />
                </div>
                <div>
                  <h3 className="font-medium">التحقق بخطوتين (TOTP)</h3>
                  <p className="text-sm text-gray-500">
                    {mfaEnabled
                      ? 'مفعل — طبقة حماية إضافية عند كل تسجيل دخول'
                      : 'فعّله لحماية حسابك برمز من Google Authenticator'}
                  </p>
                </div>
              </div>
              {!mfaEnabled ? (
                <button onClick={handleMfaSetup} className="btn-primary text-sm">
                  تفعيل
                </button>
              ) : (
                <button
                  onClick={() => setShowMfaDisable(true)}
                  className="btn-secondary text-sm text-red-600"
                >
                  تعطيل
                </button>
              )}
            </div>

            {/* 2FA setup flow */}
            {mfaSetup && (
              <div className="mt-4 p-4 bg-blue-50 dark:bg-gray-700 rounded-lg">
                <p className="text-sm text-blue-900 dark:text-blue-200 font-medium mb-3">
                  1. امسح رمز QR بتطبيق المصادقة (Google Authenticator / Authy)
                </p>
                <div className="flex flex-col md:flex-row items-center gap-4">
                  <img
                    src={mfaSetup.qr_image}
                    alt="QR Code"
                    className="w-40 h-40 bg-white p-2 rounded-lg border"
                  />
                  <div className="flex-1 w-full">
                    <p className="text-xs text-gray-600 dark:text-gray-300 mb-1">
                      أو أدخل المفتاح يدوياً:
                    </p>
                    <code dir="ltr" className="block text-xs bg-white dark:bg-gray-800 p-2 rounded border mb-3 break-all">
                      {mfaSetup.secret}
                    </code>
                    <form onSubmit={handleMfaVerify} className="flex gap-2">
                      <input
                        value={mfaCode}
                        onChange={(e) => setMfaCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
                        dir="ltr"
                        inputMode="numeric"
                        placeholder="000000"
                        className="input-field text-center tracking-widest"
                        required
                      />
                      <button type="submit" className="btn-primary text-sm whitespace-nowrap">
                        تأكيد
                      </button>
                      <button
                        type="button"
                        onClick={() => setMfaSetup(null)}
                        className="btn-secondary text-sm"
                      >
                        إلغاء
                      </button>
                    </form>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Password Change */}
          <div className="flex items-center justify-between p-4 border border-gray-200 rounded-lg">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center">
                <Lock className="w-5 h-5 text-blue-600" />
              </div>
              <div>
                <h3 className="font-medium">تغيير كلمة المرور</h3>
                <p className="text-sm text-gray-500">يُنصح بتغييرها كل 90 يوماً</p>
              </div>
            </div>
            <button
              onClick={() => setShowPasswordForm(true)}
              className="btn-secondary text-sm"
            >
              تغيير
            </button>
          </div>
        </div>
      </div>

      {/* Registered Biometric Devices */}
      <div className="card">
        <h2 className="font-bold mb-4 flex items-center gap-2">
          <MonitorSmartphone className="w-5 h-5 text-primary-600" />
          الأجهزة المسجلة للبصمة ({devices.length})
        </h2>
        {devices.length === 0 ? (
          <p className="text-sm text-gray-400 text-center py-4">
            لا توجد أجهزة مسجلة — فعّل البصمة لإضافة جهازك
          </p>
        ) : (
          <div className="space-y-2">
            {devices.map((d) => (
              <div
                key={d.id}
                className="flex items-center justify-between gap-3 p-3 bg-gray-50 dark:bg-gray-700/50 rounded-lg"
              >
                <div className="flex items-center gap-3 min-w-0">
                  <div className={`w-9 h-9 rounded-lg flex items-center justify-center flex-shrink-0 ${
                    d.is_active ? 'bg-green-100' : 'bg-gray-200 dark:bg-gray-600'
                  }`}>
                    <Fingerprint className={`w-4 h-4 ${
                      d.is_active ? 'text-green-600' : 'text-gray-400'
                    }`} />
                  </div>
                  <div className="min-w-0">
                    <p className="text-sm font-medium text-gray-900 dark:text-white truncate">
                      {d.device_name || d.device_id}
                    </p>
                    <p className="text-xs text-gray-400">
                      {d.platform} •{' '}
                      {d.is_active ? 'نشط' : 'ملغى'}
                      {d.last_used ? ` • آخر استخدام: ${new Date(d.last_used).toLocaleDateString('ar')}` : ''}
                    </p>
                  </div>
                </div>
                 <button
                   onClick={() => handleRemoveDevice(d.id, d.device_id)}
                   className="p-2 text-red-500 hover:bg-red-50 dark:hover:bg-red-900/30 rounded-lg transition-colors flex-shrink-0"
                   title="حذف الجهاز"
                   aria-label="حذف الجهاز"
                 >
                   <Trash2 className="w-4 h-4" />
                 </button>
               </div>
             ))}
           </div>
         )}
       </div>

       {/* My registered session devices */}
       {myDevices.length > 0 && (
         <div className="card">
           <h2 className="font-bold mb-4 flex items-center gap-2">
             <MonitorSmartphone className="w-5 h-5 text-primary-600" />
             أجهزتي المسجلة ({myDevices.length})
           </h2>
           <p className="text-xs text-gray-400 mb-3">
             الأجهزة التي دخلت بحسابك — إزالة جهاز تمنع جلساته الجديدة
           </p>
           <div className="space-y-2">
             {myDevices.map((d: any) => (
               <div
                 key={d.id}
                 className="flex items-center justify-between gap-3 p-3 bg-gray-50 dark:bg-gray-700/50 rounded-lg"
               >
                 <div className="flex items-center gap-3 min-w-0">
                   <div className="w-9 h-9 rounded-lg flex items-center justify-center flex-shrink-0 bg-blue-100">
                     <Smartphone className="w-4 h-4 text-blue-600" />
                   </div>
                   <div className="min-w-0">
                     <p className="text-sm font-medium text-gray-900 dark:text-white truncate">
                       {d.device_name || d.device_fingerprint}
                     </p>
                     <p className="text-xs text-gray-400">
                       {d.os_info || 'جهاز مسجل'}
                       {d.is_trusted ? ' • موثوق' : ''}
                     </p>
                   </div>
                 </div>
                 <button
                   onClick={() => handleRemoveMyDevice(d.device_fingerprint)}
                   disabled={removingDevice === d.device_fingerprint}
                   className="p-2 text-red-500 hover:bg-red-50 dark:hover:bg-red-900/30 rounded-lg transition-colors flex-shrink-0 disabled:opacity-50"
                   title="إزالة الجهاز"
                   aria-label="إزالة الجهاز"
                 >
                   <Trash2 className="w-4 h-4" />
                 </button>
               </div>
             ))}
           </div>
         </div>
       )}

       {/* Danger zone: account deletion (Play requirement) */}
       <div className="card border-red-200 dark:border-red-900/50">
         <h2 className="font-bold mb-2 flex items-center gap-2 text-red-600 dark:text-red-400">
           <AlertTriangle className="w-5 h-5" />
           منطقة الخطر
         </h2>
         <div className="flex items-center justify-between gap-3 p-4 border border-red-100 dark:border-red-900/40 rounded-lg">
           <div className="flex items-center gap-3 min-w-0">
             <div className="w-10 h-10 bg-red-100 rounded-lg flex items-center justify-center flex-shrink-0">
               <AlertTriangle className="w-5 h-5 text-red-600" />
             </div>
             <div>
               <h3 className="font-medium">حذف الحساب</h3>
               <p className="text-sm text-gray-500">
                 تعطيل نهائي للحساب وإنهاء كل جلساته على كل الأجهزة — لا يمكن التراجع
               </p>
             </div>
           </div>
           <button
             onClick={() => setShowDeleteAccount(true)}
             className="btn-secondary text-sm text-red-600 border-red-200 hover:bg-red-50 dark:hover:bg-red-900/30 flex-shrink-0"
           >
             حذف
           </button>
         </div>
       </div>

      {/* Password Change Modal */}
      {showPasswordForm && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-md p-6">
            <h2 className="text-xl font-bold mb-4">تغيير كلمة المرور</h2>
            <form onSubmit={handleChangePassword} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  كلمة المرور الحالية
                </label>
                <input
                  type="password"
                  value={passwordData.old_password}
                  onChange={(e) => setPasswordData({ ...passwordData, old_password: e.target.value })}
                  required
                  className="input-field"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  كلمة المرور الجديدة (12 حرف على الأقل)
                </label>
                <input
                  type="password"
                  value={passwordData.new_password}
                  onChange={(e) => setPasswordData({ ...passwordData, new_password: e.target.value })}
                  required
                  minLength={12}
                  className="input-field"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  تأكيد كلمة المرور
                </label>
                <input
                  type="password"
                  value={passwordData.confirm_password}
                  onChange={(e) => setPasswordData({ ...passwordData, confirm_password: e.target.value })}
                  required
                  className="input-field"
                />
              </div>
              <div className="flex gap-2 pt-2">
                <button type="submit" className="btn-primary flex-1">حفظ</button>
                <button type="button" onClick={() => setShowPasswordForm(false)} className="btn-secondary flex-1">
                  إلغاء
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Account Deletion Modal (danger zone) */}
      {showDeleteAccount && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-md p-6">
            <div className="flex items-center gap-2 mb-4">
              <AlertTriangle className="w-5 h-5 text-red-600" />
              <h2 className="text-xl font-bold">حذف الحساب نهائياً</h2>
            </div>
            <p className="text-sm text-gray-600 mb-1">
              سيُعطَّل الحساب نهائياً وتنتهي كل جلساته على كل الأجهزة، ولا يمكن التراجع.
            </p>
            <p className="text-xs text-gray-400 mb-4">
              سجلات المرضى الطبية المنشأة عبر الحساب تبقى محفوظة في النظام وفق سياسة الاحتفاظ الطبي.
            </p>
            <form
              onSubmit={(e) => {
                e.preventDefault();
                handleDeleteAccount();
              }}
              className="space-y-4"
            >
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  أدخل كلمة المرور للتأكيد
                </label>
                <input
                  type="password"
                  value={deletePassword}
                  onChange={(e) => setDeletePassword(e.target.value)}
                  required
                  autoFocus
                  className="input-field"
                />
              </div>
              <div className="flex gap-2 pt-2">
                <button
                  type="submit"
                  disabled={deleting}
                  className="flex-1 py-2 rounded-lg font-medium bg-red-600 text-white hover:bg-red-700 transition-colors disabled:opacity-50"
                >
                  {deleting ? 'جارٍ الحذف…' : 'حذف نهائي'}
                </button>
                <button
                  type="button"
                  onClick={() => setShowDeleteAccount(false)}
                  disabled={deleting}
                  className="btn-secondary flex-1"
                >
                  إلغاء
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Biometric Enrollment Modal */}
      {showBiometricForm && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-md p-6">
            <h2 className="text-xl font-bold mb-4 flex items-center gap-2">
              <Fingerprint className="w-6 h-6 text-primary-600" />
              تسجيل البصمة
            </h2>
            <form onSubmit={handleEnrollBiometric} className="space-y-4">
              <div className="bg-blue-50 p-4 rounded-lg">
                <p className="text-sm text-blue-800">
                  ستطلب منك بصمتك للتحقق داخل الجهاز فقط. لا تخرج البصمة ولا أي
                  تمثيل لها من جهازك: يُنشئ الجهاز مفتاحاً خاصاً محفوظاً في عتاده
                  الآمن، ويُرسل المفتاح العام وحده إلى الخادم.
                </p>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  اسم الجهاز
                </label>
                <input
                  type="text"
                  value={biometricData.device_name}
                  onChange={(e) => setBiometricData({ ...biometricData, device_name: e.target.value })}
                  required
                  className="input-field"
                />
              </div>
              <div className="flex gap-2 pt-2">
                <button type="submit" className="btn-primary flex-1">تسجيل البصمة</button>
                <button type="button" onClick={() => setShowBiometricForm(false)} className="btn-secondary flex-1">
                  إلغاء
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* 2FA Disable Modal */}
      {showMfaDisable && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-md p-6">
            <h2 className="text-xl font-bold mb-2 flex items-center gap-2">
              <KeyRound className="w-6 h-6 text-red-500" />
              تعطيل التحقق بخطوتين
            </h2>
            <p className="text-sm text-gray-500 mb-4">
              سيؤدي التعطيل إلى إزالة طبقة حماية إضافية من حسابك. أدخل الرمز الحالي للتأكيد.
            </p>
            <form onSubmit={handleMfaDisable} className="space-y-4">
              <input
                value={mfaDisableCode}
                onChange={(e) => setMfaDisableCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
                dir="ltr"
                inputMode="numeric"
                placeholder="000000"
                className="input-field text-center tracking-widest"
                required
                autoFocus
              />
              <div className="flex gap-2">
                <button
                  type="submit"
                  className="flex-1 py-2 bg-red-600 hover:bg-red-700 text-white font-medium rounded-lg transition-colors"
                >
                  تعطيل
                </button>
                <button
                  type="button"
                  onClick={() => setShowMfaDisable(false)}
                  className="btn-secondary flex-1"
                >
                  إلغاء
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
