import { useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useQuery, useMutation } from '@tanstack/react-query';
import {
  ArrowRight, HeartPulse, FolderKanban, FileText, ImageIcon,
  Droplet, Calendar, Phone, Hash, AlertTriangle, Loader2, CreditCard,
  Sparkles, Copy, Check, RefreshCw,
} from 'lucide-react';
import { patientsExtendedApi } from '../api/extendedApis';

/** Minimal markdown renderer for the AI summary: headings, **bold**, bullets. */
function renderSummary(text: string) {
  return text.split('\n').map((line, i) => {
    if (!line.trim()) return <div key={i} className="h-1.5" />;
    const heading = /^#{1,4}\s*(.+)/.exec(line);
    const parts = (heading ? heading[1] : line).split(/(\*\*[^*]+\*\*)/g);
    const rendered = parts.map((p, j) =>
      p.startsWith('**') && p.endsWith('**') ? (
        <strong key={j} className="font-bold text-gray-900 dark:text-white">
          {p.slice(2, -2)}
        </strong>
      ) : (
        <span key={j}>{p}</span>
      ),
    );
    const isBullet = /^\s*[-•*]\s+/.test(line);
    if (heading) {
      return (
        <p key={i} className="font-bold text-medical-700 dark:text-medical-300 mt-2 mb-0.5">
          {heading[1].replace(/\*\*/g, '')}
        </p>
      );
    }
    return (
      <p key={i} className={`text-sm leading-6 ${isBullet ? 'pr-4' : ''}`}>
        {isBullet ? '• ' : ''}
        {rendered}
      </p>
    );
  });
}

const recordTypeLabels: Record<string, string> = {
  DIAGNOSIS: 'تشخيص',
  PRESCRIPTION: 'وصفة طبية',
  LAB_RESULT: 'نتيجة مختبر',
  VITAL_SIGNS: 'مؤشرات حيوية',
  NOTE: 'ملاحظة',
  IMAGING: 'تصوير طبي',
  OTHER: 'أخرى',
};

const channelTypes: Record<string, string> = {
  EMERGENCY: 'حالة طارئة',
  INPATIENT: 'مريض مقيم',
  OUTPATIENT: 'مريض خارجي',
  CONSULTATION: 'استشارة',
  FOLLOW_UP: 'متابعة',
};

const priorityStyles: Record<string, string> = {
  LOW: 'bg-gray-100 text-gray-600',
  MEDIUM: 'bg-blue-100 text-blue-700',
  HIGH: 'bg-yellow-100 text-yellow-700',
  URGENT: 'bg-red-100 text-red-700',
};

function ageFrom(dob?: string) {
  if (!dob) return '—';
  const d = new Date(dob);
  const now = new Date();
  return String(now.getFullYear() - d.getFullYear());
}

export default function PatientProfile() {
  const { id } = useParams<{ id: string }>();
  const [summary, setSummary] = useState<any>(null);
  const [copied, setCopied] = useState(false);

  const { data, isLoading, isError } = useQuery({
    queryKey: ['patient-profile', id],
    queryFn: () => patientsExtendedApi.profile(id!),
    enabled: !!id,
  });

  const summaryMutation = useMutation({
    mutationFn: () => patientsExtendedApi.aiSummary(id!),
    onSuccess: (res) => setSummary(res.data),
  });

  const copySummary = async () => {
    if (!summary?.summary) return;
    try {
      await navigator.clipboard.writeText(summary.summary);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch { /* clipboard unavailable */ }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-24">
        <Loader2 className="w-8 h-8 animate-spin text-primary-500" />
      </div>
    );
  }

  if (isError || !data?.data) {
    return (
      <div className="text-center py-24">
        <AlertTriangle className="w-12 h-12 text-red-400 mx-auto mb-3" />
        <p className="text-gray-500 mb-4">تعذر تحميل ملف المريض أو لا تملك صلاحية الوصول</p>
        <Link to="/patients" className="btn-secondary inline-flex items-center gap-2">
          <ArrowRight className="w-4 h-4" />
          العودة إلى قائمة المرضى
        </Link>
      </div>
    );
  }

  const { patient, records, channels, files, stats } = data.data;

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      {/* Header */}
      <div className="flex items-center gap-3">
        <Link
          to="/patients"
          className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
          aria-label="عودة"
        >
          <ArrowRight className="w-5 h-5 text-gray-500" />
        </Link>
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
            <HeartPulse className="w-6 h-6 text-medical-600" />
            ملف المريض
          </h1>
          <p className="text-gray-500 text-sm mt-0.5">
            السجل الكامل: {stats?.total_records} سجلات • {stats?.total_channels} قنوات • {stats?.total_files} ملفات
          </p>
        </div>
      </div>

      {/* Patient info card */}
      <div className="card">
        <div className="flex flex-col md:flex-row items-start md:items-center gap-5">
          <div className="w-20 h-20 bg-gradient-to-br from-medical-500 to-primary-500 rounded-2xl flex items-center justify-center flex-shrink-0">
            <span className="text-white text-3xl font-bold">
              {patient.full_name?.charAt(0)}
            </span>
          </div>
          <div className="flex-1 w-full">
            <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-3">
              {patient.full_name}
            </h2>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
              <div className="flex items-center gap-2 text-sm">
                <CreditCard className="w-4 h-4 text-gray-400" />
                <span className="text-gray-500">الهوية:</span>
                <span className="font-medium text-gray-900 dark:text-gray-100">{patient.national_id || '—'}</span>
              </div>
              <div className="flex items-center gap-2 text-sm">
                <Calendar className="w-4 h-4 text-gray-400" />
                <span className="text-gray-500">الميلاد:</span>
                <span className="font-medium text-gray-900 dark:text-gray-100">
                  {patient.date_of_birth} ({ageFrom(patient.date_of_birth)} سنة)
                </span>
              </div>
              <div className="flex items-center gap-2 text-sm">
                <Droplet className="w-4 h-4 text-gray-400" />
                <span className="text-gray-500">الدم:</span>
                <span className="font-medium text-gray-900 dark:text-gray-100">{patient.blood_type || '—'}</span>
              </div>
              <div className="flex items-center gap-2 text-sm">
                <Hash className="w-4 h-4 text-gray-400" />
                <span className="text-gray-500">الجنس:</span>
                <span className="font-medium text-gray-900 dark:text-gray-100">
                  {patient.gender === 'M' ? 'ذكر' : patient.gender === 'F' ? 'أنثى' : 'أخرى'}
                </span>
              </div>
              {patient.phone && (
                <div className="flex items-center gap-2 text-sm">
                  <Phone className="w-4 h-4 text-gray-400" />
                  <span className="font-medium text-gray-900 dark:text-gray-100">{patient.phone}</span>
                </div>
              )}
            </div>
            {patient.allergies && (
              <div className="mt-3 flex items-center gap-2 p-2.5 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
                <AlertTriangle className="w-4 h-4 text-red-500" />
                <span className="text-sm text-red-700 dark:text-red-300">
                  <strong>حساسية:</strong> {patient.allergies}
                </span>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* AI clinical summary */}
      <div className="card border-2 border-dashed border-medical-200 dark:border-medical-800 bg-gradient-to-l from-medical-50/60 to-transparent dark:from-medical-900/10">
        <div className="flex items-center justify-between gap-3 mb-3">
          <h3 className="font-bold flex items-center gap-2 text-gray-900 dark:text-white">
            <span className="w-8 h-8 bg-gradient-to-br from-medical-500 to-primary-500 rounded-lg flex items-center justify-center flex-shrink-0">
              <Sparkles className="w-4 h-4 text-white" />
            </span>
            الملخص الذكي للحالة
          </h3>
          <div className="flex items-center gap-2">
            {summary?.summary && (
              <button
                onClick={copySummary}
                className="p-2 hover:bg-white dark:hover:bg-gray-700 rounded-lg transition-colors text-gray-500"
                title="نسخ الملخص"
                aria-label="نسخ الملخص"
              >
                {copied ? <Check className="w-4 h-4 text-green-500" /> : <Copy className="w-4 h-4" />}
              </button>
            )}
            <button
              onClick={() => summaryMutation.mutate()}
              disabled={summaryMutation.isPending}
              className="btn-primary inline-flex items-center gap-2 text-sm disabled:opacity-60"
            >
              {summaryMutation.isPending ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  جارٍ التوليد...
                </>
              ) : summary?.summary ? (
                <>
                  <RefreshCw className="w-4 h-4" />
                  إعادة التوليد
                </>
              ) : (
                <>
                  <Sparkles className="w-4 h-4" />
                  توليد الملخص الذكي
                </>
              )}
            </button>
          </div>
        </div>

        {summaryMutation.isError && (
          <p className="text-sm text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-3">
            تعذر توليد الملخص الذكي — تأكد من تشغيل خدمة الذكاء الاصطناعي ثم أعد المحاولة
          </p>
        )}

        {summary?.summary ? (
          <div className="bg-white dark:bg-gray-800 rounded-lg p-4 border border-gray-100 dark:border-gray-700">
            {renderSummary(summary.summary)}
            <div className="flex flex-wrap items-center justify-between gap-2 mt-4 pt-3 border-t border-gray-100 dark:border-gray-700">
              <p className="text-[11px] text-gray-400 flex items-center gap-1.5">
                <AlertTriangle className="w-3 h-3 text-amber-400" />
                {summary.disclaimer || 'هذا الملخص مولّد آلياً ولا يُغني عن المراجعة الطبية البشرية'}
              </p>
              <p className="text-[11px] text-gray-400">
                مبني على {summary.records_used} سجل طبي
                {summary.generated_at && (
                  <> • {new Date(summary.generated_at).toLocaleString('ar', {
                    hour: '2-digit', minute: '2-digit', day: 'numeric', month: 'short',
                  })}</>
                )}
              </p>
            </div>
          </div>
        ) : (
          !summaryMutation.isPending && !summaryMutation.isError && (
            <p className="text-sm text-gray-500 dark:text-gray-400">
              ولّد ملخصاً سريرياً مركّزاً لحالة المريض بالاعتماد على سجلاته الطبية الحقيقية —
              يساعد الكادر على فهم الحالة بسرعة دون تصفح كل السجلات.
            </p>
          )
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Medical records timeline */}
        <div className="lg:col-span-2 card">
          <h3 className="font-bold mb-4 flex items-center gap-2 text-gray-900 dark:text-white">
            <FileText className="w-5 h-5 text-primary-600" />
            الخط الزمني للسجلات الطبية ({records.length})
          </h3>
          {records.length === 0 ? (
            <p className="text-center text-gray-400 py-8 text-sm">لا توجد سجلات طبية بعد</p>
          ) : (
            <div className="relative max-h-[480px] overflow-y-auto pr-4">
              <div className="absolute right-[7px] top-2 bottom-2 w-0.5 bg-primary-100 dark:bg-gray-700" />
              <div className="space-y-4">
                {records.map((r: any) => (
                  <div key={r.id} className="relative pr-6">
                    <div
                      className={`absolute right-0 top-1.5 w-4 h-4 rounded-full border-2 ${
                        r.is_critical
                          ? 'bg-red-500 border-red-200'
                          : 'bg-primary-500 border-primary-200'
                      }`}
                    />
                    <div className="p-3 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
                      <div className="flex items-center justify-between gap-2 mb-1">
                        <span className={`text-xs font-bold px-2 py-0.5 rounded-full ${
                          r.is_critical
                            ? 'bg-red-100 text-red-700'
                            : 'bg-primary-100 text-primary-700'
                        }`}>
                          {recordTypeLabels[r.record_type] || r.record_type}
                        </span>
                        <span className="text-xs text-gray-400">
                          {new Date(r.created_at).toLocaleDateString('ar', {
                            year: 'numeric', month: 'short', day: 'numeric',
                          })}
                        </span>
                      </div>
                      <p className="font-medium text-sm text-gray-900 dark:text-white">
                        {r.title}
                      </p>
                      {r.content && (
                        <p className="text-xs text-gray-500 dark:text-gray-400 mt-1 line-clamp-2">
                          {r.content}
                        </p>
                      )}
                      {r.channel_name && (
                        <p className="text-xs text-gray-400 mt-1.5 flex items-center gap-1">
                          <FolderKanban className="w-3 h-3" />
                          {r.channel_name}
                        </p>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Side column: channels + files */}
        <div className="space-y-6">
          <div className="card">
            <h3 className="font-bold mb-4 flex items-center gap-2 text-gray-900 dark:text-white">
              <FolderKanban className="w-5 h-5 text-primary-600" />
              القنوات ({channels.length})
            </h3>
            {channels.length === 0 ? (
              <p className="text-center text-gray-400 py-6 text-sm">لا توجد قنوات</p>
            ) : (
              <div className="space-y-2 max-h-56 overflow-y-auto">
                {channels.map((c: any) => (
                  <Link
                    key={c.id}
                    to={`/channels/${c.id}`}
                    className="block p-2.5 bg-gray-50 dark:bg-gray-700/50 hover:bg-primary-50 dark:hover:bg-gray-700 rounded-lg transition-colors"
                  >
                    <div className="flex items-center justify-between gap-2">
                      <p className="text-sm font-medium text-gray-900 dark:text-white truncate">
                        {c.name}
                      </p>
                      <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full flex-shrink-0 ${priorityStyles[c.priority] || ''}`}>
                        {c.priority}
                      </span>
                    </div>
                    <p className="text-xs text-gray-400 mt-0.5">
                      {channelTypes[c.channel_type] || c.channel_type}
                    </p>
                  </Link>
                ))}
              </div>
            )}
          </div>

          <div className="card">
            <h3 className="font-bold mb-4 flex items-center gap-2 text-gray-900 dark:text-white">
              <ImageIcon className="w-5 h-5 text-primary-600" />
              الملفات الطبية ({files.length})
            </h3>
            {files.length === 0 ? (
              <p className="text-center text-gray-400 py-6 text-sm">لا توجد ملفات مرفوعة</p>
            ) : (
              <div className="space-y-2 max-h-56 overflow-y-auto">
                {files.map((f: any) => (
                  <div
                    key={f.id}
                    className="flex items-center gap-3 p-2.5 bg-gray-50 dark:bg-gray-700/50 rounded-lg"
                  >
                    <div className="w-8 h-8 bg-primary-100 text-primary-600 rounded-lg flex items-center justify-center flex-shrink-0">
                      <ImageIcon className="w-4 h-4" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-gray-900 dark:text-white truncate">
                        {f.title}
                      </p>
                      <p className="text-xs text-gray-400">
                        {f.file_type_display} • {Math.round((f.file_size || 0) / 1024)} KB
                      </p>
                    </div>
                    {f.is_critical && (
                      <AlertTriangle className="w-4 h-4 text-red-500 flex-shrink-0" />
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
