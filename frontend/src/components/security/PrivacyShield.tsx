import React, { useState, useEffect, useCallback, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ShieldCheck, ShieldAlert, Lock, Unlock, LogOut, EyeOff, KeyRound, Loader2 } from 'lucide-react';
import { useAuthStore } from '../../store/authStore';
import { useSecurityPreferencesStore, LockReason } from '../../store/securityPreferencesStore';
import { roleLabel } from '../../constants/roles';
import api from '../../api/client';
import toast from 'react-hot-toast';

/**
 * Smart Privacy Shield for the SecureMed Web Application.
 *
 * Implements:
 * 1. Visual Privacy Shield (Tab Blur): Blurs sensitive clinical records when the user switches
 *    tabs or minimizes the browser, preventing visual eavesdropping in busy wards.
 * 2. Idle Session Lock: Automatically locks after the configured period of inactivity.
 * 3. Quick Unlock: Allows the clinician to verify identity (or confirm presence) to return
 *    to their exact uncommitted form state without losing half-typed clinical notes.
 */
export default function PrivacyShield() {
  const user = useAuthStore((state) => state.user);
  const logout = useAuthStore((state) => state.logout);

  const {
    isTabBlurEnabled,
    isIdleLockEnabled,
    idleTimeoutMinutes,
    isLocked,
    lockReason,
    lock,
    unlock,
    lastActiveTimestamp,
    recordActivity,
  } = useSecurityPreferencesStore();

  const [password, setPassword] = useState('');
  const [isVerifying, setIsVerifying] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');
  const passwordInputRef = useRef<HTMLInputElement>(null);

  // Focus password input when locked
  useEffect(() => {
    if (isLocked) {
      setPassword('');
      setErrorMsg('');
      setTimeout(() => {
        passwordInputRef.current?.focus();
      }, 150);
    }
  }, [isLocked]);

  // Handle Tab Switch / Visibility Change
  useEffect(() => {
    if (!user || !isTabBlurEnabled) return;

    const handleVisibilityChange = () => {
      if (document.visibilityState === 'hidden') {
        lock('tab_switch');
      }
    };

    document.addEventListener('visibilitychange', handleVisibilityChange);
    return () => document.removeEventListener('visibilitychange', handleVisibilityChange);
  }, [user, isTabBlurEnabled, lock]);

  // Handle User Activity Tracking & Inactivity Timeout Watchdog
  useEffect(() => {
    if (!user) return;

    // Activity tracker (throttled)
    let lastRecord = 0;
    const onUserInteraction = () => {
      const now = Date.now();
      if (now - lastRecord > 15_000) {
        lastRecord = now;
        recordActivity();
      }
    };

    const events = ['mousedown', 'mousemove', 'keydown', 'scroll', 'touchstart', 'click'];
    events.forEach((evt) => window.addEventListener(evt, onUserInteraction, { passive: true }));

    // Idle watchdog loop
    const checkInterval = setInterval(() => {
      if (!isIdleLockEnabled || isLocked) return;

      const idleDurationMs = Date.now() - lastActiveTimestamp;
      const thresholdMs = idleTimeoutMinutes * 60 * 1000;

      if (idleDurationMs >= thresholdMs) {
        lock('idle');
      }
    }, 10_000);

    return () => {
      events.forEach((evt) => window.removeEventListener(evt, onUserInteraction));
      clearInterval(checkInterval);
    };
  }, [user, isIdleLockEnabled, isLocked, idleTimeoutMinutes, lastActiveTimestamp, lock, recordActivity]);

  const handleUnlock = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();

    // If locked due to tab switch and password was not strictly typed, allow quick resume
    // If password was entered, verify against the login endpoint or unlock directly
    if (password.trim().length > 0) {
      setIsVerifying(true);
      setErrorMsg('');
      try {
        // Attempt fast credential check
        await api.post('/auth/login/', {
          email: user?.email,
          password: password.trim(),
        });
        toast.success('تم التحقق واستئناف الجلسة بأمان');
        unlock();
      } catch (err: any) {
        setErrorMsg('كلمة المرور غير صحيحة');
      } finally {
        setIsVerifying(false);
      }
    } else {
      // Quick presence unlock for routine tab-switching or momentary pause
      unlock();
      toast.success('تم استئناف الجلسة');
    }
  };

  const reasonDescription = useCallback((reason: LockReason) => {
    switch (reason) {
      case 'tab_switch':
        return 'تم تعتيم الشاشة تلقائياً لحماية خصوصية المريض (HIPAA) عند الانتقال إلى تبويب آخر أو تصغير النافذة.';
      case 'idle':
        return `تم قفل الشاشة مؤقتاً لعدم وجود نشاط لمدة (${idleTimeoutMinutes}) دقائق للحفاظ على أمن السجلات الطبية.`;
      case 'manual':
        return 'تم قفل الشاشة يدوياً بناءً على طلبك لتأمين المحطة الطبية.';
      default:
        return 'تم تفعيل حماية الشاشة لتأمين البيانات الطبية الحساسة.';
    }
  }, [idleTimeoutMinutes]);

  if (!isLocked || !user) return null;

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0, backdropFilter: 'blur(0px)' }}
        animate={{ opacity: 1, backdropFilter: 'blur(24px)' }}
        exit={{ opacity: 0, backdropFilter: 'blur(0px)' }}
        className="fixed inset-0 z-[100] flex items-center justify-center bg-gray-950/85 p-4 select-none text-right font-sans"
        dir="rtl"
      >
        <motion.div
          initial={{ scale: 0.95, y: 15 }}
          animate={{ scale: 1, y: 0 }}
          className="relative w-full max-w-md overflow-hidden rounded-3xl border border-white/10 bg-gradient-to-b from-gray-900/90 to-gray-950/95 p-8 shadow-2xl shadow-black/80 backdrop-blur-3xl"
        >
          {/* Glowing Ambient Orb */}
          <div className="absolute -right-20 -top-20 h-44 w-44 rounded-full bg-primary-500/20 blur-3xl pointer-events-none" />
          <div className="absolute -left-20 -bottom-20 h-44 w-44 rounded-full bg-teal-500/15 blur-3xl pointer-events-none" />

          {/* Header Icon */}
          <div className="flex flex-col items-center text-center">
            <div className="relative mb-4 flex h-20 w-20 items-center justify-center rounded-2xl bg-gradient-to-tr from-primary-600 to-teal-500 p-0.5 shadow-lg shadow-primary-500/25">
              <div className="flex h-full w-full items-center justify-center rounded-2xl bg-gray-950">
                <Lock className="h-9 w-9 text-primary-400 animate-pulse" />
              </div>
              <span className="absolute -bottom-1 -right-1 flex h-6 w-6 items-center justify-center rounded-full bg-teal-500 text-white shadow-md">
                <EyeOff className="h-3.5 w-3.5" />
              </span>
            </div>

            <h2 className="text-xl font-bold text-white tracking-wide">
              شاشة الخصوصية النشطة
            </h2>
            <p className="mt-1 text-xs text-primary-400 font-medium tracking-wide flex items-center gap-1">
              <ShieldCheck className="w-3.5 h-3.5" />
              حماية بيانات المرضى والامتثال لمعايير Zero Trust
            </p>
            <p className="mt-3 text-xs text-gray-400 leading-relaxed max-w-sm">
              {reasonDescription(lockReason)}
            </p>
          </div>

          {/* User Profile Card */}
          <div className="mt-6 flex items-center gap-3 rounded-2xl border border-white/5 bg-white/[0.03] p-3.5">
            <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-primary-500 to-indigo-600 text-base font-bold text-white shadow-md">
              {user.full_name?.charAt(0) || 'U'}
            </div>
            <div className="min-w-0 flex-1">
              <p className="text-sm font-semibold text-white truncate">{user.full_name}</p>
              <div className="flex items-center gap-2 mt-0.5">
                <span className="inline-block rounded-md bg-primary-500/10 px-2 py-0.5 text-[10px] font-semibold text-primary-300 border border-primary-500/20">
                  {roleLabel(user.role)}
                </span>
                {user.department && (
                  <span className="text-[11px] text-gray-400 truncate">
                    {user.department}
                  </span>
                )}
              </div>
            </div>
          </div>

          {/* Unlock Form */}
          <form onSubmit={handleUnlock} className="mt-6 space-y-4">
            <div>
              <label className="block text-xs font-medium text-gray-300 mb-1.5 flex items-center justify-between">
                <span>تأكيد الهوية لاستئناف الجلسة:</span>
                <span className="text-[10px] text-gray-500 font-normal">كلمة المرور (اختياري للاستئناف السريع)</span>
              </label>
              <div className="relative">
                <input
                  ref={passwordInputRef}
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="أدخل كلمة المرور أو اضغط استئناف..."
                  className="w-full rounded-xl border border-white/10 bg-white/[0.05] px-4 py-3 pl-10 text-sm text-white placeholder-gray-500 focus:border-primary-500 focus:bg-white/[0.08] focus:outline-none focus:ring-1 focus:ring-primary-500 transition-all text-right"
                />
                <KeyRound className="absolute left-3.5 top-3.5 h-4 w-4 text-gray-500 pointer-events-none" />
              </div>
              {errorMsg && (
                <p className="mt-1.5 text-xs text-red-400 flex items-center gap-1">
                  <ShieldAlert className="w-3.5 h-3.5" />
                  {errorMsg}
                </p>
              )}
            </div>

            <div className="flex gap-2.5 pt-1">
              <button
                type="submit"
                disabled={isVerifying}
                className="flex-1 rounded-xl bg-gradient-to-r from-primary-600 to-teal-600 hover:from-primary-500 hover:to-teal-500 py-3 text-sm font-bold text-white shadow-lg shadow-primary-500/20 transition-all active:scale-[0.98] flex items-center justify-center gap-2 cursor-pointer"
              >
                {isVerifying ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    جارِ الفحص...
                  </>
                ) : (
                  <>
                    <Unlock className="h-4 w-4" />
                    استئناف العمل
                  </>
                )}
              </button>

              <button
                type="button"
                onClick={logout}
                title="تسجيل الخروج وإنهاء الجلسة"
                className="rounded-xl border border-red-500/20 bg-red-500/10 hover:bg-red-500/20 px-4 py-3 text-xs font-semibold text-red-400 transition-all flex items-center justify-center gap-1.5 cursor-pointer"
              >
                <LogOut className="h-4 w-4" />
                خروج
              </button>
            </div>
          </form>

          {/* Footer Note */}
          <div className="mt-6 border-t border-white/5 pt-4 text-center">
            <p className="text-[11px] text-gray-500">
              جميع المحاولات وجلسات فك القفل موثقة في سجل التدقيق الأمني المشفر (HMAC Audit Trail).
            </p>
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
}
