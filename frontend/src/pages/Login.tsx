import { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { useAuthStore } from '../store/authStore';
import { authAPI } from '../api/client';
import { mfaApi } from '../api/extendedApis';
import {
  Stethoscope, Fingerprint, Mail, Lock, ShieldCheck, AlertCircle,
  Smartphone, HeartPulse, Activity, Eye, EyeOff, ArrowLeft, ScanFace,
  Cpu, Monitor, ShieldAlert, RefreshCw, CheckCircle2,
} from 'lucide-react';
import toast from 'react-hot-toast';
import AnimatedBackground from '../components/fx/AnimatedBackground';
import ECGLine from '../components/fx/ECGLine';
import {
  isWebAuthnAvailable, isBiometricAvailable,
  enrollBiometric, loginWithBiometric,
  getCredentialByEmail,
} from '../utils/webauthn';
import { getDeviceFingerprint, DeviceInfo } from '../utils/deviceFingerprint';

const easing = [0.22, 1, 0.36, 1] as const;

const heroFeatures = [
  { icon: ShieldCheck, title: 'تشفير AES-256', sub: 'حماية عسكرية للسجلات' },
  { icon: HeartPulse, title: 'مراقبة لحظية', sub: 'مؤشرات حيوية وتنبيهات ذكية' },
  { icon: Activity, title: 'ذكاء اصطناعي', sub: 'تحليل تنبؤي للحالات' },
];

export default function Login() {
  const navigate = useNavigate();
  const setAuth = useAuthStore((s) => s.setAuth);
  const [mode, setMode] = useState<'password' | 'biometric'>('password');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [webauthnSupported] = useState(isWebAuthnAvailable());
  const [deviceInfo, setDeviceInfo] = useState<DeviceInfo | null>(null);
  const [rememberDevice, setRememberDevice] = useState(true);
  const [failedCount, setFailedCount] = useState(0);
  const [captchaAnswer, setCaptchaAnswer] = useState('');
  const [captchaChallenge, setCaptchaChallenge] = useState({ a: 3, b: 5 });
  const [blockedAlert, setBlockedAlert] = useState<string | null>(null);

  useEffect(() => {
    getDeviceFingerprint().then((info) => setDeviceInfo(info)).catch(console.error);
    generateCaptcha();
  }, []);

  const generateCaptcha = () => {
    const a = Math.floor(Math.random() * 8) + 1;
    const b = Math.floor(Math.random() * 9) + 1;
    setCaptchaChallenge({ a, b });
    setCaptchaAnswer('');
  };

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
    setBlockedAlert(null);

    // Verify captcha if enabled after multiple attempts
    if (failedCount >= 2) {
      if (parseInt(captchaAnswer, 10) !== captchaChallenge.a + captchaChallenge.b) {
        toast.error('إجابة التحقق الأمني (CAPTCHA) غير صحيحة');
        generateCaptcha();
        return;
      }
    }

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
      const detail = err.response?.data?.detail || err.response?.data?.message || 'فشل تسجيل الدخول';
      if (err.response?.status === 403 || detail.includes('حظر') || detail.includes('blocked')) {
        setBlockedAlert(detail || 'تم حظر هذا الجهاز أو عنوان IP لأسباب أمنية');
      }
      setFailedCount((c) => c + 1);
      generateCaptcha();
      toast.error(detail);
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
    <div className="min-h-screen flex items-stretch">
      <AnimatedBackground variant="login" particles={16} />

      {/* ============ Form panel (RTL start side) ============ */}
      <div className="flex-1 flex items-center justify-center p-4 sm:p-8 relative z-10">
        <div className="w-full max-w-md">
          {/* Brand */}
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
              <Stethoscope className="w-10 h-10 text-white relative animate-glow" />
            </motion.div>
            <h1 className="text-4xl font-black font-heading text-white drop-shadow-lg">
              Secure<span className="text-gradient-animated">Med</span>
            </h1>
            <p className="text-primary-100/80 mt-2 text-sm">منصة الرعاية الصحية الذكية الآمنة</p>
            <div className="mt-3 inline-flex items-center gap-2 text-xs text-medical-300 glass-chip px-3 py-1.5 rounded-full">
              <ShieldCheck className="w-3.5 h-3.5" />
              <span>محمي بـ DevSecOps + HIPAA + WebAuthn</span>
            </div>
          </motion.div>

          {/* Card */}
          <motion.div
            className="glass-strong rounded-3xl p-6 sm:p-8"
            initial={{ opacity: 0, y: 30, scale: 0.97 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            transition={{ duration: 0.65, delay: 0.12, ease: easing }}
          >
            <AnimatePresence mode="wait">
              {pendingMfaToken ? (
                /* ===== 2FA verification step ===== */
                <motion.div
                  key="mfa"
                  className="space-y-4"
                  initial={{ opacity: 0, x: -28 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: 28 }}
                  transition={{ duration: 0.35, ease: easing }}
                >
                  <div className="flex items-center gap-3 p-3.5 bg-blue-50/90 dark:bg-primary-500/10 border border-blue-200/80 dark:border-primary-500/20 rounded-2xl">
                    <div className="w-9 h-9 rounded-xl bg-blue-100 dark:bg-primary-500/20 flex items-center justify-center shrink-0">
                      <Smartphone className="w-5 h-5 text-blue-600 dark:text-primary-300 animate-wiggle" />
                    </div>
                    <p className="text-sm text-blue-900 dark:text-primary-100">
                      أدخل رمز التحقق الستة أرقام من تطبيق المصادقة
                      <span className="block text-xs text-blue-600/80 dark:text-primary-300/80 mt-0.5" dir="ltr">{mfaEmail}</span>
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
                      className="input-field text-center text-2xl tracking-[0.5em] font-bold bg-white/95 dark:bg-gray-800/95"
                    />
                    <button
                      type="submit"
                      disabled={loading || mfaCode.length !== 6}
                      className="btn-primary w-full flex items-center justify-center gap-2"
                    >
                      {loading && <span className="w-4 h-4 border-2 border-white/40 border-t-white rounded-full animate-spin" />}
                      {loading ? 'جاري التحقق...' : 'تحقق ودخول'}
                    </button>
                    <button
                      type="button"
                      onClick={() => {
                        setPendingMfaToken(null);
                        setMfaCode('');
                      }}
                      className="w-full text-sm text-gray-500 hover:text-gray-800 dark:text-gray-400 dark:hover:text-white transition-colors"
                    >
                      العودة لتسجيل الدخول
                    </button>
                  </form>
                </motion.div>
              ) : (
                <motion.div
                  key="main"
                  initial={{ opacity: 0, x: 28 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: -28 }}
                  transition={{ duration: 0.35, ease: easing }}
                >
                  {/* Tabs with sliding pill */}
                  <div className="flex gap-1 mb-6 bg-gray-900/20 dark:bg-black/30 p-1.5 rounded-2xl border border-white/10">
                    {([
                      { key: 'password', label: 'كلمة المرور', icon: Mail },
                      { key: 'biometric', label: 'البصمة', sub: '(WebAuthn)', icon: Fingerprint },
                    ] as const).map((tab) => (
                      <button
                        key={tab.key}
                        onClick={() => setMode(tab.key)}
                        className={`relative flex-1 flex items-center justify-center gap-1.5 py-2.5 px-2 rounded-xl text-sm font-semibold whitespace-nowrap transition-colors duration-200 ${
                          mode === tab.key ? 'text-white' : 'text-gray-500 hover:text-gray-800 dark:text-gray-300 dark:hover:text-white'
                        }`}
                      >
                        {mode === tab.key && (
                          <motion.span
                            layoutId="login-tab-pill"
                            className="absolute inset-0 rounded-xl bg-gradient-to-l from-primary-600 to-medical-600 shadow-lg shadow-primary-600/40"
                            transition={{ type: 'spring', stiffness: 380, damping: 32 }}
                          />
                        )}
                        <tab.icon className="w-4 h-4 relative z-10 shrink-0" />
                        <span className="relative z-10">
                          {tab.label}
                          {'sub' in tab && tab.sub && <span className="hidden md:inline text-xs"> {tab.sub}</span>}
                        </span>
                      </button>
                    ))}
                  </div>

                  <AnimatePresence mode="wait">
                    {mode === 'biometric' && !webauthnSupported && (
                      <motion.div
                        key="webauthn-warn"
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: 'auto' }}
                        exit={{ opacity: 0, height: 0 }}
                        className="overflow-hidden"
                      >
                        <div className="mb-4 p-3.5 bg-amber-50/95 dark:bg-amber-400/10 border border-amber-300/80 dark:border-amber-400/25 rounded-2xl flex items-start gap-2.5">
                          <AlertCircle className="w-5 h-5 text-amber-500 dark:text-amber-300 flex-shrink-0 mt-0.5" />
                          <p className="text-sm text-amber-800 dark:text-amber-200">
                            متصفحك لا يدعم WebAuthn. استخدم Chrome 67+ أو Edge أو Safari 13+ أو Firefox 60+
                          </p>
                        </div>
                      </motion.div>
                    )}
                  </AnimatePresence>

                  <AnimatePresence mode="wait">
                    {mode === 'password' ? (
                      <motion.form
                        key="password-form"
                        onSubmit={handlePasswordLogin}
                        className="space-y-4"
                        initial={{ opacity: 0, y: 16 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: -16 }}
                        transition={{ duration: 0.3, ease: easing }}
                      >
                        {/* Blocked Alert Banner */}
                        {blockedAlert && (
                          <motion.div
                            initial={{ opacity: 0, scale: 0.95 }}
                            animate={{ opacity: 1, scale: 1 }}
                            className="p-3.5 bg-red-500/15 border border-red-500/40 rounded-2xl flex items-start gap-3 text-red-200"
                          >
                            <ShieldAlert className="w-5 h-5 text-red-400 shrink-0 mt-0.5" />
                            <div className="text-xs space-y-1">
                              <p className="font-bold text-red-300">وصول محظور من هذا الجهاز أو العنوان</p>
                              <p>{blockedAlert}</p>
                              <p className="text-[11px] text-red-300/80">تم تقييد الوصول وتسجيل الحدث الجنائي في سجلات التدقيق الأمني WAF.</p>
                            </div>
                          </motion.div>
                        )}

                        <motion.div
                          initial={{ opacity: 0, y: 14 }}
                          animate={{ opacity: 1, y: 0 }}
                          transition={{ delay: 0.08, duration: 0.4, ease: easing }}
                        >
                          <label className="block text-sm font-semibold text-gray-700 dark:text-gray-200 mb-1.5">
                            البريد الإلكتروني
                          </label>
                          <div className="relative group">
                            <Mail className="input-icon group-focus-within:text-primary-500 dark:group-focus-within:text-primary-400" />
                            <input
                              type="email"
                              value={email}
                              onChange={(e) => setEmail(e.target.value)}
                              required
                              className="input-field pr-11 bg-white/95 text-gray-900 placeholder:text-gray-400 dark:bg-gray-800/95 dark:text-white"
                              placeholder="doctor@securemed.app"
                            />
                          </div>
                        </motion.div>
                        <motion.div
                          initial={{ opacity: 0, y: 14 }}
                          animate={{ opacity: 1, y: 0 }}
                          transition={{ delay: 0.16, duration: 0.4, ease: easing }}
                        >
                          <label className="block text-sm font-semibold text-gray-700 dark:text-gray-200 mb-1.5">
                            كلمة المرور
                          </label>
                          <div className="relative group">
                            <Lock className="input-icon group-focus-within:text-primary-500 dark:group-focus-within:text-primary-400" />
                            <input
                              type={showPassword ? 'text' : 'password'}
                              value={password}
                              onChange={(e) => setPassword(e.target.value)}
                              required
                              className="input-field pr-11 pl-11 bg-white/95 text-gray-900 placeholder:text-gray-400 dark:bg-gray-800/95 dark:text-white"
                              placeholder="••••••••"
                            />
                            <button
                              type="button"
                              tabIndex={-1}
                              onClick={() => setShowPassword(!showPassword)}
                              className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-primary-400 transition-colors"
                              aria-label={showPassword ? 'إخفاء كلمة المرور' : 'إظهار كلمة المرور'}
                            >
                              {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                            </button>
                          </div>
                        </motion.div>

                        {/* Security CAPTCHA (active after multiple attempts) */}
                        {failedCount >= 2 && (
                          <motion.div
                            initial={{ opacity: 0, height: 0 }}
                            animate={{ opacity: 1, height: 'auto' }}
                            className="p-3 bg-amber-500/10 border border-amber-500/30 rounded-2xl space-y-2"
                          >
                            <div className="flex items-center justify-between text-xs text-amber-300">
                              <span className="font-semibold flex items-center gap-1.5">
                                <ShieldCheck className="w-4 h-4 text-amber-400" />
                                فحص التحقق البشري (مكافحة الهجمات الآلية)
                              </span>
                              <button
                                type="button"
                                onClick={generateCaptcha}
                                className="hover:text-amber-200 flex items-center gap-1"
                                title="تحديث التحدي"
                              >
                                <RefreshCw className="w-3.5 h-3.5" />
                              </button>
                            </div>
                            <div className="flex items-center gap-3">
                              <div className="bg-gray-900/80 px-3 py-2 rounded-xl text-white font-mono font-bold tracking-wider text-sm border border-white/10">
                                {captchaChallenge.a} + {captchaChallenge.b} = ؟
                              </div>
                              <input
                                type="number"
                                required
                                value={captchaAnswer}
                                onChange={(e) => setCaptchaAnswer(e.target.value)}
                                placeholder="الناتج"
                                className="input-field py-2 text-center text-sm font-bold w-28 bg-white/95 dark:bg-gray-800/95"
                              />
                            </div>
                          </motion.div>
                        )}

                        {/* Remember / Trust this device */}
                        <div className="flex items-center justify-between pt-1">
                          <label className="flex items-center gap-2 cursor-pointer text-xs text-gray-300 hover:text-white transition-colors">
                            <input
                              type="checkbox"
                              checked={rememberDevice}
                              onChange={(e) => setRememberDevice(e.target.checked)}
                              className="rounded border-gray-600 text-primary-600 focus:ring-primary-500 bg-gray-800 w-4 h-4"
                            />
                            <span>توثيق هذا الجهاز كجهاز موثوق</span>
                          </label>
                          <Link
                            to="/forgot-password"
                            className="text-xs text-primary-300 hover:text-primary-200 transition-colors"
                          >
                            نسيت كلمة المرور؟
                          </Link>
                        </div>

                        <motion.div
                          initial={{ opacity: 0, y: 14 }}
                          animate={{ opacity: 1, y: 0 }}
                          transition={{ delay: 0.24, duration: 0.4, ease: easing }}
                        >
                          <button
                            type="submit"
                            disabled={loading}
                            className="btn-primary w-full flex items-center justify-center gap-2 py-3 shadow-lg shadow-primary-600/30"
                          >
                            {loading && <span className="w-4 h-4 border-2 border-white/40 border-t-white rounded-full animate-spin" />}
                            {loading ? 'جاري التحقق...' : 'تسجيل الدخول الآمن'}
                            {!loading && <ArrowLeft className="w-4 h-4" />}
                          </button>
                        </motion.div>

                        {/* Device Footprint & Hardware Identity Indicator */}
                        {deviceInfo && (
                          <motion.div
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            transition={{ delay: 0.4 }}
                            className="pt-2 border-t border-white/10"
                          >
                            <div className="p-2.5 rounded-xl bg-gray-900/40 border border-white/5 space-y-1.5 text-[11px] text-gray-400">
                              <div className="flex items-center justify-between text-gray-300">
                                <span className="flex items-center gap-1 font-semibold">
                                  <Monitor className="w-3.5 h-3.5 text-medical-400" />
                                  بصمة الجهاز والتحقق الجنائي
                                </span>
                                <span className="inline-flex items-center gap-1 text-emerald-400 text-[10px] bg-emerald-500/10 px-2 py-0.5 rounded-full">
                                  <CheckCircle2 className="w-3 h-3" />
                                  نشط ومراقب
                                </span>
                              </div>
                              <div className="grid grid-cols-2 gap-1 font-mono text-[10px]">
                                <div>نظام: <span className="text-gray-300">{deviceInfo.os_info}</span></div>
                                <div>متصفح: <span className="text-gray-300">{deviceInfo.browser_info}</span></div>
                                <div className="truncate" title={deviceInfo.mac_address}>
                                  MAC: <span className="text-gray-300">{deviceInfo.mac_address || 'محمي'}</span>
                                </div>
                                <div className="truncate" title={deviceInfo.device_fingerprint}>
                                  ID: <span className="text-gray-300">{deviceInfo.device_fingerprint.slice(0, 10)}...</span>
                                </div>
                              </div>
                            </div>
                          </motion.div>
                        )}
                      </motion.form>
                    ) : (
                      <motion.div
                        key="biometric-form"
                        className="space-y-4"
                        initial={{ opacity: 0, y: 16 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: -16 }}
                        transition={{ duration: 0.3, ease: easing }}
                      >
                        <div>
                          <label className="block text-sm font-semibold text-gray-700 dark:text-gray-200 mb-1.5">
                            البريد الإلكتروني
                          </label>
                          <div className="relative group">
                            <Mail className="input-icon group-focus-within:text-primary-500 dark:group-focus-within:text-primary-400" />
                            <input
                              type="email"
                              value={email}
                              onChange={(e) => setEmail(e.target.value)}
                              className="input-field pr-11 bg-white/95 text-gray-900 placeholder:text-gray-400 dark:bg-gray-800/95 dark:text-white"
                              placeholder="doctor@securemed.app"
                            />
                          </div>
                        </div>

                        {/* Fingerprint scanner visual */}
                        <div className="flex justify-center py-2">
                          <motion.div
                            className="relative w-28 h-28 rounded-full bg-gradient-to-br from-primary-500/20 to-medical-500/20 border border-primary-400/30 flex items-center justify-center"
                            whileHover={{ scale: 1.05 }}
                            whileTap={{ scale: 0.95 }}
                          >
                            <span className="absolute inset-0 rounded-full bg-primary-500/25 animate-pulse-ring" />
                            <span
                              className="absolute inset-0 rounded-full bg-medical-500/20 animate-pulse-ring"
                              style={{ animationDelay: '0.8s' }}
                            />
                            <motion.div
                              animate={loading ? { scale: [1, 1.15, 1] } : {}}
                              transition={{ repeat: Infinity, duration: 1.2 }}
                            >
                              {loading ? (
                                <ScanFace className="w-12 h-12 text-medical-300 animate-heartbeat" />
                              ) : (
                                <Fingerprint className="w-12 h-12 text-primary-300 animate-glow" />
                              )}
                            </motion.div>
                          </motion.div>
                        </div>

                        <button
                          onClick={handleBiometricLogin}
                          disabled={loading || !webauthnSupported}
                          className="btn-primary w-full flex items-center justify-center gap-3 py-3.5"
                        >
                          <Fingerprint className="w-5 h-5" />
                          {loading ? 'جاري المسح...' : 'تسجيل الدخول بالبصمة'}
                        </button>
                        <div className="p-3.5 bg-blue-50/90 dark:bg-primary-500/10 border border-blue-200/80 dark:border-primary-500/20 rounded-2xl">
                          <p className="text-xs text-blue-900 dark:text-primary-100 leading-relaxed">
                            <strong>WebAuthn (FIDO2):</strong> يطلب بصمتك عبر Windows Hello أو Touch ID.
                            البيانات البيومترية لا تغادر جهازك أبداً — يتم تخزين hash فقط.
                          </p>
                        </div>
                        <p className="text-xs text-gray-500 dark:text-gray-400 text-center">
                          يتطلب تفعيل البصمة مسبقاً من الملف الشخصي
                        </p>
                      </motion.div>
                    )}
                  </AnimatePresence>
                </motion.div>
              )}
            </AnimatePresence>
          </motion.div>

          <motion.p
            className="text-center text-xs text-gray-400/80 mt-6"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.5 }}
          >
            © 2026 SecureMed — مشروع مادة تصميم وهندسة البرمجيات الآمنة
          </motion.p>
        </div>
      </div>

      {/* ============ Hero image panel (desktop) ============ */}
      <motion.div
        className="hidden lg:block relative w-[46%] xl:w-[48%] overflow-hidden"
        initial={{ opacity: 0, x: -60 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 0.8, ease: easing }}
      >
        {/* Ken Burns animated medical image */}
        <motion.img
          src="/images/login-hero.jpg"
          alt="تقنية طبية رقمية"
          className="absolute inset-0 w-full h-full object-cover animate-ken-burns"
          initial={{ scale: 1.05 }}
          animate={{ scale: 1 }}
          transition={{ duration: 1.2, ease: easing }}
        />
        {/* Cinematic gradient overlays */}
        <div className="absolute inset-0 bg-gradient-to-l from-navy-900/85 via-primary-950/30 to-transparent" />
        <div className="absolute inset-0 bg-gradient-to-t from-navy-900/85 via-transparent to-primary-950/25" />

        {/* ECG line across the image */}
        <div className="absolute bottom-28 left-0 right-0">
          <ECGLine height={90} stroke="#5eead4" strokeWidth={2.8} opacity={0.85} duration={3.6} />
        </div>

        {/* Content overlay */}
        <div className="relative z-10 h-full flex flex-col justify-end p-10 xl:p-14">
          <motion.div
            initial={{ opacity: 0, y: 34 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.35, duration: 0.7, ease: easing }}
          >
            <h2 className="text-3xl xl:text-4xl font-black font-heading text-white leading-snug drop-shadow-xl">
              صحتكِ <span className="text-gradient-animated">بأمان</span>،
              <br />
              سجلاتك في متناول يدك
            </h2>
            <p className="text-primary-100/85 mt-3 max-w-md leading-relaxed">
              منصة موحّدة تربط الأطباء والمرضى بسجلات طبية مشفّرة، تنبيهات ذكية، ومساعد طبي مدعوم بالذكاء الاصطناعي.
            </p>
          </motion.div>

          {/* Floating feature chips */}
          <div className="mt-8 space-y-3">
            {heroFeatures.map((f, i) => (
              <motion.div
                key={f.title}
                className="glass-chip rounded-2xl p-3.5 flex items-center gap-3.5 max-w-sm hover:bg-white/20 transition-colors"
                initial={{ opacity: 0, x: -36 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.55 + i * 0.15, duration: 0.55, ease: easing }}
                whileHover={{ x: -6 }}
              >
                <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-primary-500/40 to-medical-500/40 border border-white/20 flex items-center justify-center shrink-0">
                  <f.icon className="w-5 h-5 text-medical-200" />
                </div>
                <div>
                  <p className="text-white text-sm font-bold">{f.title}</p>
                  <p className="text-primary-200/75 text-xs">{f.sub}</p>
                </div>
              </motion.div>
            ))}
          </div>

          {/* Live pulse indicator */}
          <motion.div
            className="mt-8 flex items-center gap-2 text-medical-300 text-xs"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 1.1 }}
          >
            <span className="relative flex h-2.5 w-2.5">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-medical-400 opacity-60" />
              <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-medical-400" />
            </span>
            النظام يعمل — تشفير نشط ومتصل بقاعدة بيانات آمنة
          </motion.div>
        </div>
      </motion.div>
    </div>
  );
}
