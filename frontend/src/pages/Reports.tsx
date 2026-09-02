import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { motion } from 'framer-motion';
import {
  FileText, Download, BarChart3, Shield, Users, Calendar,
  FileSpreadsheet, Clock, CheckCircle2, AlertCircle,
  Stethoscope, TrendingUp, RefreshCw, Eye,
} from 'lucide-react';
import toast from 'react-hot-toast';
import { reportsAPI } from '../api/extendedApis';
import { useAuthStore } from '../store/authStore';

// ─── Report definitions ───────────────────────────────────────────────────────

const REPORTS = [
  {
    id: 'monthly_summary',
    title: 'التقرير الشهري الشامل',
    description: 'إحصائيات شاملة للمرضى والقنوات والإيرادات للشهر المحدد',
    icon: BarChart3,
    color: 'from-blue-500 to-indigo-600',
    shadow: 'shadow-blue-500/20',
    formats: ['pdf', 'excel'],
    roles: ['SUPER_ADMIN', 'HOSPITAL_ADMIN'],
  },
  {
    id: 'patient_report',
    title: 'تقرير المرضى',
    description: 'قائمة شاملة بالمرضى وحالاتهم وسجلاتهم الطبية',
    icon: Users,
    color: 'from-emerald-500 to-teal-600',
    shadow: 'shadow-emerald-500/20',
    formats: ['pdf', 'excel'],
    roles: ['SUPER_ADMIN', 'HOSPITAL_ADMIN', 'DOCTOR'],
  },
  {
    id: 'security_report',
    title: 'تقرير الأمان',
    description: 'سجل الأحداث الأمنية والثغرات المكتشفة وتوصيات الأمان',
    icon: Shield,
    color: 'from-red-500 to-rose-600',
    shadow: 'shadow-red-500/20',
    formats: ['pdf'],
    roles: ['SUPER_ADMIN', 'AUDITOR'],
  },
  {
    id: 'appointments_report',
    title: 'تقرير المواعيد',
    description: 'إحصائيات المواعيد: معدلات الحضور، الإلغاء، وأوقات الذروة',
    icon: Calendar,
    color: 'from-purple-500 to-violet-600',
    shadow: 'shadow-purple-500/20',
    formats: ['pdf', 'excel'],
    roles: ['SUPER_ADMIN', 'HOSPITAL_ADMIN', 'DOCTOR'],
  },
  {
    id: 'audit_report',
    title: 'تقرير سجلات التدقيق',
    description: 'سجل مفصّل لجميع العمليات والأحداث الأمنية في النظام',
    icon: FileText,
    color: 'from-amber-500 to-orange-600',
    shadow: 'shadow-amber-500/20',
    formats: ['pdf', 'excel'],
    roles: ['SUPER_ADMIN', 'AUDITOR'],
  },
  {
    id: 'channels_report',
    title: 'تقرير القنوات / الحالات',
    description: 'تحليل القنوات الطبية النشطة والمغلقة وتوزيعها',
    icon: Stethoscope,
    color: 'from-cyan-500 to-sky-600',
    shadow: 'shadow-cyan-500/20',
    formats: ['pdf', 'excel'],
    roles: ['SUPER_ADMIN', 'HOSPITAL_ADMIN', 'DOCTOR'],
  },
];

// ─── Date range picker ────────────────────────────────────────────────────────

function DateRangePicker({
  startDate, endDate, setStart, setEnd,
}: {
  startDate: string; endDate: string;
  setStart: (d: string) => void; setEnd: (d: string) => void;
}) {
  const presets = [
    { label: 'هذا الشهر', action: () => {
      const now = new Date();
      setStart(`${now.getFullYear()}-${String(now.getMonth()+1).padStart(2,'0')}-01`);
      setEnd(now.toISOString().slice(0,10));
    }},
    { label: 'الشهر الماضي', action: () => {
      const now = new Date();
      const lastMonth = new Date(now.getFullYear(), now.getMonth()-1, 1);
      const lastDay = new Date(now.getFullYear(), now.getMonth(), 0);
      setStart(lastMonth.toISOString().slice(0,10));
      setEnd(lastDay.toISOString().slice(0,10));
    }},
    { label: 'آخر 3 أشهر', action: () => {
      const now = new Date();
      const d = new Date(now); d.setMonth(d.getMonth()-3);
      setStart(d.toISOString().slice(0,10));
      setEnd(now.toISOString().slice(0,10));
    }},
    { label: 'هذا العام', action: () => {
      const now = new Date();
      setStart(`${now.getFullYear()}-01-01`);
      setEnd(now.toISOString().slice(0,10));
    }},
  ];

  return (
    <div className="bg-white/5 border border-white/10 rounded-2xl p-4 space-y-3">
      <p className="text-sm font-medium text-gray-300">النطاق الزمني</p>
      <div className="flex flex-wrap gap-2">
        {presets.map(p => (
          <button
            key={p.label}
            onClick={p.action}
            className="text-xs px-3 py-1.5 bg-white/5 hover:bg-primary-600/30 text-gray-400 hover:text-primary-300 border border-white/10 hover:border-primary-500/30 rounded-lg transition-colors"
          >
            {p.label}
          </button>
        ))}
      </div>
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="text-xs text-gray-500 mb-1 block">من</label>
          <input
            type="date"
            value={startDate}
            onChange={e => setStart(e.target.value)}
            className="w-full bg-white/5 border border-white/10 rounded-xl px-3 py-2 text-sm text-white focus:outline-none focus:border-primary-500 transition-colors"
          />
        </div>
        <div>
          <label className="text-xs text-gray-500 mb-1 block">إلى</label>
          <input
            type="date"
            value={endDate}
            onChange={e => setEnd(e.target.value)}
            className="w-full bg-white/5 border border-white/10 rounded-xl px-3 py-2 text-sm text-white focus:outline-none focus:border-primary-500 transition-colors"
          />
        </div>
      </div>
    </div>
  );
}

// ─── Report Card ──────────────────────────────────────────────────────────────

function ReportCard({
  report, startDate, endDate, onDownload, loading,
}: {
  report: typeof REPORTS[0];
  startDate: string; endDate: string;
  onDownload: (id: string, format: string) => void;
  loading: string | null;
}) {
  const Icon = report.icon;
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-white/5 border border-white/10 rounded-2xl p-5 hover:bg-white/8 hover:border-white/20 transition-all group"
    >
      <div className="flex items-start gap-4">
        <div className={`p-3 rounded-xl bg-gradient-to-br ${report.color} shadow-lg ${report.shadow} flex-shrink-0`}>
          <Icon className="w-5 h-5 text-white" />
        </div>
        <div className="flex-1 min-w-0">
          <h3 className="font-semibold text-white group-hover:text-primary-300 transition-colors">
            {report.title}
          </h3>
          <p className="text-sm text-gray-400 mt-0.5 leading-relaxed">{report.description}</p>

          {/* Actions */}
          <div className="flex items-center gap-2 mt-3">
            {report.formats.includes('pdf') && (
              <button
                onClick={() => onDownload(report.id, 'pdf')}
                disabled={loading === `${report.id}-pdf`}
                className="flex items-center gap-1.5 px-3 py-1.5 bg-red-600/20 hover:bg-red-600/40 text-red-400 hover:text-red-300 border border-red-500/20 hover:border-red-500/40 rounded-lg text-xs font-medium transition-all disabled:opacity-50"
              >
                {loading === `${report.id}-pdf`
                  ? <RefreshCw className="w-3 h-3 animate-spin" />
                  : <FileText className="w-3 h-3" />}
                PDF
              </button>
            )}
            {report.formats.includes('excel') && (
              <button
                onClick={() => onDownload(report.id, 'excel')}
                disabled={loading === `${report.id}-excel`}
                className="flex items-center gap-1.5 px-3 py-1.5 bg-emerald-600/20 hover:bg-emerald-600/40 text-emerald-400 hover:text-emerald-300 border border-emerald-500/20 hover:border-emerald-500/40 rounded-lg text-xs font-medium transition-all disabled:opacity-50"
              >
                {loading === `${report.id}-excel`
                  ? <RefreshCw className="w-3 h-3 animate-spin" />
                  : <FileSpreadsheet className="w-3 h-3" />}
                Excel
              </button>
            )}
          </div>
        </div>
      </div>
    </motion.div>
  );
}

// ─── Main Reports Page ────────────────────────────────────────────────────────

export default function Reports() {
  const { user } = useAuthStore();
  const now = new Date();
  const [startDate, setStartDate] = useState(`${now.getFullYear()}-${String(now.getMonth()+1).padStart(2,'0')}-01`);
  const [endDate, setEndDate] = useState(now.toISOString().slice(0,10));
  const [loading, setLoading] = useState<string | null>(null);

  // Filter reports by role
  const availableReports = REPORTS.filter(
    r => !r.roles || r.roles.includes(user?.role || '')
  );

  const handleDownload = async (reportId: string, format: string) => {
    const key = `${reportId}-${format}`;
    setLoading(key);
    try {
      const res = await reportsAPI.download(reportId, format as 'pdf' | 'excel', startDate, endDate);
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const a = document.createElement('a');
      a.href = url;
      const ext = format === 'excel' ? 'xlsx' : 'pdf';
      a.download = `${reportId}_${startDate}_${endDate}.${ext}`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      a.remove();
      toast.success('تم تنزيل التقرير بنجاح');
    } catch (err: any) {
      toast.error('فشل تنزيل التقرير — تحقق من الفترة الزمنية');
    } finally {
      setLoading(null);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-white flex items-center gap-2">
          <FileText className="w-7 h-7 text-primary-400" />
          التقارير
        </h1>
        <p className="text-gray-400 text-sm mt-1">تنزيل التقارير بصيغة PDF أو Excel</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Date range sidebar */}
        <div className="space-y-4">
          <DateRangePicker
            startDate={startDate} endDate={endDate}
            setStart={setStartDate} setEnd={setEndDate}
          />

          {/* Info */}
          <div className="bg-blue-500/10 border border-blue-500/20 rounded-xl p-3">
            <div className="flex gap-2">
              <AlertCircle className="w-4 h-4 text-blue-400 flex-shrink-0 mt-0.5" />
              <div>
                <p className="text-xs text-blue-300 font-medium">ملاحظة</p>
                <p className="text-xs text-blue-400 mt-0.5 leading-relaxed">
                  التقارير الكبيرة قد تستغرق بضع ثوانٍ. تأكد من اختيار نطاق زمني مناسب.
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Reports list */}
        <div className="lg:col-span-2 space-y-3">
          {availableReports.length === 0 ? (
            <div className="flex flex-col items-center py-12 text-gray-500">
              <FileText className="w-10 h-10 mb-2 opacity-30" />
              <p>لا توجد تقارير متاحة لدورك الحالي</p>
            </div>
          ) : (
            availableReports.map(report => (
              <ReportCard
                key={report.id}
                report={report}
                startDate={startDate}
                endDate={endDate}
                onDownload={handleDownload}
                loading={loading}
              />
            ))
          )}
        </div>
      </div>
    </div>
  );
}
