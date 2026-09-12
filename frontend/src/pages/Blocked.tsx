import React, { useState, useEffect } from 'react';
import { ShieldAlert, RefreshCw, LogIn } from 'lucide-react';
import { securityAPI } from '../api/client';
import { getDeviceFingerprint } from '../utils/deviceFingerprint';

export default function Blocked() {
  const [checking, setChecking] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  const checkStatus = async () => {
    setChecking(true);
    setMessage(null);
    try {
      const info = await getDeviceFingerprint();
      const res = await securityAPI.checkDevice({
        device_fingerprint: info.device_fingerprint,
        mac_address: info.mac_address,
      });
      if (res.data?.authorized) {
        window.location.href = '/login';
        return;
      }
      setMessage('الجهاز أو الشبكة لا يزال قيد الحظر أو بانتظار الموافقة.');
    } catch (err: any) {
      const code = err.response?.data?.code || err.response?.data?.state;
      if (code === 'ZTNA_BLOCKED' || code === 'network_changed') {
        window.location.href = '/login';
      } else {
        setMessage(err.response?.data?.detail || err.response?.data?.error || 'الجهاز أو الشبكة لا يزال قيد الحظر.');
      }
    } finally {
      setChecking(false);
    }
  };

  useEffect(() => {
    checkStatus();
    const interval = setInterval(checkStatus, 6000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="flex h-screen w-full items-center justify-center bg-gray-50 dark:bg-gray-900 px-4">
      <div className="max-w-md w-full text-center space-y-6 bg-white dark:bg-gray-800 p-8 rounded-2xl shadow-xl border border-red-100 dark:border-red-900">
        <div className="mx-auto flex h-24 w-24 items-center justify-center rounded-full bg-red-100 dark:bg-red-900/30">
          <ShieldAlert className="h-12 w-12 text-red-600 dark:text-red-500" />
        </div>
        <div className="space-y-3">
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white">تم حظر الوصول</h1>
          <p className="text-gray-600 dark:text-gray-300">
            عذراً، لقد تم حظر هذا الجهاز أو عنوان الشبكة الخاص بك من الوصول إلى النظام لدواعي أمنية.
          </p>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            إذا قمت بالسماح من تيليجرام أو تم فك الحظر، اضغط على الزر أدناه للمتابعة.
          </p>
        </div>

        {message && (
          <div className="p-3 bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-300 rounded-lg text-sm border border-red-200 dark:border-red-800">
            {message}
          </div>
        )}

        <div className="flex flex-col sm:flex-row gap-3 pt-2">
          <button
            onClick={checkStatus}
            disabled={checking}
            className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 bg-primary-600 hover:bg-primary-700 disabled:opacity-50 text-white rounded-xl font-medium transition-colors shadow-sm"
          >
            <RefreshCw className={`h-4 w-4 ${checking ? 'animate-spin' : ''}`} />
            <span>{checking ? 'جاري التحقق...' : 'إعادة التحقق'}</span>
          </button>
          <a
            href="/login"
            className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-200 rounded-xl font-medium transition-colors"
          >
            <LogIn className="h-4 w-4" />
            <span>صفحة الدخول</span>
          </a>
        </div>
      </div>
    </div>
  );
}
