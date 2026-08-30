import { useState } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import {
  Shield, Scan, AlertTriangle, CheckCircle, XCircle,
  Fingerprint, Lock, Cookie, Network, Bug, Activity
} from 'lucide-react';
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
      toast.success('اكتمل مسح المنافذ');
    },
    onError: () => toast.error('فشل المسح'),
  });

  const vulnScanMutation = useMutation({
    mutationFn: () => securityAPI.vulnScan(),
    onSuccess: (res) => {
      setVulnResult(res.data);
      toast.success('اكتمل فحص الثغرات');
    },
    onError: () => toast.error('فشل الفحص'),
  });

  const securityFeatures = [
    {
      icon: Cookie,
      title: 'وسم الكوكيز',
      description: 'HttpOnly + Secure + SameSite=Strict',
      status: 'active',
      requirement: '#1',
    },
    {
      icon: Network,
      title: 'أداة مسح المنافذ',
      description: 'Port Scanner مدمج للكشف عن المنافذ المفتوحة',
      status: 'active',
      requirement: '#2',
    },
    {
      icon: Lock,
      title: 'وسم مشفر',
      description: 'JWT مع RS256 + تشفير AES-256',
      status: 'active',
      requirement: '#3',
    },
    {
      icon: Bug,
      title: 'فاحص الثغرات',
      description: 'OWASP Top 10 scanner مدمج',
      status: 'active',
      requirement: '#4',
    },
    {
      icon: Shield,
      title: 'حماية قاعدة البيانات',
      description: 'WAF Middleware + Prepared Statements',
      status: 'active',
      requirement: '#5',
    },
    {
      icon: Activity,
      title: 'تشفير الاتصال DV↔DB',
      description: 'TLS 1.3 + SSL للاتصال بقاعدة البيانات',
      status: 'active',
      requirement: '#6',
    },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <Shield className="w-7 h-7 text-primary-600" />
          لوحة الأمان
        </h1>
        <p className="text-gray-600 text-sm mt-1">
          المراقبة الأمنية الشاملة - متطلبات الأمان الستة
        </p>
      </div>

      {/* Security Features Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {securityFeatures.map((feature) => (
          <div key={feature.title} className="card">
            <div className="flex items-start justify-between mb-3">
              <div className="w-10 h-10 bg-green-100 rounded-lg flex items-center justify-center">
                <feature.icon className="w-5 h-5 text-green-600" />
              </div>
              <span className="text-xs text-gray-400 bg-gray-100 px-2 py-1 rounded">
                متطلب {feature.requirement}
              </span>
            </div>
            <h3 className="font-bold text-gray-900">{feature.title}</h3>
            <p className="text-sm text-gray-600 mt-1">{feature.description}</p>
            <div className="mt-3 flex items-center gap-2 text-sm">
              <CheckCircle className="w-4 h-4 text-green-600" />
              <span className="font-medium text-green-700">مفعلة</span>
            </div>
          </div>
        ))}
      </div>

      {/* Risk Score */}
      {dashboardData?.data && (
        <div className="card">
          <h2 className="font-bold text-gray-900 mb-4">درجة المخاطر الأمنية</h2>
          <div className="flex items-center gap-6">
            <div className="flex-1">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm text-gray-600">المستوى الحالي</span>
                <span className="text-2xl font-bold text-green-600">
                  {100 - dashboardData.data.vulnerability_scan.risk_score}/100
                </span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-3">
                <div
                  className="bg-gradient-to-r from-green-500 to-medical-500 h-3 rounded-full transition-all"
                  style={{
                    width: `${100 - dashboardData.data.vulnerability_scan.risk_score}%`,
                  }}
                />
              </div>
            </div>
          </div>
          <div className="mt-4 grid grid-cols-2 md:grid-cols-5 gap-3 text-sm">
            {Object.entries(dashboardData.data.vulnerability_scan.summary).map(([key, value]: any) => (
              <div key={key} className="text-center p-2 bg-gray-50 rounded">
                <div className="text-xl font-bold text-gray-900">{value}</div>
                <div className="text-xs text-gray-500">
                  {key === 'critical' ? 'حرج' :
                   key === 'high' ? 'عالي' :
                   key === 'medium' ? 'متوسط' :
                   key === 'low' ? 'منخفض' :
                   key === 'info' ? 'معلومة' : 'الإجمالي'}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Security Tools */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Port Scanner */}
        <div className="card">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-bold flex items-center gap-2">
              <Network className="w-5 h-5 text-primary-600" />
              ماسح المنافذ
            </h2>
            <button
              onClick={() => portScanMutation.mutate({ target: 'localhost' })}
              disabled={portScanMutation.isPending}
              className="btn-primary text-sm flex items-center gap-2"
            >
              <Scan className="w-4 h-4" />
              {portScanMutation.isPending ? 'جاري المسح...' : 'بدء المسح'}
            </button>
          </div>
          {scanResult ? (
            <div className="space-y-3">
              <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                <span className="text-sm">الهدف:</span>
                <span className="font-medium">{scanResult.target}</span>
              </div>
              <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                <span className="text-sm">المنافذ المفتوحة:</span>
                <span className="font-bold text-orange-600">{scanResult.open_ports}</span>
              </div>
              <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                <span className="text-sm">مدة المسح:</span>
                <span className="font-medium">{scanResult.duration_seconds} ثانية</span>
              </div>
              {scanResult.open_ports > 0 && (
                <div className="mt-3">
                  <h3 className="text-sm font-bold mb-2">المنافذ المفتوحة:</h3>
                  <div className="space-y-1 max-h-40 overflow-y-auto">
                    {scanResult.results
                      .filter((r: any) => r.state === 'open')
                      .map((port: any) => (
                        <div
                          key={port.port}
                          className="flex items-center justify-between p-2 border border-gray-200 rounded text-sm"
                        >
                          <span className="font-mono">{port.port}</span>
                          <span className="text-gray-600">{port.service}</span>
                          <span className={`badge ${
                            port.risk_level === 'critical' ? 'badge-danger' :
                            port.risk_level === 'high' ? 'badge-warning' : 'badge-info'
                          }`}>
                            {port.risk_level}
                          </span>
                        </div>
                      ))}
                  </div>
                </div>
              )}
              <div className="p-3 bg-blue-50 rounded-lg text-sm text-blue-800">
                {scanResult.risk_assessment}
              </div>
            </div>
          ) : (
            <p className="text-center text-gray-500 py-8 text-sm">
              اضغط "بدء المسح" لفحص المنافذ
            </p>
          )}
        </div>

        {/* Vulnerability Scanner */}
        <div className="card">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-bold flex items-center gap-2">
              <Bug className="w-5 h-5 text-primary-600" />
              فاحص الثغرات الأمنية
            </h2>
            <button
              onClick={() => vulnScanMutation.mutate()}
              disabled={vulnScanMutation.isPending}
              className="btn-primary text-sm flex items-center gap-2"
            >
              <Scan className="w-4 h-4" />
              {vulnScanMutation.isPending ? 'جاري الفحص...' : 'بدء الفحص'}
            </button>
          </div>
          {vulnResult ? (
            <div className="space-y-3">
              <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                <span className="text-sm">عدد الفحوصات:</span>
                <span className="font-medium">{vulnResult.total_checks}</span>
              </div>
              <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                <span className="text-sm">الثغرات المكتشفة:</span>
                <span className="font-bold text-orange-600">{vulnResult.summary.total}</span>
              </div>
              <div className="grid grid-cols-5 gap-2 text-center">
                {[
                  { key: 'critical', label: 'حرج', color: 'text-red-600' },
                  { key: 'high', label: 'عالي', color: 'text-orange-600' },
                  { key: 'medium', label: 'متوسط', color: 'text-yellow-600' },
                  { key: 'low', label: 'منخفض', color: 'text-blue-600' },
                  { key: 'info', label: 'معلومة', color: 'text-gray-600' },
                ].map(({ key, label, color }) => (
                  <div key={key} className="p-2 bg-gray-50 rounded">
                    <div className={`text-lg font-bold ${color}`}>
                      {(vulnResult.summary as any)[key]}
                    </div>
                    <div className="text-xs text-gray-500">{label}</div>
                  </div>
                ))}
              </div>
              {vulnResult.recommendations.length > 0 && (
                <div className="mt-3">
                  <h3 className="text-sm font-bold mb-2">التوصيات:</h3>
                  <div className="space-y-2 max-h-40 overflow-y-auto">
                    {vulnResult.recommendations.map((rec: string, i: number) => (
                      <div key={i} className="p-2 bg-yellow-50 rounded text-xs text-yellow-800">
                        {rec}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ) : (
            <p className="text-center text-gray-500 py-8 text-sm">
              اضغط "بدء الفحص" للبحث عن ثغرات OWASP
            </p>
          )}
        </div>
      </div>

      {/* Biometric & Encryption Status */}
      <div className="card">
        <h2 className="font-bold mb-4">حالة المصادقة البيومترية والتشفير</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="flex items-center gap-3 p-3 bg-green-50 rounded-lg">
            <Fingerprint className="w-8 h-8 text-green-600" />
            <div>
              <p className="text-sm font-bold">المصادقة بالبصمة</p>
              <p className="text-xs text-green-700">مفعلة</p>
            </div>
          </div>
          <div className="flex items-center gap-3 p-3 bg-green-50 rounded-lg">
            <Lock className="w-8 h-8 text-green-600" />
            <div>
              <p className="text-sm font-bold">تشفير AES-256</p>
              <p className="text-xs text-green-700">نشط</p>
            </div>
          </div>
          <div className="flex items-center gap-3 p-3 bg-green-50 rounded-lg">
            <CheckCircle className="w-8 h-8 text-green-600" />
            <div>
              <p className="text-sm font-bold">TLS 1.3</p>
              <p className="text-xs text-green-700">مفعلة</p>
            </div>
          </div>
          <div className="flex items-center gap-3 p-3 bg-green-50 rounded-lg">
            <Shield className="w-8 h-8 text-green-600" />
            <div>
              <p className="text-sm font-bold">WAF Protection</p>
              <p className="text-xs text-green-700">نشط</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
