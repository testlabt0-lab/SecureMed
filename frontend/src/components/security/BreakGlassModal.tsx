import React, { useState } from 'react';
import { ShieldAlert, AlertTriangle, Clock, Lock, Loader2, Hospital } from 'lucide-react';
import Modal from '../common/Modal';
import api from '../../api/client';
import toast from 'react-hot-toast';

interface BreakGlassModalProps {
  isOpen: boolean;
  onClose: () => void;
  patientId: string;
  patientName: string;
  onSuccess: (breakGlassData: any) => void;
}

const DEPARTMENTS = [
  { value: 'قسم الطوارئ (ER)', label: 'قسم الطوارئ (ER)' },
  { value: 'العناية المركزة (ICU)', label: 'العناية المركزة (ICU)' },
  { value: 'العمليات الجراحية (OR)', label: 'العمليات الجراحية (OR)' },
  { value: 'قسطرة القلب والشرايين', label: 'قسطرة القلب والشرايين' },
  { value: 'أخرى - استدعاء إسعافي', label: 'أخرى - استدعاء إسعافي' },
];

export default function BreakGlassModal({
  isOpen,
  onClose,
  patientId,
  patientName,
  onSuccess,
}: BreakGlassModalProps) {
  const [department, setDepartment] = useState(DEPARTMENTS[0].value);
  const [reason, setReason] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const minChars = 20;
  const isReasonValid = reason.trim().length >= minChars;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!isReasonValid) {
      toast.error(`يجب كتابة تبرير إسعافي يحتوي على ${minChars} حرفاً على الأقل`);
      return;
    }

    try {
      setIsSubmitting(true);
      const res = await api.post('/security/break-glass/activate/', {
        patient_id: patientId,
        reason: reason.trim(),
        department,
      });

      toast.success(res.data.message || 'تم تفعيل وصول الطوارئ بنجاح');
      onSuccess(res.data.break_glass);
      onClose();
    } catch (err: any) {
      const detail = err.response?.data?.detail || 'فشل تفعيل بروتوكول كسر الزجاج';
      toast.error(detail);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="🚨 بروتوكول كسر الزجاج للطوارئ (Break-Glass Protocol)"
      maxWidth="max-w-xl"
    >
      <form onSubmit={handleSubmit} className="space-y-5">
        {/* Warning Banner */}
        <div className="p-4 rounded-2xl bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-900/50 flex gap-3 text-red-800 dark:text-red-200 text-sm">
          <ShieldAlert className="w-6 h-6 text-red-600 dark:text-red-400 shrink-0 mt-0.5 animate-pulse" />
          <div className="space-y-1">
            <p className="font-bold">تنبيه أمني وطبي عالي الخطورة (HIPAA Security Rule)</p>
            <p className="text-xs text-red-700 dark:text-red-300 leading-relaxed">
              أنت على وشك تجاوز ضوابط الوصول العادية لفتح السجل الطبي للمريض <strong>{patientName}</strong>. 
              يُسمح بهذا الإجراء حصراً لإنقاذ حياة المريض في الحالات الإسعافية الحرجة.
            </p>
          </div>
        </div>

        {/* Audit Notice */}
        <div className="bg-amber-50 dark:bg-amber-950/30 p-3 rounded-xl border border-amber-200 dark:border-amber-800/40 text-xs text-amber-800 dark:text-amber-300 flex items-start gap-2">
          <AlertTriangle className="w-4 h-4 text-amber-600 dark:text-amber-400 shrink-0 mt-0.5" />
          <span>
            سيتم إرسال تنبيه فوري لإدارة الأمن والمستشفى عبر <strong>Telegram Bot</strong> وقنوات المراقبة، وتوثيق بصمة جهازك وعنوان IP في سلسلة تدقيق مشفرة غير قابلة للتعديل.
          </span>
        </div>

        {/* Department Selection */}
        <div>
          <label className="block text-sm font-semibold text-gray-700 dark:text-gray-300 mb-1.5 flex items-center gap-1.5">
            <Hospital className="w-4 h-4 text-primary-500" />
            القسم الإسعافي الطالب للوصول:
          </label>
          <select
            value={department}
            onChange={(e) => setDepartment(e.target.value)}
            className="w-full px-3 py-2.5 rounded-xl border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-white text-sm focus:ring-2 focus:ring-red-500 focus:border-transparent outline-none"
          >
            {DEPARTMENTS.map((dept) => (
              <option key={dept.value} value={dept.value}>
                {dept.label}
              </option>
            ))}
          </select>
        </div>

        {/* Emergency Medical Reason */}
        <div>
          <div className="flex justify-between items-center mb-1.5">
            <label className="block text-sm font-semibold text-gray-700 dark:text-gray-300">
              التبرير الطبي الإسعافي (مطلوب):
            </label>
            <span
              className={`text-xs font-mono ${
                isReasonValid ? 'text-green-600 dark:text-green-400' : 'text-gray-400 dark:text-gray-500'
              }`}
            >
              {reason.trim().length} / {minChars} حرفاً كحد أدنى
            </span>
          </div>
          <textarea
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            placeholder="اكتب وصفاً سريرياً دقيقاً للحالة الإسعافية الطارئة (مثلاً: توقف مفاجئ في عضلة القلب أو غيبوبة غير معلومة وتطلب التدخل السريع لمعرفة الحساسية والتاريخ الدوائي)..."
            rows={4}
            className="w-full p-3.5 rounded-2xl border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-white text-sm focus:ring-2 focus:ring-red-500 focus:border-transparent outline-none transition-all placeholder:text-gray-400"
          />
        </div>

        {/* Access Expiration Info */}
        <div className="flex items-center gap-2 text-xs text-gray-500 dark:text-gray-400 bg-gray-50 dark:bg-gray-900/40 p-2.5 rounded-xl">
          <Clock className="w-4 h-4 text-gray-400 shrink-0" />
          <span>مدة صلاحية الوصول الإسعافي: <strong>4 ساعات</strong>، ويمكن إنهاؤها يدوياً فور استقرار المريض.</span>
        </div>

        {/* Action Buttons */}
        <div className="flex items-center justify-end gap-3 pt-2">
          <button
            type="button"
            onClick={onClose}
            disabled={isSubmitting}
            className="px-5 py-2.5 rounded-xl border border-gray-300 dark:border-gray-700 text-gray-700 dark:text-gray-300 text-sm font-medium hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
          >
            إلغاء
          </button>
          <button
            type="submit"
            disabled={!isReasonValid || isSubmitting}
            className={`px-6 py-2.5 rounded-xl text-sm font-bold flex items-center gap-2 shadow-lg transition-all ${
              isReasonValid && !isSubmitting
                ? 'bg-gradient-to-r from-red-600 to-red-700 hover:from-red-700 hover:to-red-800 text-white shadow-red-500/25 hover:shadow-red-500/40 active:scale-95'
                : 'bg-gray-200 dark:bg-gray-800 text-gray-400 cursor-not-allowed shadow-none'
            }`}
          >
            {isSubmitting ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                جارِ تفعيل البروتوكول...
              </>
            ) : (
              <>
                <ShieldAlert className="w-4 h-4" />
                تأكيد كسر الزجاج وفتح الملف الإسعافي
              </>
            )}
          </button>
        </div>
      </form>
    </Modal>
  );
}
