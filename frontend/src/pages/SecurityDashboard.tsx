import { useState } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import {
  Shield, Scan, AlertTriangle, CheckCircle, XCircle,
  Fingerprint, Lock, Cookie, Network, Bug, Activity, MonitorSmartphone, ScrollText, Settings,
  ShieldCheck, RefreshCw, Cpu, Server, Terminal, Check
} from 'lucide-react';
import { Link } from 'react-router-dom';
import { securityAPI } from '../api/client';
import toast from 'react-hot-toast';

export default function SecurityDashboard() {
  const [scanResult, setScanResult] = useState<any>(null);
  const [vulnResult, setVulnResult] = useState<any>(null);

  const { data: dashboardData, refetch, isLoading } = useQuery({
    queryKey: ['security-dashboard'],
    queryFn: () => securityAPI.dashboard(),
  });

  const portScanMutation = useMutation({
    mutationFn: (data: any) => securityAPI.portScan(data),
    onSuccess: (res) => {
      setScanResult(res.data);
      toast.success('اكتمل مسح المنافذ بنجاح');
    },
    onError: () => toast.error('فشل مسح المنافذ'),
  });

  const vulnScanMutation = useMutation({
    mutationFn: () => securityAPI.vulnScan(),
    onSuccess: (res) => {
      setVulnResult(res.data);
      toast.success('اكتمل فحص الثغرات الأمنية بنجاح');
    },
    onError: () => toast.error('فشل فحص الثغرات'),
  });

  const securityFeatures = [
    {
      icon: Cookie,
      title: 'وسم الكوكيز المحمي',
      description: 'HttpOnly + Secure + SameSite=Strict',
      status: 'active',
      requirement: '#1',
      details: 'عزل وحماية الكوكيز ومنع قراءتها عبر JavaScript وتثبيتها عبر قنوات SSL فقط',
    },
    {
      icon: Network,
      title: 'أداة مسح المنافذ',
      description: 'Port Scanner متقدم لرصد المنافذ المفتوحة والمخاطر',
      status: 'active',
      requirement: '#2',
      details: 'فحص اتصالات TCP المتوازية وكشف الخدمات النشطة على البنية التحتية',
    },
    {
      icon: Lock,
      title: 'وسم مشفر (Cryptographic Tokens)',
      description: 'JWT مع RS256 + تشفير AES-256 للبيانات',
      status: 'active',
      requirement: '#3',
      details: 'توقيع الشهادات غير المتماثل مع حماية سرية السجلات الطبية',
    },
    {
      icon: Bug,
      title: 'فاحص الثغرات الأمنية',
      description: 'OWASP Top 10 scanner مدمج في النظام',
      status: 'active',
      requirement: '#4',
      details: 'فحص آلي للحقن، التكوينات الخاطئة، الرؤوس الأمنية، وسياسات كلمات المرور',
    },
    {
      icon: Shield,
      title: 'جدار حماية قاعدة البيانات (WAF)',
      description: 'WAF Middleware + Prepared Statements',
      status: 'active',
      requirement: '#5',
      details: 'اعتراض طلبات SQLi, XSS, Path Traversal وعزل عناوين IP المشبوهة تلقائياً',
    },
    {
      icon: Activity,
      title: 'تشفير الاتصال DV↔DB',
      description: 'TLS 1.3 + SSL لقناة نقل البيانات المشفرة',
      status: 'active',
      requirement: '#6',
      details: 'تشفير الاتصال بين مخدم التطبيق وقاعدة البيانات ومصادقة الشهادات',
    },
  ];

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-black text-gray-900 dark:text-white flex items-center gap-3">
            <div className="p-2.5 bg-primary-600/10 dark:bg-primary-500/20 rounded-2xl text-primary-600 dark:text-primary-400">
              <ShieldCheck className="w-7 h-7" />
            </div>
            مركز القيادة والأمان السيبراني
          </h1>
          <p className="text-gray-500 dark:text-gray-400 text-sm mt-1">
            المراقبة الأمنية الشاملة والامتثال لمعايير الأمان الستة الصارمة وحماية البيانات الطبية
          </p>
        </div>

        <button
          onClick={() => refetch()}
          disabled={isLoading}
          className="btn-secondary self-start sm:self-auto text-xs flex items-center gap-2 py-2 px-4 shadow-sm"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
          تحديث حالة الأمان
        </button>
      </div>

      {/* Security Quick Links */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Link
          to="/security/devices"
          className="card hover:shadow-lg transition-all flex items-center gap-4 cursor-pointer group border border-gray-100 dark:border-gray-800"
        >
          <div className="w-12 h-12 bg-indigo-50 dark:bg-indigo-900/30 rounded-2xl flex items-center justify-center transition-transform group-hover:scale-110">
            <MonitorSmartphone className="w-6 h-6 text-indigo-600 dark:text-indigo-400" />
          </div>
          <div>
            <h3 className="font-bold text-gray-900 dark:text-white group-hover:text-primary-600 transition-colors">
              إدارة وبصمات الأجهزة
            </h3>
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">مراقبة الأجهزة المصرحة وحظر المشبوهة</p>
          </div>
        </Link>

        <Link
          to="/security/login-history"
          className="card hover:shadow-lg transition-all flex items-center gap-4 cursor-pointer group border border-gray-100 dark:border-gray-800"
        >
          <div className="w-12 h-12 bg-blue-50 dark:bg-blue-900/30 rounded-2xl flex items-center justify-center transition-transform group-hover:scale-110">
            <ScrollText className="w-6 h-6 text-blue-600 dark:text-blue-400" />
          </div>
          <div>
            <h3 className="font-bold text-gray-900 dark:text-white group-hover:text-primary-600 transition-colors">
              سجل محاولات الدخول
            </h3>
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">تتبع الجلسات وعناوين IP وعمليات 2FA</p>
          </div>
        </Link>

        <Link
          to="/security/settings"
          className="card hover:shadow-lg transition-all flex items-center gap-4 cursor-pointer group border border-gray-100 dark:border-gray-800"
        >
          <div className="w-12 h-12 bg-purple-50 dark:bg-purple-900/30 rounded-2xl flex items-center justify-center transition-transform group-hover:scale-110">
            <Settings className="w-6 h-6 text-purple-600 dark:text-purple-400" />
          </div>
          <div>
            <h3 className="font-bold text-gray-900 dark:text-white group-hover:text-primary-600 transition-colors">
              إعدادات المصادقة المتقدمة
            </h3>
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">المصادقة الثنائية والبصمة الحيوية WebAuthn</p>
          </div>
        </Link>
      </div>

      {/* Security Features Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {securityFeatures.map((feature) => (
          <div
            key={feature.title}
            className="card shadow-sm border border-gray-100 dark:border-gray-800 hover:border-primary-200 dark:hover:border-primary-800/60 transition-all flex flex-col justify-between"
          >
            <div>
              <div className="flex items-start justify-between mb-3">
                <div className="w-10 h-10 bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-100 dark:border-emerald-800 rounded-xl flex items-center justify-center">
                  <feature.icon className="w-5 h-5 text-emerald-600 dark:text-emerald-400" />
                </div>
                <span className="text-[11px] font-bold text-emerald-700 dark:text-emerald-300 bg-emerald-50 dark:bg-emerald-900/30 px-2.5 py-1 rounded-full border border-emerald-100 dark:border-emerald-800">
                  متطلب أمني {feature.requirement}
                </span>
              </div>
              <h3 className="font-bold text-gray-900 dark:text-white text-base">{feature.title}</h3>
              <p className="text-xs font-semibold text-primary-600 dark:text-primary-400 mt-1 font-mono">
                {feature.description}
              </p>
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-2 leading-relaxed">
                {feature.details}
              </p>
            </div>

            <div className="mt-4 pt-3 border-t border-gray-100 dark:border-gray-700/60 flex items-center justify-between text-xs">
              <div className="flex items-center gap-1.5 text-emerald-600 dark:text-emerald-400 font-semibold">
                <CheckCircle className="w-4 h-4" />
                <span>مفعلة وتعمل بالكامل</span>
              </div>
              <span className="text-[10px] text-gray-400 font-mono">ENFORCED</span>
            </div>
          </div>
        ))}
      </div>

      {/* Risk Score & Posture */}
      {dashboardData?.data?.vulnerability_scan && (
        <div className="card shadow-sm border border-gray-100 dark:border-gray-800 p-6">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-4">
            <div>
              <h2 className="font-bold text-lg text-gray-900 dark:text-white flex items-center gap-2">
                <Shield className="w-5 h-5 text-emerald-600 dark:text-emerald-400" />
                مؤشر النضج والمخاطر الأمنية للنظام
              </h2>
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                تقييم فوري شامل يعتمد على معايير OWASP وفحوصات السلامة المشفرة
              </p>
            </div>
            <div className="flex items-center gap-2 self-start sm:self-auto">
              <span className="text-xs text-gray-500 dark:text-gray-400 font-medium">مستوى الحماية:</span>
              <span className="text-2xl font-black text-emerald-600 dark:text-emerald-400">
                {Math.max(0, 100 - (dashboardData.data.vulnerability_scan.risk_score || 0))}%
              </span>
            </div>
          </div>

          <div className="w-full bg-gray-100 dark:bg-gray-700/50 rounded-full h-3.5 p-0.5 mb-5">
            <div
              className="bg-gradient-to-r from-emerald-500 via-primary-500 to-medical-500 h-2.5 rounded-full transition-all duration-500 shadow-sm"
              style={{
                width: `${Math.max(5, 100 - (dashboardData.data.vulnerability_scan.risk_score || 0))}%`,
              }}
            />
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
            {Object.entries(dashboardData.data.vulnerability_scan.summary || {}).map(([key, value]: any) => {
              const labelMap: Record<string, { label: string; color: string; bg: string }> = {
                critical: { label: 'حرج', color: 'text-red-600 dark:text-red-400', bg: 'bg-red-50 dark:bg-red-950/20' },
                high: { label: 'عالي', color: 'text-orange-600 dark:text-orange-400', bg: 'bg-orange-50 dark:bg-orange-950/20' },
                medium: { label: 'متوسط', color: 'text-amber-600 dark:text-amber-400', bg: 'bg-amber-50 dark:bg-amber-950/20' },
                low: { label: 'منخفض', color: 'text-blue-600 dark:text-blue-400', bg: 'bg-blue-50 dark:bg-blue-950/20' },
                info: { label: 'معلومات', color: 'text-gray-600 dark:text-gray-400', bg: 'bg-gray-50 dark:bg-gray-800/40' },
                total: { label: 'الإجمالي', color: 'text-gray-900 dark:text-white', bg: 'bg-gray-100 dark:bg-gray-700/40' },
              };
              const item = labelMap[key] || { label: key, color: 'text-gray-700', bg: 'bg-gray-50' };

              return (
                <div key={key} className={`text-center p-3 rounded-2xl border border-gray-100 dark:border-gray-700/60 ${item.bg}`}>
                  <div className={`text-2xl font-black ${item.color}`}>{value}</div>
                  <div className="text-xs font-semibold text-gray-500 dark:text-gray-400 mt-0.5">{item.label}</div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Security Scanning Tools (Port Scanner & Vulnerability Scanner) */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Port Scanner */}
        <div className="card shadow-sm border border-gray-100 dark:border-gray-800 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-4">
              <h2 className="font-bold text-gray-900 dark:text-white flex items-center gap-2">
                <Network className="w-5 h-5 text-primary-600 dark:text-primary-400" />
                أداة مسح المنافذ (Port Scanner)
              </h2>
              <button
                onClick={() => portScanMutation.mutate({ target: 'localhost' })}
                disabled={portScanMutation.isPending}
                className="btn-primary text-xs py-2 px-4 flex items-center gap-1.5"
              >
                <Scan className="w-3.5 h-3.5" />
                {portScanMutation.isPending ? 'جارٍ فحص المنافذ...' : 'تشغيل المسح المباشر'}
              </button>
            </div>

            {scanResult ? (
              <div className="space-y-3">
                <div className="grid grid-cols-3 gap-2 text-xs">
                  <div className="p-3 bg-gray-50 dark:bg-gray-800 rounded-xl">
                    <span className="text-gray-400 block mb-0.5">المضيف الهدف</span>
                    <strong className="text-gray-900 dark:text-white font-mono">{scanResult.target}</strong>
                  </div>
                  <div className="p-3 bg-gray-50 dark:bg-gray-800 rounded-xl">
                    <span className="text-gray-400 block mb-0.5">المنافذ المفتوحة</span>
                    <strong className="text-emerald-600 dark:text-emerald-400 font-bold">{scanResult.open_ports}</strong>
                  </div>
                  <div className="p-3 bg-gray-50 dark:bg-gray-800 rounded-xl">
                    <span className="text-gray-400 block mb-0.5">زمن الفحص</span>
                    <strong className="text-gray-900 dark:text-white">{scanResult.duration_seconds} ثانية</strong>
                  </div>
                </div>

                {scanResult.open_ports > 0 && (
                  <div className="mt-3">
                    <h3 className="text-xs font-bold text-gray-700 dark:text-gray-300 mb-2">المنافذ النشطة المكتشفة:</h3>
                    <div className="space-y-1.5 max-h-48 overflow-y-auto pr-1">
                      {scanResult.results
                        .filter((r: any) => r.state === 'open')
                        .map((port: any) => (
                          <div
                            key={port.port}
                            className="flex items-center justify-between p-2.5 bg-gray-50 dark:bg-gray-800/60 rounded-xl text-xs border border-gray-100 dark:border-gray-700"
                          >
                            <span className="font-mono font-bold text-gray-900 dark:text-white">Port {port.port}</span>
                            <span className="text-gray-500 dark:text-gray-400">{port.service}</span>
                            <span
                              className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                                port.risk_level === 'critical'
                                  ? 'bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300'
                                  : port.risk_level === 'high'
                                  ? 'bg-orange-100 text-orange-700 dark:bg-orange-900/40 dark:text-orange-300'
                                  : 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300'
                              }`}
                            >
                              {port.risk_level}
                            </span>
                          </div>
                        ))}
                    </div>
                  </div>
                )}

                <div className="p-3.5 bg-blue-50/70 dark:bg-blue-950/20 border border-blue-100 dark:border-blue-900/40 rounded-xl text-xs text-blue-900 dark:text-blue-300">
                  {scanResult.risk_assessment}
                </div>
              </div>
            ) : (
              <div className="text-center py-12 bg-gray-50 dark:bg-gray-800/40 rounded-2xl border border-dashed border-gray-200 dark:border-gray-700">
                <Network className="w-10 h-10 text-gray-300 dark:text-gray-600 mx-auto mb-2" />
                <p className="text-xs text-gray-500 dark:text-gray-400">
                  اضغط على "تشغيل المسح المباشر" لفحص منافذ البنية التحتية المحلية عبر مآخذ TCP
                </p>
              </div>
            )}
          </div>
        </div>

        {/* Vulnerability Scanner */}
        <div className="card shadow-sm border border-gray-100 dark:border-gray-800 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-4">
              <h2 className="font-bold text-gray-900 dark:text-white flex items-center gap-2">
                <Bug className="w-5 h-5 text-primary-600 dark:text-primary-400" />
                فاحص الثغرات الأمنية (OWASP Scanner)
              </h2>
              <button
                onClick={() => vulnScanMutation.mutate()}
                disabled={vulnScanMutation.isPending}
                className="btn-primary text-xs py-2 px-4 flex items-center gap-1.5"
              >
                <Scan className="w-3.5 h-3.5" />
                {vulnScanMutation.isPending ? 'جارٍ الفحص الأمني...' : 'بدء فحص الثغرات'}
              </button>
            </div>

            {vulnResult ? (
              <div className="space-y-3">
                <div className="grid grid-cols-2 gap-2 text-xs">
                  <div className="p-3 bg-gray-50 dark:bg-gray-800 rounded-xl">
                    <span className="text-gray-400 block mb-0.5">عدد الفحوصات الأمنية</span>
                    <strong className="text-gray-900 dark:text-white">{vulnResult.total_checks} اختبار</strong>
                  </div>
                  <div className="p-3 bg-gray-50 dark:bg-gray-800 rounded-xl">
                    <span className="text-gray-400 block mb-0.5">الثغرات المكتشفة</span>
                    <strong className="text-emerald-600 dark:text-emerald-400">{vulnResult.summary.total} ثغرة</strong>
                  </div>
                </div>

                <div className="grid grid-cols-5 gap-2 text-center">
                  {[
                    { key: 'critical', label: 'حرج', color: 'text-red-600 dark:text-red-400' },
                    { key: 'high', label: 'عالي', color: 'text-orange-600 dark:text-orange-400' },
                    { key: 'medium', label: 'متوسط', color: 'text-amber-600 dark:text-amber-400' },
                    { key: 'low', label: 'منخفض', color: 'text-blue-600 dark:text-blue-400' },
                    { key: 'info', label: 'معلومة', color: 'text-gray-500' },
                  ].map(({ key, label, color }) => (
                    <div key={key} className="p-2 bg-gray-50 dark:bg-gray-800 rounded-xl">
                      <div className={`text-base font-bold ${color}`}>
                        {(vulnResult.summary as any)[key]}
                      </div>
                      <div className="text-[11px] text-gray-400 mt-0.5">{label}</div>
                    </div>
                  ))}
                </div>

                {vulnResult.recommendations?.length > 0 && (
                  <div className="mt-3">
                    <h3 className="text-xs font-bold text-gray-700 dark:text-gray-300 mb-2">توصيات المعالجة:</h3>
                    <div className="space-y-1.5 max-h-40 overflow-y-auto pr-1">
                      {vulnResult.recommendations.map((rec: string, i: number) => (
                        <div
                          key={i}
                          className="p-2.5 bg-emerald-50/70 dark:bg-emerald-950/20 border border-emerald-200 dark:border-emerald-800/40 rounded-xl text-xs text-emerald-800 dark:text-emerald-300"
                        >
                          {rec}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <div className="text-center py-12 bg-gray-50 dark:bg-gray-800/40 rounded-2xl border border-dashed border-gray-200 dark:border-gray-700">
                <Bug className="w-10 h-10 text-gray-300 dark:text-gray-600 mx-auto mb-2" />
                <p className="text-xs text-gray-500 dark:text-gray-400">
                  اضغط على "بدء فحص الثغرات" للتحقق من امتثال النظام لمعايير OWASP وحماية الروابط والكوكيز
                </p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Biometric & Enterprise Encryption Status Banner */}
      <div className="card shadow-sm border border-gray-100 dark:border-gray-800 p-5">
        <h2 className="font-bold text-gray-900 dark:text-white text-base mb-4 flex items-center gap-2">
          <Fingerprint className="w-5 h-5 text-medical-600" />
          البنية التحتية للمصادقة البيومترية والتشفير المتقدم
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4">
          <div className="flex items-center gap-3.5 p-4 bg-emerald-50/60 dark:bg-emerald-950/20 border border-emerald-100 dark:border-emerald-900/40 rounded-2xl">
            <div className="w-10 h-10 bg-emerald-100 dark:bg-emerald-900/50 rounded-xl flex items-center justify-center text-emerald-600 dark:text-emerald-400">
              <Fingerprint className="w-6 h-6" />
            </div>
            <div>
              <p className="text-xs text-gray-500 dark:text-gray-400">المصادقة بالبصمة</p>
              <p className="text-sm font-bold text-emerald-700 dark:text-emerald-300 mt-0.5">WebAuthn FIDO2</p>
            </div>
          </div>

          <div className="flex items-center gap-3.5 p-4 bg-emerald-50/60 dark:bg-emerald-950/20 border border-emerald-100 dark:border-emerald-900/40 rounded-2xl">
            <div className="w-10 h-10 bg-emerald-100 dark:bg-emerald-900/50 rounded-xl flex items-center justify-center text-emerald-600 dark:text-emerald-400">
              <Lock className="w-6 h-6" />
            </div>
            <div>
              <p className="text-xs text-gray-500 dark:text-gray-400">تشفير الحقول السريرية</p>
              <p className="text-sm font-bold text-emerald-700 dark:text-emerald-300 mt-0.5">AES-256 Fernet</p>
            </div>
          </div>

          <div className="flex items-center gap-3.5 p-4 bg-emerald-50/60 dark:bg-emerald-950/20 border border-emerald-100 dark:border-emerald-900/40 rounded-2xl">
            <div className="w-10 h-10 bg-emerald-100 dark:bg-emerald-900/50 rounded-xl flex items-center justify-center text-emerald-600 dark:text-emerald-400">
              <Activity className="w-6 h-6" />
            </div>
            <div>
              <p className="text-xs text-gray-500 dark:text-gray-400">قناة الاتصال المشفرة</p>
              <p className="text-sm font-bold text-emerald-700 dark:text-emerald-300 mt-0.5">TLS 1.3 / SSL</p>
            </div>
          </div>

          <div className="flex items-center gap-3.5 p-4 bg-emerald-50/60 dark:bg-emerald-950/20 border border-emerald-100 dark:border-emerald-900/40 rounded-2xl">
            <div className="w-10 h-10 bg-emerald-100 dark:bg-emerald-900/50 rounded-xl flex items-center justify-center text-emerald-600 dark:text-emerald-400">
              <Shield className="w-6 h-6" />
            </div>
            <div>
              <p className="text-xs text-gray-500 dark:text-gray-400">جدار حماية WAF</p>
              <p className="text-sm font-bold text-emerald-700 dark:text-emerald-300 mt-0.5">Active Defense</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
