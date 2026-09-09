import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  DatabaseBackup, Plus, Download, Trash2, ShieldCheck, HardDrive, RotateCcw,
  Send, Cloud, CheckCircle2, XCircle, CircleDashed
} from 'lucide-react';
import { backupsAPI } from '../api/client';
import { downloadBlobResponse } from '../api/extendedApis';
import toast from 'react-hot-toast';

// delivery_status → { label, tone }. Mirrors BackupRecord.DeliveryStatus on
// the backend so a new backend state without a mapping here degrades to
// "unknown" instead of crashing the row.
const DELIVERY_BADGES: Record<string, { label: string; cls: string }> = {
  NOT_SENT: { label: 'محلية فقط', cls: 'badge-gray' },
  TELEGRAM: { label: 'أُرسلت عبر تلجرام', cls: 'badge-info' },
  CLOUD: { label: 'في التخزين السحابي', cls: 'badge-info' },
  BOTH: { label: 'تلجرام + سحابي', cls: 'badge-success' },
  DELIVERY_FAILED: { label: 'فشل التسليم', cls: 'badge-danger' },
};

// scope → label. Mirrors BackupRecord.Scope.
const SCOPE_BADGES: Record<string, { label: string; cls: string }> = {
  FULL: { label: 'كامل', cls: 'badge-info' },
  DATABASE: { label: 'قاعدة البيانات', cls: 'badge-warning' },
  MEDIA: { label: 'الملفات', cls: 'badge-gray' },
};

export default function Backups() {
  const queryClient = useQueryClient();
  const [note, setNote] = useState('');
  const [verifying, setVerifying] = useState<string | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ['backups'],
    queryFn: () => backupsAPI.list(),
  });

  const { data: delivery } = useQuery({
    queryKey: ['backup-delivery-status'],
    queryFn: () => backupsAPI.deliveryStatus(),
  });
  const channels = delivery?.data;
  const channelsLabel = channels?.any_enabled
    ? [
        channels.telegram?.enabled ? 'تلجرام' : null,
        channels.cloud?.enabled ? `التخزين السحابي${channels.cloud?.bucket ? ` (${channels.cloud.bucket})` : ''}` : null,
      ].filter(Boolean).join(' + ')
    : null;
  const channelsMisconfigured = !!channels && (
    (channels.telegram?.enabled && !channels.telegram?.ready) ||
    (channels.cloud?.enabled && !channels.cloud?.ready)
  );

  const createMutation = useMutation({
    mutationFn: (scope: string) => backupsAPI.create(note, scope),
    onSuccess: (_res, scope: string) => {
      const scopeLabel = SCOPE_BADGES[scope]?.label || scope;
      toast.success(`تم إنشاء النسخة الاحتياطية (${scopeLabel}) بنجاح`);
      setNote('');
      queryClient.invalidateQueries({ queryKey: ['backups'] });
    },
    onError: (err: any) =>
      toast.error(err.response?.data?.detail || 'فشل إنشاء النسخة'),
  });

  const downloadMutation = useMutation({
    mutationFn: (id: string) => backupsAPI.download(id),
    onSuccess: (res) => {
      downloadBlobResponse(res as any, 'securemed_backup.zip');
      toast.success('بدأ التنزيل');
    },
  });

  const verifyMutation = useMutation({
    mutationFn: (id: string) => backupsAPI.verify(id),
    onSuccess: (res) => {
      setVerifying(null);
      if (res.data?.valid) toast.success('الأرشيف سليم — البصمة مطابقة ✓');
      else toast.error(res.data?.detail || 'الأرشيف تالف');
    },
    onError: (err: any) => {
      setVerifying(null);
      toast.error(err.response?.data?.detail || 'فشل التحقق');
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => backupsAPI.delete(id),
    onSuccess: () => {
      toast.success('تم حذف النسخة');
      queryClient.invalidateQueries({ queryKey: ['backups'] });
    },
  });

  const restoreMutation = useMutation({
    mutationFn: (id: string) => backupsAPI.restore(id, true), // force=true
    onSuccess: () => {
      toast.success('تم استعادة النسخة بنجاح! يرجى إعادة تسجيل الدخول.', { duration: 5000 });
      // Force reload the page so the app re-fetches everything from the restored DB
      setTimeout(() => {
          window.location.href = '/login';
      }, 3000);
    },
    onError: (err: any) => {
      toast.error(err.response?.data?.detail || 'فشلت عملية الاستعادة');
    },
  });

  const deliverMutation = useMutation({
    mutationFn: (id: string) => backupsAPI.deliverOffsite(id),
    onSuccess: (res) => {
      queryClient.invalidateQueries({ queryKey: ['backups'] });
      const status = res.data?.delivery_status;
      if (status === 'TELEGRAM' || status === 'CLOUD' || status === 'BOTH') {
        toast.success(res.data?.delivery_status_display || 'تم التسليم الخارجي بنجاح');
      } else {
        toast.error(res.data?.delivery_status_display || 'فشل التسليم الخارجي — راجع سجل الخادم');
      }
    },
    onError: (err: any) =>
      toast.error(err.response?.data?.detail || 'فشل التسليم الخارجي'),
  });

  const backups = data?.data?.results || data?.data || [];
  const totalSize = backups.reduce((s: number, b: any) => s + (b.size_bytes || 0), 0);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <DatabaseBackup className="w-7 h-7 text-primary-600" />
          النسخ الاحتياطي
        </h1>
        <p className="text-gray-600 dark:text-gray-400 text-sm mt-1">
          آلية النسخ الاحتياطي الكامل: قاعدة البيانات + الملفات الطبية (ZIP موثّق ببصمة SHA-256)
        </p>
      </div>

      {/* Create panel */}
      <div className="card">
        <div className="flex flex-col md:flex-row gap-3">
          <input
            className="input-field flex-1"
            placeholder="ملاحظة (اختياري) — مثال: نسخة قبل التحديث"
            value={note}
            onChange={(e) => setNote(e.target.value)}
            maxLength={200}
          />
          <div className="flex gap-2 flex-wrap">
            <button
              onClick={() => {
                if (confirm('إنشاء نسخة احتياطية كاملة الآن (قاعدة البيانات + الملفات)؟')) createMutation.mutate('FULL');
              }}
              disabled={createMutation.isPending}
              className="btn-primary flex items-center justify-center gap-2 whitespace-nowrap"
              title="قاعدة البيانات + الملفات المرفوعة"
            >
              <Plus className="w-4 h-4" />
              {createMutation.isPending ? 'جاري الإنشاء...' : 'نسخة كاملة'}
            </button>
            <button
              onClick={() => {
                if (confirm('إنشاء نسخة قاعدة البيانات فقط؟ (بدون الملفات المرفوعة)')) createMutation.mutate('DATABASE');
              }}
              disabled={createMutation.isPending}
              className="btn-secondary flex items-center justify-center gap-2 whitespace-nowrap"
              title="dump قاعدة البيانات فقط — أخف وأسرع للتسليم اليومي"
            >
              <DatabaseBackup className="w-4 h-4" />
              قاعدة البيانات فقط
            </button>
            <button
              onClick={() => {
                if (confirm('إنشاء نسخة الملفات المرفوعة فقط؟')) createMutation.mutate('MEDIA');
              }}
              disabled={createMutation.isPending}
              className="btn-secondary flex items-center justify-center gap-2 whitespace-nowrap"
              title="ملفات الرفع (التقارير، الأشعة، السجلات) فقط — لا تلمس قاعدة البيانات"
            >
              <HardDrive className="w-4 h-4" />
              الملفات فقط
            </button>
          </div>
        </div>
        <div className="flex items-center gap-4 mt-3 text-xs text-gray-500">
          <span className="flex items-center gap-1">
            <HardDrive className="w-3.5 h-3.5" />
            {backups.length} نسخة — {(totalSize / 1024 / 1024).toFixed(2)} ميجابايت
          </span>
          <span>•</span>
          <span>نسخة تلقائية يومية (قاعدة البيانات 2 صباحاً + كاملة كل جمعة) — يُحتفظ بآخر 14 نسخة لكل نطاق</span>
          <span>•</span>
          <span className="flex items-center gap-1">
            <Cloud className="w-3.5 h-3.5" />
            {channelsLabel
              ? `التسليم التلقائي مفعّل: ${channelsLabel}`
              : 'التسليم الخارجي غير مفعّل (تُضبط القنوات في إعدادات الخادم)'}
          </span>
          <span>•</span>
          <span>للاستعادة: اختر أيقونة (الاستعادة) من الجدول أدناه (تحذير: سيتم مسح البيانات الحالية)</span>
        </div>
        {channelsMisconfigured && (
          <div className="mt-3 text-xs text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg px-3 py-2">
            ⚠ قناة تسليم مفعّلة لكن بياناتها ناقصة (بوت تلجرام أو دلو التخزين) — سيُسجَّل الفشل في حالة التسليم لكل نسخة.
          </div>
        )}
      </div>

      {/* Backups list */}
      {isLoading ? (
        <div className="text-center py-12 text-gray-500">جاري التحميل...</div>
      ) : backups.length === 0 ? (
        <div className="card text-center py-12">
          <DatabaseBackup className="w-12 h-12 text-gray-300 mx-auto mb-3" />
          <p className="text-gray-500">لا توجد نسخ احتياطية بعد</p>
        </div>
      ) : (
        <div className="card overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-gray-200 dark:border-gray-700 text-right text-sm text-gray-500">
                <th className="pb-3 pr-4 font-medium">الملف</th>
                <th className="pb-3 font-medium">الحجم</th>
                <th className="pb-3 font-medium">البصمة</th>
                <th className="pb-3 font-medium">التسليم الخارجي</th>
                <th className="pb-3 font-medium">التاريخ</th>
                <th className="pb-3 pl-4 font-medium">الإجراءات</th>
              </tr>
            </thead>
            <tbody>
              {backups.map((b: any) => {
                const delivery = DELIVERY_BADGES[b.delivery_status] || {
                  label: b.delivery_status || 'غير معروف',
                  cls: 'badge-gray',
                };
                const scope = SCOPE_BADGES[b.scope] || SCOPE_BADGES.FULL;
                return (
                <tr key={b.id} className="border-b border-gray-100 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700/50">
                  <td className="py-3 pr-4">
                    <p className="font-medium text-sm">{b.filename}</p>
                    <div className="flex items-center gap-1.5 mt-0.5 flex-wrap">
                      <span className={`badge ${scope.cls} text-[10px]`}>{scope.label}</span>
                      {b.note && <span className="text-xs text-gray-500">{b.note}</span>}
                    </div>
                    {!b.exists_on_disk && (
                      <span className="badge badge-danger text-[10px]">الملف غير موجود</span>
                    )}
                  </td>
                  <td className="text-sm whitespace-nowrap">{b.size_kb} KB</td>
                  <td className="text-xs font-mono text-gray-400">{b.checksum?.slice(0, 10)}...</td>
                  <td className="text-sm whitespace-nowrap">
                    <span className={`badge ${delivery.cls} text-[10px] flex items-center gap-1 w-fit`}>
                      {b.delivery_status === 'BOTH' ? (
                        <CheckCircle2 className="w-3 h-3" />
                      ) : b.delivery_status === 'DELIVERY_FAILED' ? (
                        <XCircle className="w-3 h-3" />
                      ) : (
                        <CircleDashed className="w-3 h-3" />
                      )}
                      {delivery.label}
                    </span>
                    {b.delivered_at && (
                      <p className="text-[10px] text-gray-400 mt-0.5">
                        {new Date(b.delivered_at).toLocaleString('ar', { dateStyle: 'short', timeStyle: 'short' })}
                      </p>
                    )}
                  </td>
                  <td className="text-xs text-gray-500 whitespace-nowrap">
                    {new Date(b.created_at).toLocaleString('ar', { dateStyle: 'short', timeStyle: 'short' })}
                  </td>
                  <td className="pl-4">
                    <div className="flex gap-1 justify-end">
                      <button
                        onClick={() => { setVerifying(b.id); verifyMutation.mutate(b.id); }}
                        disabled={verifying === b.id}
                        className="p-2 hover:bg-emerald-50 dark:hover:bg-emerald-900/30 rounded-lg"
                        title="فحص السلامة"
                      >
                        <ShieldCheck className="w-4 h-4 text-emerald-600" />
                      </button>
                      <button
                        onClick={() => deliverMutation.mutate(b.id)}
                        disabled={!b.exists_on_disk || deliverMutation.isPending}
                        className="p-2 hover:bg-cyan-50 dark:hover:bg-cyan-900/30 rounded-lg disabled:opacity-30"
                        title="إعادة التسليم الخارجي (تلجرام / التخزين السحابي حسب الإعدادات)"
                      >
                        <Send className="w-4 h-4 text-cyan-600" />
                      </button>
                      <button
                        onClick={() => downloadMutation.mutate(b.id)}
                        disabled={!b.exists_on_disk}
                        className="p-2 hover:bg-primary-50 dark:hover:bg-primary-900/30 rounded-lg disabled:opacity-30"
                        title="تنزيل"
                      >
                        <Download className="w-4 h-4 text-primary-600" />
                      </button>
                      <button
                        onClick={() => {
                          const conf = prompt(`تحذير خطير: استعادة النسخة «${b.filename}» ستقوم بمسح قاعدة البيانات الحالية بالكامل وإرجاعها لهذه النسخة.\nاكتب "تأكيد" للمتابعة:`);
                          if (conf === 'تأكيد') {
                              restoreMutation.mutate(b.id);
                          } else if (conf !== null) {
                              toast.error('تم إلغاء الاستعادة. الكلمة غير متطابقة.');
                          }
                        }}
                        disabled={!b.exists_on_disk || restoreMutation.isPending}
                        className="p-2 hover:bg-orange-50 dark:hover:bg-orange-900/30 rounded-lg disabled:opacity-30"
                        title="استعادة (تتطلب تأكيد)"
                      >
                        <RotateCcw className="w-4 h-4 text-orange-600" />
                      </button>
                      <button
                        onClick={() => {
                          if (confirm(`حذف نسخة «${b.filename}» نهائياً؟`)) deleteMutation.mutate(b.id);
                        }}
                        className="p-2 hover:bg-red-50 dark:hover:bg-red-900/30 rounded-lg"
                        title="حذف"
                      >
                        <Trash2 className="w-4 h-4 text-red-500" />
                      </button>
                    </div>
                  </td>
                </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
