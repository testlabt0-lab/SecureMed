import React, { useState } from 'react';
import { useAuthStore } from '../store/authStore';
import { authAPI } from '../api/client';
import { registerWebAuthnCredential } from '../utils/webauthn';
import toast from 'react-hot-toast';

export const SecuritySettings = () => {
  const { user } = useAuthStore();
  const [loading, setLoading] = useState(false);
  const [successMsg, setSuccessMsg] = useState('');
  const [errorMsg, setErrorMsg] = useState('');

  const [passwords, setPasswords] = useState({
    old_password: '',
    new_password: '',
    confirm_password: ''
  });

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
      // In a real app we might update the authStore here to set is_biometric_enabled=true
    } catch (error: any) {
      toast.error(error.message || 'فشل تسجيل البصمة');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <h1 className="text-2xl font-bold text-gray-800 mb-6">الإعدادات الأمنية</h1>
      
      <div className="bg-white shadow rounded-lg overflow-hidden mb-6 p-6">
        <h2 className="text-lg font-semibold text-gray-800 mb-4">تغيير كلمة المرور</h2>
        
        {successMsg && <div className="mb-4 p-3 bg-green-100 text-green-700 rounded">{successMsg}</div>}
        {errorMsg && <div className="mb-4 p-3 bg-red-100 text-red-700 rounded">{errorMsg}</div>}
        
        <form onSubmit={handleChangePassword} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">كلمة المرور الحالية</label>
            <input 
              type="password" 
              required
              className="w-full border-gray-300 rounded-md shadow-sm focus:border-indigo-500 focus:ring-indigo-500 p-2 border"
              value={passwords.old_password}
              onChange={e => setPasswords({...passwords, old_password: e.target.value})}
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">كلمة المرور الجديدة</label>
            <input 
              type="password" 
              required
              className="w-full border-gray-300 rounded-md shadow-sm focus:border-indigo-500 focus:ring-indigo-500 p-2 border"
              value={passwords.new_password}
              onChange={e => setPasswords({...passwords, new_password: e.target.value})}
            />
            <p className="text-xs text-gray-500 mt-1">يجب أن تحتوي على 12 حرفاً على الأقل.</p>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">تأكيد كلمة المرور</label>
            <input 
              type="password" 
              required
              className="w-full border-gray-300 rounded-md shadow-sm focus:border-indigo-500 focus:ring-indigo-500 p-2 border"
              value={passwords.confirm_password}
              onChange={e => setPasswords({...passwords, confirm_password: e.target.value})}
            />
          </div>
          <button 
            type="submit" 
            disabled={loading}
            className="px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
          >
            {loading ? 'جاري التحديث...' : 'تحديث كلمة المرور'}
          </button>
        </form>
      </div>
      
      <div className="bg-white shadow rounded-lg overflow-hidden p-6">
        <h2 className="text-lg font-semibold text-gray-800 mb-4">خيارات إضافية</h2>
        <div className="space-y-3">
          <div className="flex items-center justify-between py-2 border-b">
            <div>
              <p className="font-medium">المصادقة الثنائية (2FA)</p>
              <p className="text-sm text-gray-500">حماية حسابك برمز إضافي</p>
            </div>
            <button className="text-indigo-600 hover:text-indigo-900 font-medium" onClick={() => toast('سيتم دعمها قريباً!', { icon: '🚧' })}>إعداد</button>
          </div>
          <div className="flex items-center justify-between py-2 border-b">
            <div>
              <p className="font-medium">البصمة البيومترية</p>
              <p className="text-sm text-gray-500">{user?.is_biometric_enabled ? 'مفعلة' : 'غير مفعلة'}</p>
            </div>
            <button onClick={handleBiometricEnroll} disabled={loading} className="text-indigo-600 hover:text-indigo-900 font-medium">
              {loading ? 'جاري...' : 'إدارة'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

