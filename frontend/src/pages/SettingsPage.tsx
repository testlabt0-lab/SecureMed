import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { motion } from 'framer-motion';
import {
  Settings, User, Shield, Bell, Monitor, Key, Smartphone,
  Eye, EyeOff, Save, AlertCircle, CheckCircle2, Trash2,
  LogOut, QrCode, Copy, ToggleLeft, ToggleRight, Clock,
  Moon, Sun, Globe, Lock, ChevronRight,
} from 'lucide-react';
import toast from 'react-hot-toast';
import { authAPI, usersAPI } from '../api/client';
import { settingsAPI } from '../api/extendedApis';
import { enrollBiometric, isBiometricAvailable } from '../utils/webauthn';
import { useAuthStore } from '../store/authStore';
import { useThemeStore } from '../store/themeStore';
import { roleLabel } from '../constants/roles';

// ─── Tabs ─────────────────────────────────────────────────────────────────────

type Tab = 'account' | 'security' | 'notifications' | 'sessions' | 'appearance';

const TABS: { id: Tab; label: string; icon: React.ElementType }[] = [
  { id: 'account',       label: 'الحساب',      icon: User },
  { id: 'security',      label: 'الأمان',       icon: Shield },
  { id: 'notifications', label: 'الإشعارات',   icon: Bell },
  { id: 'sessions',      label: 'الجلسات',      icon: Monitor },
  { id: 'appearance',    label: 'المظهر',       icon: Moon },
];

// ─── Account Tab ──────────────────────────────────────────────────────────────

function AccountTab() {
  const { user, setAuth, tokens } = useAuthStore();
  const [form, setForm] = useState({
    full_name: user?.full_name || '',
    phone: user?.phone || '',
    department: user?.department || '',
    specialization: user?.specialization || '',
  });
  const qc = useQueryClient();

  const updateMutation = useMutation({
    mutationFn: (data: any) => usersAPI.update(user!.id, data),
    onSuccess: (res) => {
      toast.success('تم حفظ البيانات بنجاح');
      setAuth({ ...user!, ...res.data }, tokens!);
    },
    onError: () => toast.error('فشل الحفظ'),
  });

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-semibold text-white mb-1">معلومات الحساب</h3>
        <p className="text-sm text-gray-400">تعديل بياناتك الشخصية والمهنية</p>
      </div>

      {/* Avatar */}
      <div className="flex items-center gap-4">
        <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-primary-500 to-indigo-600 flex items-center justify-center text-white text-2xl font-bold shadow-lg shadow-primary-500/30">
          {(user?.full_name || 'U')[0].toUpperCase()}
        </div>
        <div>
          <p className="font-semibold text-white">{user?.full_name}</p>
          <p className="text-sm text-gray-400">{user?.email}</p>
          {/* roleLabel, not user.role: this rendered the raw backend code, so the
              account card read 'LAB_TECH' while the sidebar under it read
              'فني مختبر' for the same person. */}
          <p className="text-xs text-primary-400 mt-0.5">{roleLabel(user?.role)}</p>
        </div>
      </div>

      {/* Form */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {[
          { key: 'full_name', label: 'الاسم الكامل', type: 'text' },
          { key: 'phone', label: 'رقم الهاتف', type: 'tel' },
          { key: 'department', label: 'القسم', type: 'text' },
          { key: 'specialization', label: 'التخصص', type: 'text' },
        ].map(field => (
          <div key={field.key}>
            <label className="block text-sm text-gray-400 mb-1">{field.label}</label>
            <input
              type={field.type}
              value={(form as any)[field.key]}
              onChange={e => setForm(f => ({ ...f, [field.key]: e.target.value }))}
              className="w-full bg-white/5 border border-white/10 rounded-xl px-3 py-2.5 text-sm text-white focus:outline-none focus:border-primary-500 transition-colors"
            />
          </div>
        ))}
      </div>

      <div className="flex justify-end">
        <button
          onClick={() => updateMutation.mutate(form)}
          disabled={updateMutation.isPending}
          className="flex items-center gap-2 bg-primary-600 hover:bg-primary-700 text-white px-6 py-2.5 rounded-xl text-sm font-medium transition-colors disabled:opacity-50"
        >
          <Save className="w-4 h-4" />
          {updateMutation.isPending ? 'جاري الحفظ...' : 'حفظ التغييرات'}
        </button>
      </div>
    </div>
  );
}

// ─── Security Tab ─────────────────────────────────────────────────────────────

function SecurityTab() {
  const { user, updateUser } = useAuthStore();
  const queryClient = useQueryClient();
  const [showOld, setShowOld] = useState(false);
  const [showNew, setShowNew] = useState(false);
  const [pwForm, setPwForm] = useState({ old_password: '', new_password: '', confirm_password: '' });

  const pwMutation = useMutation({
    mutationFn: (data: any) => authAPI.changePassword(data),
    onSuccess: () => {
      toast.success('تم تغيير كلمة المرور بنجاح');
      setPwForm({ old_password: '', new_password: '', confirm_password: '' });
    },
    onError: (err: any) => {
      const detail = err?.response?.data?.detail || err?.response?.data?.old_password?.[0] || 'فشل التغيير';
      toast.error(detail);
    },
  });

  const { data: totpRes } = useQuery({
    queryKey: ['totp-status'],
    queryFn: () => settingsAPI.totpStatus(),
  });
  const totpEnabled = totpRes?.data?.mfa_enabled || (user as any)?.mfa_enabled || (user as any)?.two_factor_enabled;

  // /auth/2fa/setup/ generates and stores a fresh secret server-side, so firing it
  // without ever showing the QR left the user with a rotated secret, no way to scan
  // it and a button that did nothing visible. Hold the response and render it.
  const [totpSetup, setTotpSetup] = useState<{ secret: string; otpauth_url: string; qr_image: string } | null>(null);
  const [totpCode, setTotpCode] = useState('');

  const setupTotpMutation = useMutation({
    mutationFn: () => settingsAPI.totpSetup(),
    onSuccess: (res) => {
      setTotpSetup(res.data);
      setTotpCode('');
      toast.success('افتح تطبيق المصادقة وامسح الرمز');
    },
    onError: (err: any) => toast.error(err?.response?.data?.detail || 'فشل إعداد المصادقة الثنائية'),
  });

  const verifyTotpMutation = useMutation({
    mutationFn: (code: string) => settingsAPI.totpVerify(code),
    onSuccess: () => {
      setTotpSetup(null);
      setTotpCode('');
      queryClient.invalidateQueries({ queryKey: ['totp-status'] });
      toast.success('تم تفعيل التحقق بخطوتين');
    },
    onError: (err: any) => toast.error(err?.response?.data?.detail || 'الرمز غير صحيح'),
  });

  // Previously declared and never rendered, so this panel could turn 2FA on but not
  // off — the user had to find a different page to disable it. The server requires a
  // valid TOTP code to disable, hence the same six-digit input as the enable step.
  const [showTotpDisable, setShowTotpDisable] = useState(false);

  const disableTotpMutation = useMutation({
    mutationFn: (code: string) => settingsAPI.totpDisable(code),
    onSuccess: () => {
      setShowTotpDisable(false);
      setTotpCode('');
      queryClient.invalidateQueries({ queryKey: ['totp-status'] });
      toast.success('تم تعطيل التحقق بخطوتين');
    },
    onError: (err: any) => toast.error(err?.response?.data?.detail || 'الرمز غير صحيح'),
  });

  // Biometrics. This section used to be a paragraph telling the user to go to the
  // profile page to enrol — the only screen that could actually run the ceremony
  // was /security/settings, so two of the three security panels were dead ends.
  // enrollBiometric() owns the whole WebAuthn ceremony, so calling it here adds no
  // duplicate protocol code.
  const [webauthnSupported, setWebauthnSupported] = useState<boolean | null>(null);
  useEffect(() => {
    isBiometricAvailable().then(setWebauthnSupported).catch(() => setWebauthnSupported(false));
  }, []);

  const enrollMutation = useMutation({
    mutationFn: async () => {
      const result = await enrollBiometric();
      if (!result.success) throw new Error(result.error || 'فشل تسجيل البصمة');
    },
    onSuccess: () => {
      // is_biometric_enabled comes from the user serializer, so the badge above
      // stays stale until the store is updated — SecuritySettings never did this
      // and left the page claiming "غير مفعّلة" right after a successful enrolment.
      updateUser({ is_biometric_enabled: true });
      toast.success('تم تسجيل البصمة على هذا الجهاز');
    },
    onError: (err: any) => toast.error(err?.message || 'فشل تسجيل البصمة'),
  });

  return (
    <div className="space-y-6">
      {/* Change Password */}
      <section className="bg-white/5 border border-white/10 rounded-2xl p-5">
        <div className="flex items-center gap-2 mb-4">
          <Key className="w-5 h-5 text-primary-400" />
          <h3 className="font-semibold text-white">تغيير كلمة المرور</h3>
        </div>
        <div className="space-y-3">
          {[
            { key: 'old_password', label: 'كلمة المرور الحالية', show: showOld, toggle: setShowOld },
            { key: 'new_password', label: 'كلمة المرور الجديدة', show: showNew, toggle: setShowNew },
            { key: 'confirm_password', label: 'تأكيد كلمة المرور الجديدة', show: showNew, toggle: setShowNew },
          ].map(field => (
            <div key={field.key} className="relative">
              <label className="block text-xs text-gray-400 mb-1">{field.label}</label>
              <input
                type={field.show ? 'text' : 'password'}
                value={(pwForm as any)[field.key]}
                onChange={e => setPwForm(f => ({ ...f, [field.key]: e.target.value }))}
                className="w-full bg-white/5 border border-white/10 rounded-xl px-3 py-2.5 pr-10 text-sm text-white focus:outline-none focus:border-primary-500 transition-colors"
              />
              <button
                type="button"
                onClick={() => field.toggle(!field.show)}
                className="absolute left-3 top-[calc(50%+10px)] -translate-y-1/2 text-gray-500 hover:text-gray-300"
              >
                {field.show ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
          ))}
        </div>
        <button
          onClick={() => pwMutation.mutate(pwForm)}
          disabled={pwMutation.isPending || !pwForm.old_password || !pwForm.new_password}
          className="mt-4 flex items-center gap-2 bg-primary-600 hover:bg-primary-700 text-white px-5 py-2 rounded-xl text-sm font-medium transition-colors disabled:opacity-50"
        >
          <Lock className="w-4 h-4" />
          {pwMutation.isPending ? 'جاري التغيير...' : 'تغيير كلمة المرور'}
        </button>
      </section>

      {/* 2FA */}
      <section className="bg-white/5 border border-white/10 rounded-2xl p-5">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <Smartphone className="w-5 h-5 text-emerald-400" />
            <div>
              <h3 className="font-semibold text-white">التحقق بخطوتين (2FA)</h3>
              <p className="text-xs text-gray-500 mt-0.5">حماية إضافية باستخدام تطبيق Google Authenticator</p>
            </div>
          </div>
          <span className={`text-xs px-2 py-1 rounded-full ${totpEnabled ? 'bg-emerald-500/20 text-emerald-400' : 'bg-gray-500/20 text-gray-400'}`}>
            {totpEnabled ? 'مفعّل' : 'معطّل'}
          </span>
        </div>

        {!totpEnabled ? (
          totpSetup ? (
            <div className="space-y-4">
              <p className="text-sm text-gray-400">
                امسح الرمز بتطبيق المصادقة ثم أدخل الرمز المؤقت لتأكيد التفعيل.
              </p>
              {/* qr_image is a data: URI rendered by the server. The provisioning URI
                  carries the shared secret, so it must never be handed to an external
                  QR service. */}
              <div className="flex justify-center bg-white p-4 rounded-xl w-fit mx-auto">
                <img src={totpSetup.qr_image} alt="رمز QR للمصادقة الثنائية" className="w-44 h-44" />
              </div>
              <div className="flex items-center gap-2">
                <code className="flex-1 bg-black/30 border border-white/10 rounded-xl px-3 py-2 text-xs font-mono text-center tracking-wider text-gray-200 select-all">
                  {totpSetup.secret}
                </code>
                <button
                  type="button"
                  onClick={() => { navigator.clipboard.writeText(totpSetup.secret); toast.success('تم النسخ'); }}
                  className="p-2 bg-white/5 hover:bg-white/10 rounded-xl text-gray-300 transition-colors"
                  title="نسخ الرمز السري"
                >
                  <Copy className="w-4 h-4" />
                </button>
              </div>
              <div className="flex items-center gap-2">
                <input
                  value={totpCode}
                  onChange={e => setTotpCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
                  inputMode="numeric"
                  placeholder="000000"
                  className="flex-1 bg-white/5 border border-white/10 rounded-xl px-3 py-2.5 text-sm text-white text-center tracking-[0.4em] focus:outline-none focus:border-emerald-500 transition-colors"
                />
                <button
                  onClick={() => verifyTotpMutation.mutate(totpCode)}
                  disabled={totpCode.length !== 6 || verifyTotpMutation.isPending}
                  className="bg-emerald-600/80 hover:bg-emerald-600 text-white px-4 py-2.5 rounded-xl text-sm font-medium transition-colors disabled:opacity-50"
                >
                  تأكيد
                </button>
              </div>
              <button
                onClick={() => { setTotpSetup(null); setTotpCode(''); }}
                className="text-xs text-gray-500 hover:text-gray-300 transition-colors"
              >
                إلغاء
              </button>
            </div>
          ) : (
            <button
              onClick={() => setupTotpMutation.mutate()}
              disabled={setupTotpMutation.isPending}
              className="flex items-center gap-2 bg-emerald-600/80 hover:bg-emerald-600 text-white px-4 py-2 rounded-xl text-sm font-medium transition-colors disabled:opacity-50"
            >
              <QrCode className="w-4 h-4" />
              تفعيل التحقق بخطوتين
            </button>
          )
        ) : (
          <div className="space-y-3">
            <div className="flex items-center gap-2 text-sm text-gray-400">
              <CheckCircle2 className="w-4 h-4 text-emerald-400" />
              التحقق بخطوتين مفعّل ويحمي حسابك.
            </div>

            {!showTotpDisable ? (
              <button
                onClick={() => { setShowTotpDisable(true); setTotpCode(''); }}
                className="text-xs text-red-400 hover:text-red-300 transition-colors"
              >
                تعطيل التحقق بخطوتين
              </button>
            ) : (
              <div className="space-y-2 pt-1 border-t border-white/10">
                <p className="text-xs text-amber-400 pt-2">
                  التعطيل يُضعف حماية حسابك. أدخل رمزاً حالياً من تطبيق المصادقة للتأكيد.
                </p>
                <div className="flex items-center gap-2">
                  <input
                    value={totpCode}
                    onChange={e => setTotpCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
                    inputMode="numeric"
                    placeholder="000000"
                    className="flex-1 bg-white/5 border border-white/10 rounded-xl px-3 py-2.5 text-sm text-white text-center tracking-[0.4em] focus:outline-none focus:border-red-500 transition-colors"
                  />
                  <button
                    onClick={() => disableTotpMutation.mutate(totpCode)}
                    disabled={totpCode.length !== 6 || disableTotpMutation.isPending}
                    className="bg-red-600/80 hover:bg-red-600 text-white px-4 py-2.5 rounded-xl text-sm font-medium transition-colors disabled:opacity-50"
                  >
                    تعطيل
                  </button>
                </div>
                <button
                  onClick={() => { setShowTotpDisable(false); setTotpCode(''); }}
                  className="text-xs text-gray-500 hover:text-gray-300 transition-colors"
                >
                  إلغاء
                </button>
              </div>
            )}
          </div>
        )}
      </section>

      {/* Biometric */}
      <section className="bg-white/5 border border-white/10 rounded-2xl p-5">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2">
            <Shield className="w-5 h-5 text-purple-400" />
            <h3 className="font-semibold text-white">المصادقة البيومترية</h3>
          </div>
          <span className={`text-xs px-2 py-1 rounded-full ${user?.is_biometric_enabled ? 'bg-purple-500/20 text-purple-300' : 'bg-gray-500/20 text-gray-400'}`}>
            {user?.is_biometric_enabled ? 'مفعّلة' : 'معطّلة'}
          </span>
        </div>
        <p className="text-sm text-gray-400 mb-3">
          تسجيل الدخول بالبصمة أو Face ID أو Windows Hello. التسجيل يخص هذا الجهاز
          والمتصفح الحالي فقط، ويلزم تكراره على كل جهاز تريد الدخول منه.
        </p>

        {webauthnSupported === false ? (
          <div className="text-xs px-3 py-2 rounded-lg bg-gray-500/10 text-gray-400">
            هذا المتصفح أو الجهاز لا يدعم المصادقة البيومترية (WebAuthn).
          </div>
        ) : (
          <div className="flex flex-wrap items-center gap-3">
            <button
              onClick={() => enrollMutation.mutate()}
              disabled={enrollMutation.isPending || webauthnSupported === null}
              className="flex items-center gap-2 bg-purple-600/80 hover:bg-purple-600 text-white px-4 py-2 rounded-xl text-sm font-medium transition-colors disabled:opacity-50"
            >
              <Smartphone className="w-4 h-4" />
              {enrollMutation.isPending ? 'جاري التسجيل...' : 'تسجيل هذا الجهاز'}
            </button>
            <Link to="/profile" className="text-xs text-gray-400 hover:text-gray-200 transition-colors">
              إدارة الأجهزة المسجّلة وسحب صلاحياتها
            </Link>
          </div>
        )}
      </section>
    </div>
  );
}

// ─── Notifications Tab ────────────────────────────────────────────────────────

/**
 * The nine toggles this tab used to show (email_critical, push_high,
 * weekly_digest, ...) do not exist on the server: NotificationPreference stores
 * per-category flags, not per-severity ones. Nothing was ever loaded, and "حفظ
 * التفضيلات" only fired a success toast — a user who turned security alerts off
 * was told it saved while the server kept mailing them. These are the real
 * fields, from backend/apps/notifications/serializers.py.
 *
 * Who enforces what (backend/apps/notifications/utils.py::send_notification):
 *  - email_*      → the server checks these before sending mail.
 *  - quiet_hours_* → the server suppresses mail inside the window. There was no
 *                    way to set them from the UI at all, so the feature was dead.
 *  - push_* / in_app_all → the server stores them and never reads them; the row
 *                    is always created and the browser notification is decided
 *                    client-side in components/Layout.tsx, which now honours
 *                    these two so the toggles are not decoration.
 */
type PrefKey =
  | 'email_channel_updates' | 'email_security_alerts' | 'email_medical_records'
  | 'push_channel_updates' | 'push_security_alerts' | 'push_medical_records'
  | 'in_app_all';

type NotificationPrefs = Record<PrefKey, boolean>;

/** Mirrors the model defaults so the first paint matches a fresh server row. */
const defaultPrefs: NotificationPrefs = {
  email_channel_updates: true,
  email_security_alerts: true,
  email_medical_records: false,
  push_channel_updates: true,
  push_security_alerts: true,
  push_medical_records: true,
  in_app_all: true,
};

const PREF_KEYS = Object.keys(defaultPrefs) as PrefKey[];

const emailPrefRows: { key: PrefKey; label: string; sub?: string }[] = [
  { key: 'email_channel_updates', label: 'تحديثات القنوات', sub: 'الدعوات والتحديثات والإغلاق' },
  { key: 'email_security_alerts', label: 'تنبيهات الأمان', sub: 'محاولات دخول مشبوهة وأحداث أمنية' },
  { key: 'email_medical_records', label: 'السجلات الطبية', sub: 'إضافة سجل طبي جديد لمريض' },
];

const pushPrefRows: { key: PrefKey; label: string; sub?: string }[] = [
  { key: 'push_channel_updates', label: 'تحديثات القنوات' },
  { key: 'push_security_alerts', label: 'تنبيهات الأمان' },
  { key: 'push_medical_records', label: 'السجلات الطبية' },
];

function NotificationsTab() {
  const qc = useQueryClient();
  const [prefs, setPrefs] = useState<NotificationPrefs>(defaultPrefs);
  // TimeField serialises as 'HH:MM:SS' and accepts 'HH:MM'; '' means "no window",
  // which has to go to the server as null, not as an empty string.
  const [quietStart, setQuietStart] = useState('');
  const [quietEnd, setQuietEnd] = useState('');
  const [dirty, setDirty] = useState(false);

  const { data: prefsRes, isLoading } = useQuery({
    queryKey: ['notification-prefs'],
    queryFn: () => settingsAPI.notificationPrefs(),
  });

  // Server values win until the user touches a control; without the `dirty`
  // guard a background refetch would revert edits mid-session.
  useEffect(() => {
    const d = prefsRes?.data;
    if (!d || dirty) return;
    const next = { ...defaultPrefs };
    // Copy only the keys this tab owns, so `id`/`user` never ride along into the
    // PATCH body and an added server field cannot leak in untyped.
    PREF_KEYS.forEach(k => { if (typeof d[k] === 'boolean') next[k] = d[k]; });
    setPrefs(next);
    setQuietStart((d.quiet_hours_start || '').slice(0, 5));
    setQuietEnd((d.quiet_hours_end || '').slice(0, 5));
  }, [prefsRes, dirty]);

  const toggle = (key: PrefKey) => {
    setPrefs(p => ({ ...p, [key]: !p[key] }));
    setDirty(true);
  };

  const quietIncomplete = (!!quietStart) !== (!!quietEnd);

  const saveMutation = useMutation({
    mutationFn: () => settingsAPI.updateNotificationPrefs({
      ...prefs,
      quiet_hours_start: quietStart || null,
      quiet_hours_end: quietEnd || null,
    }),
    onSuccess: () => {
      setDirty(false);
      qc.invalidateQueries({ queryKey: ['notification-prefs'] });
      toast.success('تم حفظ تفضيلات الإشعارات');
    },
    onError: (err: any) =>
      toast.error(err?.response?.data?.detail || 'فشل حفظ التفضيلات'),
  });

  const ToggleSwitch = ({ k }: { k: PrefKey }) => (
    <button
      onClick={() => toggle(k)}
      disabled={isLoading}
      className="flex-shrink-0 disabled:opacity-40"
      aria-pressed={prefs[k]}
    >
      {prefs[k]
        ? <ToggleRight className="w-8 h-8 text-primary-500" />
        : <ToggleLeft className="w-8 h-8 text-gray-600" />}
    </button>
  );

  const Row = ({ label, sub, k }: { label: string; sub?: string; k: PrefKey }) => (
    <div className="flex items-center justify-between py-3 border-b border-white/5 last:border-0">
      <div>
        <p className="text-sm text-white">{label}</p>
        {sub && <p className="text-xs text-gray-500">{sub}</p>}
      </div>
      <ToggleSwitch k={k} />
    </div>
  );

  return (
    <div className="space-y-5">
      <section className="bg-white/5 border border-white/10 rounded-2xl p-5">
        <h3 className="font-semibold text-white mb-1 flex items-center gap-2">
          <Bell className="w-4 h-4 text-primary-400" /> إشعارات البريد الإلكتروني
        </h3>
        <p className="text-xs text-gray-500 mb-2">يطبّقها الخادم قبل إرسال أي رسالة.</p>
        {emailPrefRows.map(r => (
          <Row key={r.key} label={r.label} sub={r.sub} k={r.key} />
        ))}
      </section>

      <section className="bg-white/5 border border-white/10 rounded-2xl p-5">
        <h3 className="font-semibold text-white mb-1 flex items-center gap-2">
          <Clock className="w-4 h-4 text-amber-400" /> ساعات الهدوء
        </h3>
        <p className="text-xs text-gray-500 mb-3">
          لا تُرسل رسائل البريد داخل هذه الفترة. اتركها فارغة لتعطيلها.
        </p>
        <div className="flex items-center gap-3">
          <label className="text-xs text-gray-400">
            من
            <input
              type="time"
              value={quietStart}
              onChange={e => { setQuietStart(e.target.value); setDirty(true); }}
              className="block mt-1 bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm text-white"
            />
          </label>
          <label className="text-xs text-gray-400">
            إلى
            <input
              type="time"
              value={quietEnd}
              onChange={e => { setQuietEnd(e.target.value); setDirty(true); }}
              className="block mt-1 bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm text-white"
            />
          </label>
        </div>
        {quietIncomplete && (
          <p className="text-xs text-amber-400 mt-2">
            الفترة تحتاج وقت بداية ونهاية معاً، وإلا تُهمل.
          </p>
        )}
      </section>

      <section className="bg-white/5 border border-white/10 rounded-2xl p-5">
        <h3 className="font-semibold text-white mb-1 flex items-center gap-2">
          <Monitor className="w-4 h-4 text-emerald-400" /> تنبيهات المتصفح
        </h3>
        <p className="text-xs text-gray-500 mb-2">
          تُطبَّق في هذا المتصفح على التنبيهات المنبثقة فقط؛ سجل الإشعارات يبقى كاملاً.
        </p>
        {pushPrefRows.map(r => (
          <Row key={r.key} label={r.label} sub={r.sub} k={r.key} />
        ))}
        <Row
          label="إيقاف كل التنبيهات المنبثقة"
          sub="تعطيل هذا الخيار يكتم المنبثقات كلها مهما كانت الخيارات أعلاه"
          k="in_app_all"
        />
      </section>

      <button
        onClick={() => saveMutation.mutate()}
        disabled={!dirty || saveMutation.isPending}
        className="flex items-center gap-2 bg-primary-600 hover:bg-primary-700 text-white px-5 py-2.5 rounded-xl text-sm font-medium transition-colors disabled:opacity-50"
      >
        <Save className="w-4 h-4" />
        {saveMutation.isPending ? 'يتم الحفظ...' : 'حفظ التفضيلات'}
      </button>
    </div>
  );
}

// ─── Sessions Tab ─────────────────────────────────────────────────────────────

function SessionsTab() {
  const { logout } = useAuthStore();
  const qc = useQueryClient();

  const { data: sessionsRes, isLoading } = useQuery({
    queryKey: ['active-sessions'],
    queryFn: () => settingsAPI.sessions(),
  });
  const sessions = sessionsRes?.data?.sessions || [];

  const revokeAll = useMutation({
    mutationFn: () => settingsAPI.revokeAllSessions(),
    onSuccess: () => {
      toast.success('تم إنهاء جميع الجلسات');
      logout();
    },
    onError: () => toast.error('فشل إنهاء الجلسات'),
  });

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="font-semibold text-white">الجلسات النشطة</h3>
          <p className="text-xs text-gray-400 mt-0.5">الأجهزة المسجّلة حالياً في حسابك</p>
        </div>
        <button
          onClick={() => revokeAll.mutate()}
          disabled={revokeAll.isPending}
          className="flex items-center gap-1.5 text-red-400 hover:text-red-300 text-sm border border-red-500/30 hover:border-red-500/50 px-3 py-1.5 rounded-xl transition-colors"
        >
          <LogOut className="w-4 h-4" /> إنهاء الكل
        </button>
      </div>

      {isLoading ? (
        <p className="text-sm text-gray-500">جاري التحميل...</p>
      ) : sessions.length === 0 ? (
        <div className="bg-white/5 border border-white/10 rounded-2xl p-6 text-center">
          <Monitor className="w-8 h-8 text-gray-600 mx-auto mb-2" />
          <p className="text-sm text-gray-500">لا توجد جلسات نشطة أخرى</p>
        </div>
      ) : (
        <div className="space-y-3">
          {sessions.map((session: any, i: number) => (
            <div key={i} className="bg-white/5 border border-white/10 rounded-xl p-4 flex items-center gap-3">
              <Monitor className="w-8 h-8 text-gray-400 flex-shrink-0" />
              <div className="flex-1 min-w-0">
                <p className="text-sm text-white font-medium">{session.device || 'جهاز غير معروف'}</p>
                <p className="text-xs text-gray-400">{session.ip_address} • {session.location || 'موقع غير معروف'}</p>
                <p className="text-xs text-gray-500 flex items-center gap-1 mt-0.5">
                  <Clock className="w-3 h-3" />
                  آخر نشاط: {session.last_activity || 'الآن'}
                </p>
              </div>
              {session.current && (
                <span className="text-xs bg-emerald-500/20 text-emerald-400 px-2 py-0.5 rounded-full">الجلسة الحالية</span>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ─── Appearance Tab ───────────────────────────────────────────────────────────

function AppearanceTab() {
  const { theme, toggleTheme } = useThemeStore();

  return (
    <div className="space-y-5">
      <div>
        <h3 className="font-semibold text-white mb-1">المظهر</h3>
        <p className="text-sm text-gray-400">تخصيص مظهر التطبيق</p>
      </div>

      <div className="grid grid-cols-2 gap-3">
        {[
          { value: 'dark', label: 'داكن', icon: Moon, desc: 'وضع الليل' },
          { value: 'light', label: 'فاتح', icon: Sun, desc: 'وضع النهار' },
        ].map(t => (
          <button
            key={t.value}
            onClick={() => theme !== t.value && toggleTheme()}
            className={`
              p-4 rounded-2xl border-2 transition-all text-right
              ${theme === t.value
                ? 'border-primary-500 bg-primary-500/10'
                : 'border-white/10 bg-white/5 hover:bg-white/8'}
            `}
          >
            <t.icon className={`w-6 h-6 mb-2 ${theme === t.value ? 'text-primary-400' : 'text-gray-400'}`} />
            <p className={`font-semibold text-sm ${theme === t.value ? 'text-primary-300' : 'text-white'}`}>{t.label}</p>
            <p className="text-xs text-gray-500">{t.desc}</p>
          </button>
        ))}
      </div>

      <div className="bg-white/5 border border-white/10 rounded-2xl p-4">
        <div className="flex items-center gap-2 mb-2">
          <Globe className="w-4 h-4 text-gray-400" />
          <h4 className="text-sm font-medium text-white">اللغة</h4>
        </div>
        <div className="flex gap-2">
          <button className="px-4 py-2 bg-primary-600/30 text-primary-300 border border-primary-500/30 rounded-xl text-sm">العربية</button>
          <button className="px-4 py-2 bg-white/5 text-gray-400 border border-white/10 rounded-xl text-sm hover:bg-white/10 transition-colors">English</button>
        </div>
      </div>
    </div>
  );
}

// ─── Main Settings Page ───────────────────────────────────────────────────────

export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState<Tab>('account');

  const tabContent: Record<Tab, React.ReactNode> = {
    account: <AccountTab />,
    security: <SecurityTab />,
    notifications: <NotificationsTab />,
    sessions: <SessionsTab />,
    appearance: <AppearanceTab />,
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-white flex items-center gap-2">
          <Settings className="w-7 h-7 text-primary-400" />
          الإعدادات
        </h1>
        <p className="text-gray-400 text-sm mt-1">إدارة حسابك وتفضيلاتك وأمانك</p>
      </div>

      <div className="flex flex-col md:flex-row gap-6">
        {/* Sidebar tabs */}
        <nav className="md:w-52 flex md:flex-col gap-1 overflow-x-auto md:overflow-visible pb-2 md:pb-0">
          {TABS.map(tab => {
            const Icon = tab.icon;
            const active = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`
                  flex items-center gap-2.5 px-4 py-2.5 rounded-xl text-sm font-medium whitespace-nowrap transition-all
                  ${active
                    ? 'bg-primary-600 text-white shadow-lg shadow-primary-500/20'
                    : 'text-gray-400 hover:text-white hover:bg-white/5'}
                `}
              >
                <Icon className={`w-4 h-4 ${active ? 'text-white' : 'text-gray-500'}`} />
                {tab.label}
                {active && <ChevronRight className="w-3 h-3 mr-auto hidden md:block" />}
              </button>
            );
          })}
        </nav>

        {/* Content */}
        <div className="flex-1 min-w-0">
          <motion.div
            key={activeTab}
            initial={{ opacity: 0, x: 10 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.2 }}
          >
            {tabContent[activeTab]}
          </motion.div>
        </div>
      </div>
    </div>
  );
}
