import React, { useState, useEffect } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import Modal from '../common/Modal';
import { appointmentsAPI } from '../../api/extendedApis';
import { patientsAPI, usersAPI } from '../../api/client';
import { useAuthStore } from '../../store/authStore';

export default function CreateAppointmentModal({ isOpen, onClose }: { isOpen: boolean; onClose: () => void }) {
  const qc = useQueryClient();
  const { user } = useAuthStore();
  const [formData, setFormData] = useState({
    title: '',
    patient: '',
    doctor: user?.role === 'DOCTOR' ? user.id : '',
    appointment_type: 'CONSULTATION',
    priority: 'MEDIUM',
    scheduled_at: '',
    duration_minutes: 30,
    is_virtual: false,
    notes: ''
  });

  const { data: patientsData, isLoading: isLoadingPatients } = useQuery({
    queryKey: ['patients-list'],
    queryFn: () => patientsAPI.list(),
    enabled: isOpen,
  });

  const { data: doctorsData, isLoading: isLoadingDoctors } = useQuery({
    queryKey: ['doctors-list'],
    queryFn: () => usersAPI.byRole('DOCTOR'),
    enabled: isOpen && user?.role !== 'DOCTOR',
  });

  const patients = Array.isArray(patientsData?.data?.results)
    ? patientsData.data.results
    : Array.isArray(patientsData?.data)
    ? patientsData.data
    : [];

  const doctors = Array.isArray(doctorsData?.data?.results)
    ? doctorsData.data.results
    : Array.isArray(doctorsData?.data)
    ? doctorsData.data
    : [];

  useEffect(() => {
    if (isOpen && patients.length > 0 && !formData.patient) {
      setFormData(prev => ({ ...prev, patient: patients[0].id }));
    }
  }, [isOpen, patients]);

  useEffect(() => {
    if (isOpen && doctors.length > 0 && !formData.doctor && user?.role !== 'DOCTOR') {
      setFormData(prev => ({ ...prev, doctor: doctors[0].id }));
    }
  }, [isOpen, doctors]);

  const mutation = useMutation({
    mutationFn: (data: any) => appointmentsAPI.create(data),
    onSuccess: () => {
      toast.success('تمت إضافة الموعد بنجاح');
      qc.invalidateQueries({ queryKey: ['appointments-list'] });
      qc.invalidateQueries({ queryKey: ['appointments-calendar'] });
      qc.invalidateQueries({ queryKey: ['appointments-stats'] });
      onClose();
    },
    onError: () => toast.error('فشل في إضافة الموعد')
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.patient || !formData.doctor) {
      toast.error('يرجى اختيار المريض والطبيب');
      return;
    }
    mutation.mutate(formData);
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="إضافة موعد جديد">
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">عنوان الموعد</label>
          <input
            required
            type="text"
            className="w-full border border-gray-300 dark:border-gray-600 rounded-lg p-2 bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
            value={formData.title}
            onChange={e => setFormData({ ...formData, title: e.target.value })}
          />
        </div>
        
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">المريض</label>
            <select
              required
              className="w-full border border-gray-300 dark:border-gray-600 rounded-lg p-2 bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
              value={formData.patient}
              onChange={e => setFormData({ ...formData, patient: e.target.value })}
            >
              <option value="" disabled>اختر المريض...</option>
              {patients.map((p: any) => (
                <option key={p.id} value={p.id}>{p.full_name} {p.national_id ? `(${p.national_id})` : ''}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">الطبيب</label>
            <select
              required
              className="w-full border border-gray-300 dark:border-gray-600 rounded-lg p-2 bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
              value={formData.doctor}
              onChange={e => setFormData({ ...formData, doctor: e.target.value })}
              disabled={user?.role === 'DOCTOR'}
            >
              <option value="" disabled>اختر الطبيب...</option>
              {user?.role === 'DOCTOR' ? (
                <option value={user.id}>{user.full_name}</option>
              ) : (
                doctors.map((d: any) => (
                  <option key={d.id} value={d.id}>{d.full_name}</option>
                ))
              )}
            </select>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">التاريخ والوقت</label>
            <input
              required
              type="datetime-local"
              className="w-full border border-gray-300 dark:border-gray-600 rounded-lg p-2 bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
              value={formData.scheduled_at}
              onChange={e => setFormData({ ...formData, scheduled_at: e.target.value })}
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">المدة (دقائق)</label>
            <input
              required
              type="number"
              min="15"
              step="15"
              className="w-full border border-gray-300 dark:border-gray-600 rounded-lg p-2 bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
              value={formData.duration_minutes}
              onChange={e => setFormData({ ...formData, duration_minutes: parseInt(e.target.value) })}
            />
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">نوع الموعد</label>
            <select
              className="w-full border border-gray-300 dark:border-gray-600 rounded-lg p-2 bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
              value={formData.appointment_type}
              onChange={e => setFormData({ ...formData, appointment_type: e.target.value })}
            >
              <option value="CONSULTATION">استشارة</option>
              <option value="FOLLOW_UP">مراجعة</option>
              <option value="CHECKUP">فحص عام</option>
              <option value="EMERGENCY">حالة طارئة</option>
              <option value="PROCEDURE">إجراء طبي</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">الأولوية</label>
            <select
              className="w-full border border-gray-300 dark:border-gray-600 rounded-lg p-2 bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
              value={formData.priority}
              onChange={e => setFormData({ ...formData, priority: e.target.value })}
            >
              <option value="LOW">منخفضة</option>
              <option value="MEDIUM">متوسطة</option>
              <option value="HIGH">عالية</option>
              <option value="URGENT">عاجلة</option>
            </select>
          </div>
        </div>

        <div className="flex items-center gap-2 mt-4">
          <input
            type="checkbox"
            id="is_virtual"
            checked={formData.is_virtual}
            onChange={e => setFormData({ ...formData, is_virtual: e.target.checked })}
            className="w-4 h-4 text-primary-600 rounded border-gray-300 focus:ring-primary-500"
          />
          <label htmlFor="is_virtual" className="text-sm text-gray-700 dark:text-gray-300">موعد افتراضي (عن بعد)</label>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">ملاحظات إضافية</label>
          <textarea
            className="w-full border border-gray-300 dark:border-gray-600 rounded-lg p-2 bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
            rows={3}
            value={formData.notes}
            onChange={e => setFormData({ ...formData, notes: e.target.value })}
          />
        </div>

        <div className="flex justify-end gap-3 pt-4 border-t border-gray-100 dark:border-gray-700">
          <button type="button" onClick={onClose} className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 hover:bg-gray-200 dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600 rounded-xl transition-colors">
            إلغاء
          </button>
          <button type="submit" disabled={mutation.isPending} className="px-4 py-2 text-sm font-medium text-white bg-primary-600 hover:bg-primary-700 disabled:opacity-50 rounded-xl transition-colors">
            {mutation.isPending ? 'جاري الحفظ...' : 'حفظ الموعد'}
          </button>
        </div>
      </form>
    </Modal>
  );
}
