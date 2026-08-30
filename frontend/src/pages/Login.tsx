import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';
import { authAPI } from '../api/client';
import { mfaApi } from '../api/extendedApis';
import { Stethoscope, Fingerprint, Mail, Lock, ShieldCheck, AlertCircle, Smartphone } from 'lucide-react';
import toast from 'react-hot-toast';
import {
  isWebAuthnAvailable, isBiometricAvailable,
  enrollBiometric, loginWithBiometric,
  getCredentialByEmail,
} from '../utils/webauthn';

export default function Login() {
  const navigate = useNavigate();
  const setAuth = useAuthStore((s) => s.setAuth);
  const [mode, setMode] = useState<'password' | 'biometric'>('password');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [webauthnSupported] = useState(isWebAuthnAvailable());

  // 2FA step state
  const [pendingMfaToken, setPendingMfaToken] = useState<string | null>(null);
  const [mfaCode, setMfaCode] = useState('');
  const [mfaEmail, setMfaEmail] = useState('');

  const completeMfaLogin = async (token: string, code: string) => {
    setLoading(true);
    try {
      const { data } = await mfaApi.login(token, code);
      setAuth(data.user, data.tokens);
      toast.success(`مرحباً ${data.user.full_name}`);
      navigate('/dashboard');
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'رمز التحقق غير صحيح');
    } finally {
      setLoading(false);
    }
  };

  const handlePasswordLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      const { data } = await authAPI.login(email, password);
      if (data.requires_2fa) {
        setPendingMfaToken(data.mfa_token);
        setMfaEmail(email);
        toast('الحساب محمي بالتحقق بخطوتين — أدخل الرمز', { icon: '🔐' });
        return;
      }
      setAuth(data.user, data.tokens);
      toast.success(`مرحباً ${data.user.full_name}`);
      navigate('/dashboard');
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'فشل تسجيل الدخول');
    } finally {
      setLoading(false);
    }
  };

  const handleBiometricLogin = async () => {
    if (!email) {
      toast.error('يرجى إدخال البريد الإلكتروني أولاً');
      return;
    }

    if (!webauthnSupported) {
      toast.error('متصفحك لا يدعم WebAuthn. استخدم Chrome أو Edge أو Safari حديث');
      return;
    }

    setLoading(true);
    try {
      // Check if biometric is available on this device
      const available = await isBiometricAvailable();
      if (!available) {
        toast.error('البصمة غير متاحة على هذا الجهاز. استخدم جهازاً به بصمة (Windows Hello / Touch ID)');
        setLoading(false);
        return;
      }

      // Check if user has registered biometric
      const stored = getCredentialByEmail(email);
      if (!stored) {
        toast.error('البصمة غير مسجلة لهذا المستخدم. سجل الدخول بكلمة المرور ثم فعّل البصمة من الملف الشخصي');
        setLoading(false);
        return;
      }

      // Use WebAuthn for biometric authentication
      const result = await loginWithBiometric(email);
      if (!result.success) {
        toast.error(result.error || 'فشل المصادقة البيومترية');
        setLoading(false);
        return;
      }

      // Get a challenge from the server (or generate locally for demo)
      try {
        const challengeData = await authAPI.biometricChallenge(email, `web-${navigator.userAgent.slice(0, 30)}`);
        // Send the WebAuthn assertion to the server for verification
        // In production, the server verifies the assertion cryptographically
        // For demo, we use the assertion as the biometric response
        const biometricResponse = result.assertion?.id || `webauthn-${Date.now()}`;
        const biometricTemplate = `webauthn-template-${result.assertion?.id || ''}`;

        const { data: loginData } = await authAPI.biometricLogin({
          challenge_id: challengeData.data.challenge_id,
          biometric_response: biometricResponse,
          biometric_template: biometricTemplate,
        });

        setAuth(loginData.user, loginData.tokens);
        toast.success(`مرحباً ${loginData.user.full_name} (بصمة WebAuthn)`);
        navigate('/dashboard');
      } catch (apiErr: any) {
        // Fallback: if server biometric API fails, try direct login with WebAuthn result
        // This allows demo without a fully configured backend biometric profile
        toast.error(apiErr.response?.data?.detail || 'فشل التحقق من الخادم');
      }
    } catch (err: any) {
      toast.error(err.message || 'فشل المصادقة البيومترية');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-primary-50 via-white to-medical-50 flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-20 h-20 bg-gradient-to-br from-primary-600 to-medical-600 rounded-2xl mb-4 shadow-lg">
            <Stethoscope className="w-10 h-10 text-white" />
          </div>
          <h1 className="text-3xl font-bold text-gray-900">SecureMed</h1>
          <p className="text-gray-600 mt-2">منصة الرعاية الصحية الذكية الآمنة</p>
          <div className="mt-3 flex items-center justify-center gap-2 text-sm text-medical-600">
            <ShieldCheck className="w-4 h-4" />
            <span>محمي بـ DevSecOps + HIPAA + WebAuthn</span>
          </div>
        </div>

        <div className="card">
          {/* ===== 2FA verification step ===== */}
          {pendingMfaToken ? (
            <div className="space-y-4">
              <div className="flex items-center gap-3 p-3 bg-blue-50 rounded-lg">
                <Smartphone className="w-5 h-5 text-blue-600" />
                <p className="text-sm text-blue-800">
                  أدخل رمز التحقق الستة أرقام من تطبيق المصادقة
                  <span className="block text-xs text-blue-600 mt-0.5" dir="ltr">{mfaEmail}</span>
                </p>
              </div>
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  completeMfaLogin(pendingMfaToken, mfaCode);
                }}
                className="space-y-4"
              >
                <input
                  type="text"
                  value={mfaCode}
                  onChange={(e) => setMfaCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
                  required
                  autoFocus
                  dir="ltr"
                  inputMode="numeric"
                  pattern="[0-9]{6}"
                  placeholder="000000"
                  className="input-field text-center text-2xl tracking-[0.5em] font-bold"
                />
                <button type="submit" disabled={loading || mfaCode.length !== 6} className="btn-primary w-full">
                  {loading ? 'جاري التحقق...' : 'تحقق ودخول'}
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setPendingMfaToken(null);
                    setMfaCode('');
                  }}
                  className="w-full text-sm text-gray-500 hover:text-gray-700 transition-colors"
                >
                  العودة لتسجيل الدخول
                </button>
              </form>
            </div>
          ) : (
          <>
          <div className="flex gap-2 mb-6 bg-gray-100 p-1 rounded-lg">
            <button
              onClick={() => setMode('password')}
              className={`flex-1 flex items-center justify-center gap-2 py-2 rounded-md transition-all text-sm font-medium ${
                mode === 'password'
                  ? 'bg-white text-primary-700 shadow-sm'
                  : 'text-gray-500'
              }`}
            >
              <Mail className="w-4 h-4" />
              كلمة المرور
            </button>
            <button
              onClick={() => setMode('biometric')}
              className={`flex-1 flex items-center justify-center gap-2 py-2 rounded-md transition-all text-sm font-medium ${
                mode === 'biometric'
                  ? 'bg-white text-primary-700 shadow-sm'
                  : 'text-gray-500'
              }`}
            >
              <Fingerprint className="w-4 h-4" />
              البصمة (WebAuthn)
            </button>
          </div>

          {!webauthnSupported && mode === 'biometric' && (
            <div className="mb-4 p-3 bg-yellow-50 border border-yellow-200 rounded-lg flex items-start gap-2">
              <AlertCircle className="w-5 h-5 text-yellow-600 flex-shrink-0 mt-0.5" />
              <p className="text-sm text-yellow-800">
                متصفحك لا يدعم WebAuthn. استخدم Chrome 67+ أو Edge أو Safari 13+ أو Firefox 60+
              </p>
            </div>
          )}

          {mode === 'password' ? (
            <form onSubmit={handlePasswordLogin} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  البريد الإلكتروني
                </label>
                <div className="relative">
                  <Mail className="absolute right-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
                  <input
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    required
                    className="input-field pr-10"
                    placeholder="doctor@securemed.app"
                  />
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  كلمة المرور
                </label>
                <div className="relative">
                  <Lock className="absolute right-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
                  <input
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    required
                    className="input-field pr-10"
                    placeholder="••••••••"
                  />
                </div>
              </div>
              <button type="submit" disabled={loading} className="btn-primary w-full">
                {loading ? 'جاري التحقق...' : 'تسجيل الدخول'}
              </button>
              <Link
                to="/forgot-password"
                className="block text-center text-sm text-primary-600 hover:text-primary-700 transition-colors"
              >
                نسيت كلمة المرور؟
              </Link>
            </form>
          ) : (
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  البريد الإلكتروني
                </label>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="input-field"
                  placeholder="doctor@securemed.app"
                />
              </div>
              <button
                onClick={handleBiometricLogin}
                disabled={loading || !webauthnSupported}
                className="w-full py-4 bg-gradient-to-r from-primary-600 to-medical-600 text-white rounded-lg font-medium hover:shadow-lg transition-all flex items-center justify-center gap-3 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <Fingerprint className="w-6 h-6" />
                {loading ? 'جاري المسح...' : 'تسجيل الدخول بالبصمة'}
              </button>
              <div className="p-3 bg-blue-50 rounded-lg">
                <p className="text-xs text-blue-800">
                  <strong>WebAuthn (FIDO2):</strong> يطلب بصمتك عبر Windows Hello أو Touch ID.
                  البيانات البيومترية لا تغادر جهازك أبداً - يتم تخزين hash فقط.
                </p>
              </div>
              <p className="text-xs text-gray-500 text-center">
                يتطلب تفعيل البصمة مسبقاً من الملف الشخصي
              </p>
            </div>
          )}
          </>
          )}
        </div>

        <div className="mt-6 text-center">
          <p className="text-xs text-gray-500">
            © 2026 SecureMed - مشروع مادة تصميم وهندسة البرمجيات الآمنة
          </p>
        </div>
      </div>
    </div>
  );
}
