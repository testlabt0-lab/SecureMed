import React, { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import Modal from '../common/Modal';
import { telemedicineAPI } from '../../api/extendedApis';

export default function CreateSessionModal({ isOpen, onClose }: { isOpen: boolean; onClose: () => void }) {
  const qc = useQueryClient();
  const [formData, setFormData] = useState({
    patient_name: '',
    scheduled_at: '',
    duration_minutes: 30,
    notes: ''
  });

  const mutation = useMutation({
    mutationFn: (data: any) => telemedicineAPI.createConsultation(data),
    onSuccess: () => {
      toast.success('تم جدولة الجلسة بنجاح');
      qc.invalidateQueries({ queryKey: ['telemedicine-sessions'] });
      onClose();
    },
    onError: () => toast.error('فشل جدولة الجلسة')
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    mutation.mutate({
      ...formData,
      status: 'SCHEDULED'
    });
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="جلسة استشارة جديدة">
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">اسم المريض</label>
          <input
            required
            type="text"
            className="w-full border border-gray-300 dark:border-gray-600 rounded-lg p-2 bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
            value={formData.patient_name}
            onChange={e => setFormData({ ...formData, patient_name: e.target.value })}
          />
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">وقت الجلسة</label>
            <input
              required
              type="datetime-local"
              className="w-full border border-gray-300 dark:border-gray-600 rounded-lg p-2 bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
              value={formData.scheduled_at}
              onChange={e => setFormData({ ...formData, scheduled_at: e.target.value })}
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">المدة (بالدقائق)</label>
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

        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">ملاحظات / سبب الاستشارة</label>
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
            {mutation.isPending ? 'جاري الجدولة...' : 'جدولة الجلسة'}
          </button>
        </div>
      </form>
    </Modal>
  );
}
