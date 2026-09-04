import React, { useState, useEffect } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import { User, Calendar, Clock, FileText, Stethoscope, AlertCircle, Loader2 } from 'lucide-react';
import Modal from '../common/Modal';
import { telemedicineAPI } from '../../api/extendedApis';
import { patientsAPI } from '../../api/client';

interface CreateSessionModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess?: () => void;
}

export default function CreateSessionModal({ isOpen, onClose, onSuccess }: CreateSessionModalProps) {
  const qc = useQueryClient();

  // Fetch patients for selection
  const { data: patientsData, isLoading: isLoadingPatients } = useQuery({
    queryKey: ['patients-list'],
    queryFn: () => patientsAPI.list(),
    enabled: isOpen,
  });

  const patients = Array.isArray(patientsData?.data?.results)
    ? patientsData.data.results
    : Array.isArray(patientsData?.data)
    ? patientsData.data
    : [];

  // Default to 15 minutes from now in local ISO string for datetime-local
  const getDefaultScheduledTime = () => {
    const d = new Date(Date.now() + 15 * 60000);
    const tzOffset = d.getTimezoneOffset() * 60000;
    return new Date(d.getTime() - tzOffset).toISOString().slice(0, 16);
  };

  const [formData, setFormData] = useState({
    patient: '',
    scheduled_at: getDefaultScheduledTime(),
    duration_minutes: 30,
    notes: '',
    diagnosis: '',
  });

  useEffect(() => {
    if (isOpen && patients.length > 0 && !formData.patient) {
      setFormData(prev => ({ ...prev, patient: patients[0].id }));
    }
  }, [isOpen, patients]);

  const mutation = useMutation({
    mutationFn: (data: any) => telemedicineAPI.createConsultation(data),
    onSuccess: () => {
      toast.success('تمت جدولة جلسة الاستشارة الافتراضية بنجاح');
      qc.invalidateQueries({ queryKey: ['telemedicine-sessions'] });
      onSuccess?.();
      onClose();
    },
    onError: (err: any) => {
      const msg = err.response?.data?.patient?.[0] || err.response?.data?.detail || 'فشل جدولة الجلسة';
      toast.error(msg);
    }
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.patient) {
      toast.error('يرجى اختيار المريض');
      return;
    }

    mutation.mutate({
      patient: formData.patient,
      scheduled_at: formData.scheduled_at,
      notes: formData.notes.trim(),
      diagnosis: formData.diagnosis.trim(),
    });
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="جدولة استشارة طبية عن بعد" maxWidth="max-w-lg">
      <form onSubmit={handleSubmit} className="space-y-4">
        {/* Patient Selection */}
        <div>
          <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1.5 flex items-center gap-1.5">
            <User className="w-3.5 h-3.5 text-primary-500" />
            المريض <span className="text-red-500">*</span>
          </label>
          {isLoadingPatients ? (
            <div className="flex items-center gap-2 p-2.5 text-xs text-gray-500 bg-gray-50 dark:bg-gray-700/50 rounded-xl">
              <Loader2 className="w-4 h-4 animate-spin text-primary-500" />
              جارٍ تحميل قائمة المرضى...
            </div>
          ) : patients.length === 0 ? (
            <div className="p-3 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-xl text-amber-800 dark:text-amber-300 text-xs flex items-center gap-2">
              <AlertCircle className="w-4 h-4 flex-shrink-0" />
              <span>لا يوجد مرضى مسجلين بالنظام حالياً. يرجى إضافة مريض أولاً.</span>
            </div>
          ) : (
            <select
              required
              className="w-full px-3 py-2.5 text-sm bg-gray-50 dark:bg-gray-700/50 border border-gray-200 dark:border-gray-700 rounded-xl focus:ring-2 focus:ring-primary-500 focus:outline-none text-gray-900 dark:text-white"
              value={formData.patient}
              onChange={e => setFormData({ ...formData, patient: e.target.value })}
            >
              {patients.map((p: any) => (
                <option key={p.id} value={p.id}>
                  {p.full_name} {p.national_id ? `(هوية: ${p.national_id})` : ''}
                </option>
              ))}
            </select>
          )}
        </div>

        {/* Date & Time */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div>
            <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1.5 flex items-center gap-1.5">
              <Calendar className="w-3.5 h-3.5 text-primary-500" />
              وقت الجلسة <span className="text-red-500">*</span>
            </label>
            <input
              required
              type="datetime-local"
              className="w-full px-3 py-2 text-sm bg-gray-50 dark:bg-gray-700/50 border border-gray-200 dark:border-gray-700 rounded-xl focus:ring-2 focus:ring-primary-500 focus:outline-none text-gray-900 dark:text-white"
              value={formData.scheduled_at}
              onChange={e => setFormData({ ...formData, scheduled_at: e.target.value })}
            />
          </div>
          <div>
            <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1.5 flex items-center gap-1.5">
              <Clock className="w-3.5 h-3.5 text-primary-500" />
              المدة المقدرة (بالدقائق)
            </label>
            <select
              className="w-full px-3 py-2 text-sm bg-gray-50 dark:bg-gray-700/50 border border-gray-200 dark:border-gray-700 rounded-xl focus:ring-2 focus:ring-primary-500 focus:outline-none text-gray-900 dark:text-white"
              value={formData.duration_minutes}
              onChange={e => setFormData({ ...formData, duration_minutes: parseInt(e.target.value) })}
            >
              <option value="15">15 دقيقة</option>
              <option value="30">30 دقيقة</option>
              <option value="45">45 دقيقة</option>
              <option value="60">60 دقيقة (ساعة)</option>
            </select>
          </div>
        </div>

        {/* Diagnosis / Initial Assessment */}
        <div>
          <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1.5 flex items-center gap-1.5">
            <Stethoscope className="w-3.5 h-3.5 text-primary-500" />
            التشخيص المبدئي أو التخصص المطلوب
          </label>
          <input
            type="text"
            placeholder="مثال: استشارة باطنية عامة، متابعة أعراض تنفسية..."
            className="w-full px-3 py-2 text-sm bg-gray-50 dark:bg-gray-700/50 border border-gray-200 dark:border-gray-700 rounded-xl focus:ring-2 focus:ring-primary-500 focus:outline-none text-gray-900 dark:text-white"
            value={formData.diagnosis}
            onChange={e => setFormData({ ...formData, diagnosis: e.target.value })}
          />
        </div>

        {/* Clinical Notes / Consultation Reason */}
        <div>
          <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1.5 flex items-center gap-1.5">
            <FileText className="w-3.5 h-3.5 text-primary-500" />
            ملاحظات الطبيب وسبب الاستشارة
          </label>
          <textarea
            rows={3}
            placeholder="اكتب أي معلومات توضيحية أو تاريخ مرضي للجلسة..."
            className="w-full px-3 py-2 text-sm bg-gray-50 dark:bg-gray-700/50 border border-gray-200 dark:border-gray-700 rounded-xl focus:ring-2 focus:ring-primary-500 focus:outline-none text-gray-900 dark:text-white"
            value={formData.notes}
            onChange={e => setFormData({ ...formData, notes: e.target.value })}
          />
        </div>

        {/* Action Buttons */}
        <div className="flex justify-end gap-2 pt-3 border-t border-gray-100 dark:border-gray-700">
          <button
            type="button"
            onClick={onClose}
            className="btn-secondary text-sm px-4 py-2"
          >
            إلغاء
          </button>
          <button
            type="submit"
            disabled={mutation.isPending || !formData.patient}
            className="btn-primary text-sm px-5 py-2 inline-flex items-center gap-2"
          >
            {mutation.isPending ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                جارٍ الجدولة...
              </>
            ) : (
              'تأكيد وجدولة الجلسة'
            )}
          </button>
        </div>
      </form>
    </Modal>
  );
}
