import React, { useState, useMemo } from 'react';
import { Calendar, Stethoscope, Pill, FlaskConical, ImageIcon, Activity, FileText, Clock, ChevronDown, ChevronUp, Search, Filter, CheckCircle2, User, Eye } from 'lucide-react';

interface TimelineRecord {
  id?: string;
  record_type: string;
  title?: string;
  description?: string;
  recorded_at?: string;
  created_at?: string;
  date?: string;
  performed_by?: string;
  doctor_name?: string;
  created_by_name?: string;
  image_preview?: string;
  attachment?: { image_url?: string; file?: string } | string | null;
  image_url?: string;
  file?: string;
}

interface PatientTimelineProps {
  records?: TimelineRecord[];
  patientId?: string;
  patientName?: string;
  onOpenImage?: (imageUrl: string, title: string, date?: string) => void;
}

const TYPE_CONFIG: Record<string, { label: string; icon: any; color: string; badge: string }> = {
  DIAGNOSIS: {
    label: 'تشخيص سريري',
    icon: Stethoscope,
    color: 'text-blue-600 dark:text-blue-400 bg-blue-500/10 border-blue-500/30',
    badge: 'bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-300 border-blue-200 dark:border-blue-800',
  },
  PRESCRIPTION: {
    label: 'وصفة طبية / دواء',
    icon: Pill,
    color: 'text-emerald-600 dark:text-emerald-400 bg-emerald-500/10 border-emerald-500/30',
    badge: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300 border-emerald-200 dark:border-emerald-800',
  },
  LAB_ORDER: {
    label: 'طلب فحص مخبري',
    icon: FlaskConical,
    color: 'text-amber-600 dark:text-amber-400 bg-amber-500/10 border-amber-500/30',
    badge: 'bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300 border-amber-200 dark:border-amber-800',
  },
  LAB_RESULT: {
    label: 'نتيجة تحليل',
    icon: FlaskConical,
    color: 'text-purple-600 dark:text-purple-400 bg-purple-500/10 border-purple-500/30',
    badge: 'bg-purple-100 text-purple-800 dark:bg-purple-900/40 dark:text-purple-300 border-purple-200 dark:border-purple-800',
  },
  IMAGING: {
    label: 'تصوير وأشعة (Radiology)',
    icon: ImageIcon,
    color: 'text-teal-600 dark:text-teal-400 bg-teal-500/10 border-teal-500/30',
    badge: 'bg-teal-100 text-teal-800 dark:bg-teal-900/40 dark:text-teal-300 border-teal-200 dark:border-teal-800',
  },
  VITALS: {
    label: 'علامات حيوية',
    icon: Activity,
    color: 'text-rose-600 dark:text-rose-400 bg-rose-500/10 border-rose-500/30',
    badge: 'bg-rose-100 text-rose-800 dark:bg-rose-900/40 dark:text-rose-300 border-rose-200 dark:border-rose-800',
  },
  VITAL_SIGNS: {
    label: 'علامات حيوية',
    icon: Activity,
    color: 'text-rose-600 dark:text-rose-400 bg-rose-500/10 border-rose-500/30',
    badge: 'bg-rose-100 text-rose-800 dark:bg-rose-900/40 dark:text-rose-300 border-rose-200 dark:border-rose-800',
  },
  PROCEDURE: {
    label: 'إجراء طبي أو جراحي',
    icon: CheckCircle2,
    color: 'text-indigo-600 dark:text-indigo-400 bg-indigo-500/10 border-indigo-500/30',
    badge: 'bg-indigo-100 text-indigo-800 dark:bg-indigo-900/40 dark:text-indigo-300 border-indigo-200 dark:border-indigo-800',
  },
  NOTE: {
    label: 'ملاحظات سريرية',
    icon: FileText,
    color: 'text-gray-600 dark:text-gray-400 bg-gray-500/10 border-gray-500/30',
    badge: 'bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-300 border-gray-200 dark:border-gray-700',
  },
  NOTES: {
    label: 'ملاحظات سريرية',
    icon: FileText,
    color: 'text-gray-600 dark:text-gray-400 bg-gray-500/10 border-gray-500/30',
    badge: 'bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-300 border-gray-200 dark:border-gray-700',
  },
};

export default function PatientTimeline({
  records = [],
  onOpenImage,
  patientName,
}: PatientTimelineProps) {
  const [filterType, setFilterType] = useState<string>('ALL');
  const [searchQuery, setSearchQuery] = useState('');
  const [expandedIds, setExpandedIds] = useState<Record<string, boolean>>({});

  const toggleExpand = (id: string | number) => {
    setExpandedIds((prev) => ({ ...prev, [String(id)]: !prev[String(id)] }));
  };

  const filteredRecords = useMemo(() => {
    return records.filter((r) => {
      // Type match
      if (filterType !== 'ALL') {
        const matchesType =
          r.record_type === filterType ||
          (filterType === 'VITALS' && r.record_type === 'VITAL_SIGNS') ||
          (filterType === 'NOTE' && r.record_type === 'NOTES');
        if (!matchesType) return false;
      }

      // Search match
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        const titleMatch = r.title?.toLowerCase().includes(q);
        const descMatch = r.description?.toLowerCase().includes(q);
        const docMatch = r.doctor_name?.toLowerCase().includes(q);
        return titleMatch || descMatch || docMatch;
      }

      return true;
    });
  }, [records, filterType, searchQuery]);

  const categories = [
    { key: 'ALL', label: 'الكل' },
    { key: 'DIAGNOSIS', label: 'التشخيصات' },
    { key: 'PRESCRIPTION', label: 'الأدوية' },
    { key: 'LAB_RESULT', label: 'المختبر' },
    { key: 'IMAGING', label: 'الأشعة' },
    { key: 'VITALS', label: 'العلامات الحيوية' },
  ];

  return (
    <div className="space-y-4" dir="rtl">
      {/* Controls Bar */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-3 p-3.5 rounded-2xl bg-white dark:bg-gray-800 border border-gray-100 dark:border-gray-700/60 shadow-sm">
        {/* Category filters */}
        <div className="flex items-center gap-1.5 overflow-x-auto w-full sm:w-auto pb-1 sm:pb-0">
          {categories.map((c) => (
            <button
              key={c.key}
              onClick={() => setFilterType(c.key)}
              className={`px-3 py-1.5 rounded-xl text-xs font-semibold whitespace-nowrap transition-all cursor-pointer ${
                filterType === c.key
                  ? 'bg-primary-600 text-white shadow-sm'
                  : 'bg-gray-100 dark:bg-gray-700/60 text-gray-600 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700'
              }`}
            >
              {c.label}
            </button>
          ))}
        </div>

        {/* Search inside timeline */}
        <div className="relative w-full sm:w-64">
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="بحث في السجلات والتشخيصات..."
            className="w-full px-3.5 py-1.5 pl-9 rounded-xl border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900 text-gray-900 dark:text-white text-xs outline-none focus:ring-2 focus:ring-primary-500"
          />
          <Search className="w-3.5 h-3.5 text-gray-400 absolute left-3 top-2.5" />
        </div>
      </div>

      {/* Timeline List */}
      {filteredRecords.length === 0 ? (
        <div className="text-center py-12 bg-white dark:bg-gray-800 rounded-2xl border border-gray-100 dark:border-gray-700/60">
          <Clock className="w-10 h-10 text-gray-300 dark:text-gray-600 mx-auto mb-2" />
          <p className="text-sm font-semibold text-gray-600 dark:text-gray-300">
            لا توجد سجلات مطابقة في الخط الزمني
          </p>
          <p className="text-xs text-gray-400 mt-0.5">
            قم بإضافة سجلات جديدة أو تغيير معايير الفلترة
          </p>
        </div>
      ) : (
        <div className="relative pl-2 pr-4 space-y-6 before:absolute before:right-7 before:top-3 before:bottom-3 before:w-0.5 before:bg-gradient-to-b before:from-primary-500 before:via-teal-500 before:to-gray-200 dark:before:to-gray-800">
          {filteredRecords.map((rec, idx) => {
            const config = TYPE_CONFIG[rec.record_type] || TYPE_CONFIG['NOTE'];
            const Icon = config.icon;
            const isExpanded = !!expandedIds[String(rec.id || idx)];
            const dateStr = rec.recorded_at || rec.created_at || rec.date;
            const formattedDate = dateStr
              ? new Date(dateStr).toLocaleDateString('ar-SA', {
                  year: 'numeric',
                  month: 'short',
                  day: 'numeric',
                  hour: '2-digit',
                  minute: '2-digit',
                })
              : 'تاريخ غير محدد';

            const isImaging = rec.record_type === 'IMAGING';
            const hasAttachment = !!(rec.attachment || rec.image_url || rec.file);
            const previewImage: string =
              (typeof rec.attachment === 'string'
                ? rec.attachment
                : (rec.attachment?.image_url || rec.attachment?.file)) ||
              rec.image_url ||
              rec.file ||
              'https://images.unsplash.com/photo-1516549655169-df83a0774514?auto=format&fit=crop&q=80&w=800';

            return (
              <div key={rec.id || idx} className="relative flex items-start gap-4 group">
                {/* Node Dot Icon */}
                <div
                  className={`w-9 h-9 rounded-2xl border flex items-center justify-center shrink-0 z-10 shadow-sm transition-transform group-hover:scale-110 ${config.color}`}
                >
                  <Icon className="w-4 h-4" />
                </div>

                {/* Event Card */}
                <div className="flex-1 bg-white dark:bg-gray-800/90 rounded-2xl border border-gray-100 dark:border-gray-700/70 p-4 shadow-sm hover:shadow-md transition-all">
                  <div className="flex flex-wrap items-center justify-between gap-2 mb-2">
                    <div className="flex items-center gap-2">
                      <span className={`px-2.5 py-0.5 rounded-lg text-[11px] font-bold border ${config.badge}`}>
                        {config.label}
                      </span>
                      <h4 className="text-sm font-bold text-gray-900 dark:text-white">
                        {rec.title || 'سجل سريري'}
                      </h4>
                    </div>

                    <div className="flex items-center gap-1.5 text-xs text-gray-400 font-mono">
                      <Calendar className="w-3.5 h-3.5" />
                      <span>{formattedDate}</span>
                    </div>
                  </div>

                  {/* Short description */}
                  {rec.description && (
                    <p className={`text-xs text-gray-600 dark:text-gray-300 leading-relaxed ${
                      isExpanded ? '' : 'line-clamp-2'
                    }`}>
                      {rec.description}
                    </p>
                  )}

                  {/* Imaging Record Quick Viewer Button */}
                  {isImaging && (
                    <div className="mt-3 p-3 rounded-xl bg-teal-50/70 dark:bg-teal-950/30 border border-teal-200 dark:border-teal-800/40 flex items-center justify-between">
                      <div className="flex items-center gap-2.5">
                        <ImageIcon className="w-5 h-5 text-teal-600 dark:text-teal-400" />
                        <div>
                          <p className="text-xs font-bold text-teal-900 dark:text-teal-200">
                            صورة فحص إشعاعي ملحقة
                          </p>
                          <p className="text-[10px] text-teal-700 dark:text-teal-400">
                            قابلة للفحص المجهري، عكس الألوان، وقياس الأبعاد
                          </p>
                        </div>
                      </div>

                      <button
                        type="button"
                        onClick={() => {
                          if (onOpenImage) {
                            onOpenImage(previewImage, rec.title || 'صورة أشعة', formattedDate);
                          }
                        }}
                        className="px-3 py-1.5 rounded-lg bg-teal-600 hover:bg-teal-700 text-white text-xs font-bold flex items-center gap-1.5 shadow-sm transition-colors cursor-pointer"
                      >
                        <Eye className="w-3.5 h-3.5" />
                        فتح في عارض الأشعة
                      </button>
                    </div>
                  )}

                  {/* Card Footer: Clinician & Expand */}
                  <div className="flex items-center justify-between pt-3 mt-3 border-t border-gray-100 dark:border-gray-700/50 text-xs">
                    <div className="flex items-center gap-1.5 text-gray-500 dark:text-gray-400">
                      <User className="w-3.5 h-3.5 text-primary-500" />
                      <span>الطبيب: {rec.doctor_name || rec.created_by_name || 'الفريق السريري'}</span>
                    </div>

                    {rec.description && rec.description.length > 100 && (
                      <button
                        type="button"
                        onClick={() => toggleExpand(String(rec.id || idx))}
                        className="text-[11px] font-semibold text-primary-600 dark:text-primary-400 hover:underline flex items-center gap-1"
                      >
                        <span>{isExpanded ? 'طي التفاصيل' : 'عرض كامل الملاحظة'}</span>
                        {isExpanded ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
                      </button>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
