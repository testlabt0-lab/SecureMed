import { useState } from 'react';
import { Link, useSearchParams, useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { Mail, Lock, ShieldCheck, KeyRound, ArrowRight, CheckCircle2, Stethoscope } from 'lucide-react';
import toast from 'react-hot-toast';
import { authAPI } from '../api/client';
import AnimatedBackground from '../components/fx/AnimatedBackground';
import ECGLine from '../components/fx/ECGLine';

const easing = [0.22, 1, 0.36, 1] as const;

/**
 * ForgotPassword page — handles both steps of the password-reset flow:
 *
 *  Step 1 (no query params): ask for the account email → server emails a
 *  one-time reset link (valid 1 hour).
 *
 *  Step 2 (uid & token in query params, i.e. user clicked the email link):
 *  show the new-password form and confirm the reset.
 */
export default function ForgotPassword() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();

  const uid = searchParams.get('uid') || '';
  const token = searchParams.get('token') || '';
  const isConfirmStep = Boolean(uid && token);

  // --- Step 1 state ---
  const [email, setEmail] = useState('');
  const [sent, setSent] = useState(false);
  const [requestLoading, setRequestLoading] = useState(false);

  // --- Step 2 state ---
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [confirmLoading, setConfirmLoading] = useState(false);

  const handleRequest = async (e: React.FormEvent) => {
    e.preventDefault();
    setRequestLoading(true);
    try {
      const { data } = await authAPI.requestPasswordReset(email);
      toast.success(data.detail || 'تم إرسال رابط الاستعادة');
      setSent(true);
    } catch (err: any) {
      toast.error(err.response?.data?.detail || err.response?.data?.email?.[0] || 'حدث خطأ، حاول مجدداً');
    } finally {
      setRequestLoading(false);
    }
  };

  const handleConfirm = async (e: React.FormEvent) => {
    e.preventDefault();
    if (newPassword !== confirmPassword) {
      toast.error('كلمتا المرور غير متطابقتين');
      return;
    }
    setConfirmLoading(true);
    try {
      const { data } = await authAPI.confirmPasswordReset({
        uid,
        token,
        new_password: newPassword,
        confirm_password: confirmPassword,
      });
      toast.success(data.detail || 'تم تحديث كلمة المرور بنجاح');
      navigate('/login');
    } catch (err: any) {
      const detail = err.response?.data?.detail;
      const fieldErrors = err.response?.data?.new_password;
      toast.error(detail || (Array.isArray(fieldErrors) ? fieldErrors.join(' ') : 'الرابط غير صالح أو منتهي الصلاحية'));
    } finally {
      setConfirmLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-4 relative">
      <AnimatedBackground variant="login" particles={12} />

      <div className="w-full max-w-md relative z-10">
        {/* Header */}
        <motion.div
          className="text-center mb-7"
          initial={{ opacity: 0, y: -22 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, ease: easing }}
        >
          <motion.div
            className="relative inline-flex items-center justify-center w-20 h-20 rounded-3xl mb-4 bg-gradient-to-br from-primary-500 via-primary-600 to-medical-600 shadow-2xl shadow-primary-600/40"
            whileHover={{ rotate: -6, scale: 1.06 }}
            transition={{ type: 'spring', stiffness: 300 }}
          >
            <span className="absolute inset-0 rounded-3xl bg-primary-500/50 animate-pulse-ring" />
            <ShieldCheck className="w-9 h-9 text-white relative animate-glow" />
          </motion.div>
          <h1 className="text-3xl font-black font-heading text-white drop-shadow-lg flex items-center justify-center gap-2">
            <Stethoscope className="w-7 h-7 text-medical-300" />
            <span dir="ltr">
              Secure<span className="text-gradient-animated">Med</span>
            </span>
          </h1>
          <p className="text-primary-100/80 mt-2 text-sm">
            {isConfirmStep ? 'إعادة تعيين كلمة المرور' : 'استعادة كلمة المرور'}
          </p>
        </motion.div>

        {/* Card */}
        <motion.div
          className="glass-strong rounded-3xl p-6 sm:p-8"
          initial={{ opacity: 0, y: 30, scale: 0.97 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          transition={{ duration: 0.65, delay: 0.12, ease: easing }}
        >
          <AnimatePresence mode="wait">
            {isConfirmStep ? (
              /* ===== Step 2: set a new password ===== */
              <motion.form
                key="confirm"
                onSubmit={handleConfirm}
                className="space-y-4"
                initial={{ opacity: 0, x: -24 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: 24 }}
                transition={{ duration: 0.35, ease: easing }}
              >
                <div className="flex items-center gap-3 p-3.5 bg-blue-50/90 dark:bg-primary-500/10 border border-blue-200/80 dark:border-primary-500/20 rounded-2xl">
                  <div className="w-9 h-9 rounded-xl bg-blue-100 dark:bg-primary-500/20 flex items-center justify-center shrink-0">
                    <KeyRound className="w-5 h-5 text-blue-600 dark:text-primary-300" />
                  </div>
                  <p className="text-sm text-blue-900 dark:text-primary-100">
                    اختر كلمة مرور جديدة قوية (12 حرفاً على الأقل، مع حروف كبيرة وصغيرة وأرقام ورموز)
                  </p>
                </div>
                <div>
                  <label className="block text-sm font-semibold text-gray-700 dark:text-gray-200 mb-1.5">كلمة المرور الجديدة</label>
                  <div className="relative group">
                    <Lock className="input-icon group-focus-within:text-primary-500 dark:group-focus-within:text-primary-400" />
                    <input
                      type="password"
                      value={newPassword}
                      onChange={(e) => setNewPassword(e.target.value)}
                      required
                      minLength={12}
                      autoFocus
                      dir="ltr"
                      className="input-field pr-11 bg-white/95 text-gray-900 placeholder:text-gray-400 dark:bg-gray-800/95 dark:text-white"
                      placeholder="••••••••••••"
                    />
                  </div>
                </div>
                <div>
                  <label className="block text-sm font-semibold text-gray-700 dark:text-gray-200 mb-1.5">تأكيد كلمة المرور</label>
                  <div className="relative group">
                    <Lock className="input-icon group-focus-within:text-primary-500 dark:group-focus-within:text-primary-400" />
                    <input
                      type="password"
                      value={confirmPassword}
                      onChange={(e) => setConfirmPassword(e.target.value)}
                      required
                      minLength={12}
                      dir="ltr"
                      className="input-field pr-11 bg-white/95 text-gray-900 placeholder:text-gray-400 dark:bg-gray-800/95 dark:text-white"
                      placeholder="••••••••••••"
                    />
                  </div>
                </div>
                <button
                  type="submit"
                  disabled={confirmLoading}
                  className="btn-primary w-full flex items-center justify-center gap-2"
                >
                  {confirmLoading && <span className="w-4 h-4 border-2 border-white/40 border-t-white rounded-full animate-spin" />}
                  {confirmLoading ? 'جاري الحفظ...' : 'حفظ كلمة المرور الجديدة'}
                </button>
              </motion.form>
            ) : sent ? (
              /* ===== Step 1 done: check your inbox ===== */
              <motion.div
                key="sent"
                className="text-center space-y-4 py-2"
                initial={{ opacity: 0, scale: 0.92 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ duration: 0.45, ease: easing }}
              >
                <motion.div
                  initial={{ scale: 0 }}
                  animate={{ scale: 1 }}
                  transition={{ type: 'spring', stiffness: 260, damping: 18, delay: 0.15 }}
                >
                  <CheckCircle2 className="w-16 h-16 text-medical-400 mx-auto animate-glow" />
                </motion.div>
                <h2 className="text-lg font-bold text-gray-900 dark:text-white">افحص بريدك الإلكتروني</h2>
                <p className="text-sm text-gray-600 dark:text-primary-100/85 leading-relaxed">
                  إذا كان <span className="font-semibold" dir="ltr">{email}</span> مسجلاً لدينا،
                  فستصل رسالة تحتوي رابط إعادة التعيين خلال دقائق.
                  الرابط صالح لمدة ساعة واحدة ولمرة واحدة فقط.
                </p>
                <p className="text-xs text-gray-400">
                  لم يصل البريد؟ افحص مجلد الرسائل غير المرغوبة (Spam)
                </p>
                <Link to="/login" className="btn-primary w-full inline-flex items-center justify-center gap-2">
                  <ArrowRight className="w-4 h-4" />
                  العودة لتسجيل الدخول
                </Link>
              </motion.div>
            ) : (
              /* ===== Step 1: request a reset link ===== */
              <motion.form
                key="request"
                onSubmit={handleRequest}
                className="space-y-4"
                initial={{ opacity: 0, x: 24 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -24 }}
                transition={{ duration: 0.35, ease: easing }}
              >
                <div className="flex items-center gap-3 p-3.5 bg-blue-50/90 dark:bg-primary-500/10 border border-blue-200/80 dark:border-primary-500/20 rounded-2xl">
                  <div className="w-9 h-9 rounded-xl bg-blue-100 dark:bg-primary-500/20 flex items-center justify-center shrink-0">
                    <Mail className="w-5 h-5 text-blue-600 dark:text-primary-300" />
                  </div>
                  <p className="text-sm text-blue-900 dark:text-primary-100">
                    أدخل بريدك الإلكتروني وسنرسل لك رابطاً لإعادة تعيين كلمة المرور
                  </p>
                </div>
                <div>
                  <label className="block text-sm font-semibold text-gray-700 dark:text-gray-200 mb-1.5">البريد الإلكتروني</label>
                  <div className="relative group">
                    <Mail className="input-icon group-focus-within:text-primary-500 dark:group-focus-within:text-primary-400" />
                    <input
                      type="email"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      required
                      autoFocus
                      dir="ltr"
                      className="input-field pr-11 bg-white/95 text-gray-900 placeholder:text-gray-400 dark:bg-gray-800/95 dark:text-white"
                      placeholder="doctor@securemed.app"
                    />
                  </div>
                </div>
                <button
                  type="submit"
                  disabled={requestLoading}
                  className="btn-primary w-full flex items-center justify-center gap-2"
                >
                  {requestLoading && <span className="w-4 h-4 border-2 border-white/40 border-t-white rounded-full animate-spin" />}
                  {requestLoading ? 'جاري الإرسال...' : 'إرسال رابط الاستعادة'}
                </button>
                <Link
                  to="/login"
                  className="block w-full text-center text-sm text-gray-500 hover:text-gray-800 dark:text-gray-300 dark:hover:text-white transition-colors"
                >
                  العودة لتسجيل الدخول
                </Link>
              </motion.form>
            )}
          </AnimatePresence>
        </motion.div>

        {/* ECG accent */}
        <div className="mt-6 opacity-60">
          <ECGLine height={44} stroke="#5eead4" strokeWidth={2.2} opacity={0.7} duration={4} />
        </div>

        <p className="text-center text-xs text-gray-400/80 mt-4">
          محمي بـ DevSecOps + HIPAA + WebAuthn
        </p>
      </div>
    </div>
  );
}
