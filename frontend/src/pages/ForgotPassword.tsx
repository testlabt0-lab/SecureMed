import { useState } from 'react';
import { Link, useSearchParams, useNavigate } from 'react-router-dom';
import { Mail, Lock, ShieldCheck, KeyRound, ArrowRight, CheckCircle2 } from 'lucide-react';
import toast from 'react-hot-toast';
import { authAPI } from '../api/client';

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
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-teal-50 flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        {/* Header */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-gradient-to-br from-primary-600 to-medical-500 rounded-2xl shadow-lg mb-4">
            <ShieldCheck className="w-10 h-10 text-white" />
          </div>
          <h1 className="text-3xl font-bold text-gray-900">SecureMed</h1>
          <p className="text-gray-600 mt-2">
            {isConfirmStep ? 'إعادة تعيين كلمة المرور' : 'استعادة كلمة المرور'}
          </p>
        </div>

        <div className="card">
          {isConfirmStep ? (
            /* ===== Step 2: set a new password ===== */
            <form onSubmit={handleConfirm} className="space-y-4">
              <div className="flex items-center gap-3 p-3 bg-blue-50 rounded-lg">
                <KeyRound className="w-5 h-5 text-blue-600 shrink-0" />
                <p className="text-sm text-blue-800">
                  اختر كلمة مرور جديدة قوية (12 حرفاً على الأقل، مع حروف كبيرة وصغيرة وأرقام ورموز)
                </p>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">كلمة المرور الجديدة</label>
                <div className="relative">
                  <Lock className="absolute right-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
                  <input
                    type="password"
                    value={newPassword}
                    onChange={(e) => setNewPassword(e.target.value)}
                    required
                    minLength={12}
                    autoFocus
                    dir="ltr"
                    className="input-field pr-10"
                    placeholder="••••••••••••"
                  />
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">تأكيد كلمة المرور</label>
                <div className="relative">
                  <Lock className="absolute right-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
                  <input
                    type="password"
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    required
                    minLength={12}
                    dir="ltr"
                    className="input-field pr-10"
                    placeholder="••••••••••••"
                  />
                </div>
              </div>
              <button type="submit" disabled={confirmLoading} className="btn-primary w-full">
                {confirmLoading ? 'جاري الحفظ...' : 'حفظ كلمة المرور الجديدة'}
              </button>
            </form>
          ) : sent ? (
            /* ===== Step 1 done: check your inbox ===== */
            <div className="text-center space-y-4 py-2">
              <CheckCircle2 className="w-14 h-14 text-green-500 mx-auto" />
              <h2 className="text-lg font-semibold text-gray-900">افحص بريدك الإلكتروني</h2>
              <p className="text-sm text-gray-600 leading-relaxed">
                إذا كان <span className="font-medium" dir="ltr">{email}</span> مسجلاً لدينا،
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
            </div>
          ) : (
            /* ===== Step 1: request a reset link ===== */
            <form onSubmit={handleRequest} className="space-y-4">
              <div className="flex items-center gap-3 p-3 bg-blue-50 rounded-lg">
                <Mail className="w-5 h-5 text-blue-600 shrink-0" />
                <p className="text-sm text-blue-800">
                  أدخل بريدك الإلكتروني وسنرسل لك رابطاً لإعادة تعيين كلمة المرور
                </p>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">البريد الإلكتروني</label>
                <div className="relative">
                  <Mail className="absolute right-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
                  <input
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    required
                    autoFocus
                    dir="ltr"
                    className="input-field pr-10"
                    placeholder="doctor@securemed.app"
                  />
                </div>
              </div>
              <button type="submit" disabled={requestLoading} className="btn-primary w-full">
                {requestLoading ? 'جاري الإرسال...' : 'إرسال رابط الاستعادة'}
              </button>
              <Link
                to="/login"
                className="block w-full text-center text-sm text-gray-500 hover:text-gray-700 transition-colors"
              >
                العودة لتسجيل الدخول
              </Link>
            </form>
          )}
        </div>

        <p className="text-center text-xs text-gray-400 mt-6">
          محمي بـ DevSecOps + HIPAA + WebAuthn
        </p>
      </div>
    </div>
  );
}
