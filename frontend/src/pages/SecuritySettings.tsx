import React, { useState, useEffect } from 'react';
import { useAuthStore } from '../store/authStore';
import { authAPI } from '../api/client';
import { settingsAPI } from '../api/extendedApis';
import { registerWebAuthnCredential } from '../utils/webauthn';
import toast from 'react-hot-toast';
import { X, ShieldCheck, Copy, AlertTriangle } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

export const SecuritySettings = () => {
  const user = useAuthStore(state => state.user);
  const [loading, setLoading] = useState(false);
  const [successMsg, setSuccessMsg] = useState('');
  const [errorMsg, setErrorMsg] = useState('');

  // 2FA State
  const [mfaEnabled, setMfaEnabled] = useState(false);
  const [showMfaModal, setShowMfaModal] = useState(false);
  const [showDisableModal, setShowDisableModal] = useState(false);
  const [mfaSetupData, setMfaSetupData] = useState<{ secret: string; qr_uri: string } | null>(null);
  const [mfaCode, setMfaCode] = useState('');
  const [mfaActionLoading, setMfaActionLoading] = useState(false);

  const [passwords, setPasswords] = useState({
    old_password: '',
    new_password: '',
    confirm_password: ''
  });

  useEffect(() => {
    fetchMfaStatus();
  }, []);

  const fetchMfaStatus = async () => {
    try {
      const res = await settingsAPI.totpStatus();
      setMfaEnabled(res.data.mfa_enabled);
    } catch (err) {
      console.error('Failed to fetch MFA status', err);
    }
  };

  const handleChangePassword = async (e: React.FormEvent) => {
    e.preventDefault();
    if (passwords.new_password !== passwords.confirm_password) {
      setErrorMsg('كلمتا المرور غير متطابقتين');
      return;
    }
    setLoading(true);
    setErrorMsg('');
    setSuccessMsg('');
    
    try {
      await authAPI.changePassword(passwords);
      setSuccessMsg('تم تغيير كلمة المرور بنجاح');
      setPasswords({ old_password: '', new_password: '', confirm_password: '' });
    } catch (error: any) {
      setErrorMsg(error.response?.data?.detail || 'فشل تغيير كلمة المرور');
    } finally {
      setLoading(false);
    }
  };

  const handleBiometricEnroll = async () => {
    if (!user) return;
    try {
      setLoading(true);
      const credential = await registerWebAuthnCredential(user.id, user.email, user.full_name || user.email);
      await authAPI.enrollBiometric({
        device_id: credential.id,
        device_name: navigator.userAgent,
        platform: 'web',
        biometric_template: JSON.stringify(credential)
      });
      toast.success('تم تفعيل البصمة البيومترية بنجاح');
    } catch (error: any) {
      toast.error(error.message || 'فشل تسجيل البصمة');
    } finally {
      setLoading(false);
    }
  };

  // MFA Setup Handlers
  const handleStartMfaSetup = async () => {
    if (mfaEnabled) {
      setShowDisableModal(true);
      return;
    }
    
    setMfaActionLoading(true);
    try {
      const res = await settingsAPI.totpSetup();
      setMfaSetupData(res.data);
      setShowMfaModal(true);
      setMfaCode('');
    } catch (err: any) {
      toast.error(err.response?.data?.error || 'فشل في بدء إعداد المصادقة الثنائية');
    } finally {
      setMfaActionLoading(false);
    }
  };

  const handleVerifyMfa = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!mfaCode) return;
    
    setMfaActionLoading(true);
    try {
      await settingsAPI.totpVerify(mfaCode);
      toast.success('تم تفعيل المصادقة الثنائية بنجاح');
      setMfaEnabled(true);
      setShowMfaModal(false);
      setMfaSetupData(null);
    } catch (err: any) {
      toast.error(err.response?.data?.error || 'رمز التحقق غير صحيح');
    } finally {
      setMfaActionLoading(false);
    }
  };

  const handleDisableMfa = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!mfaCode) return;
    
    setMfaActionLoading(true);
    try {
      await settingsAPI.totpDisable(mfaCode);
      toast.success('تم إلغاء تفعيل المصادقة الثنائية بنجاح');
      setMfaEnabled(false);
      setShowDisableModal(false);
      setMfaCode('');
    } catch (err: any) {
      toast.error(err.response?.data?.error || 'رمز التحقق غير صحيح');
    } finally {
      setMfaActionLoading(false);
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    toast.success('تم نسخ الرمز السري');
  };

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <h1 className="text-2xl font-bold text-gray-800 dark:text-white mb-6">الإعدادات الأمنية</h1>
      
      <div className="bg-white dark:bg-gray-800 shadow rounded-lg overflow-hidden mb-6 p-6">
        <h2 className="text-lg font-semibold text-gray-800 dark:text-white mb-4">تغيير كلمة المرور</h2>
        
        {successMsg && <div className="mb-4 p-3 bg-green-100 text-green-700 rounded">{successMsg}</div>}
        {errorMsg && <div className="mb-4 p-3 bg-red-100 text-red-700 rounded">{errorMsg}</div>}
        
        <form onSubmit={handleChangePassword} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">كلمة المرور الحالية</label>
            <input 
              type="password" 
              required
              className="w-full border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:border-indigo-500 focus:ring-indigo-500 p-2 border bg-white dark:bg-gray-700 dark:text-white"
              value={passwords.old_password}
              onChange={e => setPasswords({...passwords, old_password: e.target.value})}
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">كلمة المرور الجديدة</label>
            <input 
              type="password" 
              required
              className="w-full border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:border-indigo-500 focus:ring-indigo-500 p-2 border bg-white dark:bg-gray-700 dark:text-white"
              value={passwords.new_password}
              onChange={e => setPasswords({...passwords, new_password: e.target.value})}
            />
            <p className="text-xs text-gray-500 mt-1">يجب أن تحتوي على 12 حرفاً على الأقل.</p>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">تأكيد كلمة المرور</label>
            <input 
              type="password" 
              required
              className="w-full border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:border-indigo-500 focus:ring-indigo-500 p-2 border bg-white dark:bg-gray-700 dark:text-white"
              value={passwords.confirm_password}
              onChange={e => setPasswords({...passwords, confirm_password: e.target.value})}
            />
          </div>
          <button 
            type="submit" 
            disabled={loading}
            className="px-6 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50"
          >
            {loading ? 'جاري التحديث...' : 'تحديث كلمة المرور'}
          </button>
        </form>
      </div>
      
      <div className="bg-white dark:bg-gray-800 shadow rounded-lg overflow-hidden p-6">
        <h2 className="text-lg font-semibold text-gray-800 dark:text-white mb-4">خيارات إضافية</h2>
        <div className="space-y-3">
          <div className="flex items-center justify-between py-3 border-b dark:border-gray-700">
            <div>
              <p className="font-medium text-gray-800 dark:text-white flex items-center gap-2">
                <ShieldCheck className={`w-5 h-5 ${mfaEnabled ? 'text-emerald-500' : 'text-gray-400'}`} />
                المصادقة الثنائية (2FA)
              </p>
              <p className="text-sm text-gray-500 mt-1">حماية حسابك برمز إضافي من خلال تطبيق المصادقة</p>
            </div>
            <button 
              onClick={handleStartMfaSetup} 
              disabled={mfaActionLoading}
              className={`px-4 py-1.5 rounded-lg font-medium text-sm transition-colors ${
                mfaEnabled 
                  ? 'bg-red-50 text-red-600 hover:bg-red-100 dark:bg-red-900/20 dark:hover:bg-red-900/40' 
                  : 'bg-indigo-50 text-indigo-600 hover:bg-indigo-100 dark:bg-indigo-900/20 dark:hover:bg-indigo-900/40'
              }`}
            >
              {mfaActionLoading ? 'جاري التحميل...' : (mfaEnabled ? 'إلغاء التفعيل' : 'إعداد')}
            </button>
          </div>
          <div className="flex items-center justify-between py-3 border-b dark:border-gray-700">
            <div>
              <p className="font-medium text-gray-800 dark:text-white">البصمة البيومترية</p>
              <p className="text-sm text-gray-500 mt-1">{user?.is_biometric_enabled ? 'مفعلة' : 'غير مفعلة'}</p>
            </div>
            <button 
              onClick={handleBiometricEnroll} 
              disabled={loading} 
              className="text-indigo-600 hover:text-indigo-800 dark:text-indigo-400 dark:hover:text-indigo-300 font-medium text-sm"
            >
              {loading ? 'جاري...' : 'إدارة'}
            </button>
          </div>
        </div>
      </div>

      {/* MFA Setup Modal */}
      <AnimatePresence>
        {showMfaModal && mfaSetupData && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm" dir="rtl">
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="bg-white dark:bg-gray-800 rounded-2xl p-6 max-w-md w-full shadow-2xl relative"
            >
              <button
                onClick={() => setShowMfaModal(false)}
                className="absolute top-4 left-4 p-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 rounded-full hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
              >
                <X className="w-5 h-5" />
              </button>

              <div className="text-center mb-6 mt-4">
                <div className="w-12 h-12 bg-indigo-100 dark:bg-indigo-900/30 rounded-2xl flex items-center justify-center mx-auto mb-3">
                  <ShieldCheck className="w-6 h-6 text-indigo-600 dark:text-indigo-400" />
                </div>
                <h2 className="text-xl font-bold text-gray-900 dark:text-white">إعداد المصادقة الثنائية</h2>
                <p className="text-sm text-gray-500 dark:text-gray-400 mt-2">
                  امسح رمز الاستجابة السريعة (QR Code) أدناه باستخدام تطبيق مصادقة مثل Google Authenticator أو Authy.
                </p>
              </div>

              <div className="flex justify-center mb-6 bg-white p-4 rounded-xl shadow-sm border border-gray-100">
                <img 
                  src={`https://api.qrserver.com/v1/create-qr-code/?size=200x200&data=${encodeURIComponent(mfaSetupData.qr_uri)}`} 
                  alt="MFA QR Code" 
                  className="w-48 h-48 rounded-lg"
                />
              </div>

              <div className="mb-6">
                <p className="text-xs font-semibold text-gray-500 dark:text-gray-400 mb-2">أو أدخل الرمز السري يدوياً:</p>
                <div className="flex items-center gap-2">
                  <code className="flex-1 bg-gray-50 dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-lg p-2.5 text-sm font-mono text-center tracking-wider text-gray-800 dark:text-gray-200 select-all">
                    {mfaSetupData.secret}
                  </code>
                  <button 
                    onClick={() => copyToClipboard(mfaSetupData.secret)}
                    className="p-2.5 bg-gray-100 hover:bg-gray-200 dark:bg-gray-700 dark:hover:bg-gray-600 rounded-lg text-gray-600 dark:text-gray-300 transition-colors"
                    title="نسخ"
                  >
                    <Copy className="w-4 h-4" />
                  </button>
                </div>
              </div>

              <form onSubmit={handleVerifyMfa}>
                <div className="mb-4">
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    الرمز المؤقت المولد من التطبيق (6 أرقام)
                  </label>
                  <input
                    type="text"
                    required
                    maxLength={6}
                    pattern="\d{6}"
                    placeholder="123456"
                    className="w-full border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:border-indigo-500 focus:ring-indigo-500 p-2 border bg-white dark:bg-gray-700 dark:text-white text-center tracking-[0.5em] text-lg font-mono font-bold"
                    value={mfaCode}
                    onChange={(e) => setMfaCode(e.target.value.replace(/\D/g, ''))}
                  />
                </div>

                <button
                  type="submit"
                  disabled={mfaActionLoading || mfaCode.length !== 6}
                  className="w-full py-3 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50"
                >
                  {mfaActionLoading ? 'جاري التحقق...' : 'تأكيد التفعيل'}
                </button>
              </form>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      {/* MFA Disable Modal */}
      <AnimatePresence>
        {showDisableModal && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm" dir="rtl">
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="bg-white dark:bg-gray-800 rounded-2xl p-6 max-w-md w-full shadow-2xl relative"
            >
              <button
                onClick={() => { setShowDisableModal(false); setMfaCode(''); }}
                className="absolute top-4 left-4 p-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 rounded-full hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
              >
                <X className="w-5 h-5" />
              </button>

              <div className="text-center mb-6 mt-4">
                <div className="w-12 h-12 bg-red-100 dark:bg-red-900/30 rounded-2xl flex items-center justify-center mx-auto mb-3">
                  <AlertTriangle className="w-6 h-6 text-red-600 dark:text-red-400" />
                </div>
                <h2 className="text-xl font-bold text-gray-900 dark:text-white">إلغاء المصادقة الثنائية</h2>
                <p className="text-sm text-gray-500 dark:text-gray-400 mt-2">
                  هل أنت متأكد من رغبتك في إلغاء حماية حسابك؟ يرجى إدخال رمز التحقق الحالي لتأكيد الإلغاء.
                </p>
              </div>

              <form onSubmit={handleDisableMfa}>
                <div className="mb-6">
                  <input
                    type="text"
                    required
                    maxLength={6}
                    pattern="\d{6}"
                    placeholder="123456"
                    className="w-full border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:border-red-500 focus:ring-red-500 p-2 border bg-white dark:bg-gray-700 dark:text-white text-center tracking-[0.5em] text-lg font-mono font-bold"
                    value={mfaCode}
                    onChange={(e) => setMfaCode(e.target.value.replace(/\D/g, ''))}
                  />
                </div>

                <div className="flex gap-3">
                  <button
                    type="button"
                    onClick={() => { setShowDisableModal(false); setMfaCode(''); }}
                    className="flex-1 py-3 bg-gray-200 text-gray-800 dark:bg-gray-700 dark:text-white rounded-md hover:bg-gray-300 dark:hover:bg-gray-600 focus:outline-none"
                  >
                    تراجع
                  </button>
                  <button
                    type="submit"
                    disabled={mfaActionLoading || mfaCode.length !== 6}
                    className="flex-1 py-3 bg-red-600 text-white rounded-md hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500 disabled:opacity-50"
                  >
                    {mfaActionLoading ? 'جاري الإلغاء...' : 'تأكيد الإلغاء'}
                  </button>
                </div>
              </form>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
};
