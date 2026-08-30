import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  DatabaseBackup, Plus, Download, Trash2, ShieldCheck, HardDrive,
} from 'lucide-react';
import { backupsAPI } from '../api/client';
import { downloadBlobResponse } from '../api/extendedApis';
import toast from 'react-hot-toast';

export default function Backups() {
  const queryClient = useQueryClient();
  const [note, setNote] = useState('');
  const [verifying, setVerifying] = useState<string | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ['backups'],
    queryFn: () => backupsAPI.list(),
  });

  const createMutation = useMutation({
    mutationFn: () => backupsAPI.create(note),
    onSuccess: () => {
      toast.success('تم إنشاء النسخة الاحتياطية بنجاح');
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
          <button
            onClick={() => {
              if (confirm('إنشاء نسخة احتياطية كاملة الآن؟')) createMutation.mutate();
            }}
            disabled={createMutation.isPending}
            className="btn-primary flex items-center justify-center gap-2 whitespace-nowrap"
          >
            <Plus className="w-4 h-4" />
            {createMutation.isPending ? 'جاري الإنشاء...' : 'نسخة احتياطية الآن'}
          </button>
        </div>
        <div className="flex items-center gap-4 mt-3 text-xs text-gray-500">
          <span className="flex items-center gap-1">
            <HardDrive className="w-3.5 h-3.5" />
            {backups.length} نسخة — {(totalSize / 1024 / 1024).toFixed(2)} ميجابايت
          </span>
          <span>•</span>
          <span>يُحتفظ تلقائياً بآخر 14 نسخة</span>
          <span>•</span>
          <span>للاستعادة: <code className="bg-gray-100 dark:bg-gray-700 px-1 rounded">python manage.py restore_backup &lt;file.zip&gt;</code></span>
        </div>
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
                <th className="pb-3 font-medium">التاريخ</th>
                <th className="pb-3 pl-4 font-medium">الإجراءات</th>
              </tr>
            </thead>
            <tbody>
              {backups.map((b: any) => (
                <tr key={b.id} className="border-b border-gray-100 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700/50">
                  <td className="py-3 pr-4">
                    <p className="font-medium text-sm">{b.filename}</p>
                    {b.note && <p className="text-xs text-gray-500">{b.note}</p>}
                    {!b.exists_on_disk && (
                      <span className="badge badge-danger text-[10px]">الملف غير موجود</span>
                    )}
                  </td>
                  <td className="text-sm whitespace-nowrap">{b.size_kb} KB</td>
                  <td className="text-xs font-mono text-gray-400">{b.checksum?.slice(0, 10)}...</td>
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
                        onClick={() => downloadMutation.mutate(b.id)}
                        disabled={!b.exists_on_disk}
                        className="p-2 hover:bg-primary-50 dark:hover:bg-primary-900/30 rounded-lg disabled:opacity-30"
                        title="تنزيل"
                      >
                        <Download className="w-4 h-4 text-primary-600" />
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
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
