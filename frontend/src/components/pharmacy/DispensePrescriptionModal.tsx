import React, { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import Modal from '../common/Modal';
import { pharmacyAPI } from '../../api/extendedApis';

export default function DispensePrescriptionModal({ isOpen, onClose }: { isOpen: boolean; onClose: () => void }) {
  const qc = useQueryClient();
  const [formData, setFormData] = useState({
    patient_name: '',
    doctor_name: '',
    medication_name: '',
    dosage: '',
    quantity: 1,
    instructions: ''
  });

  const mutation = useMutation({
    mutationFn: (data: any) => pharmacyAPI.createPrescription(data),
    onSuccess: () => {
      toast.success('تم إنشاء وصرف الوصفة الطبية');
      qc.invalidateQueries({ queryKey: ['pharmacy-prescriptions'] });
      qc.invalidateQueries({ queryKey: ['pharmacy-stats'] });
      qc.invalidateQueries({ queryKey: ['pharmacy-medications'] });
      onClose();
    },
    onError: () => toast.error('فشل في صرف الوصفة الطبية')
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    mutation.mutate({
      ...formData,
      status: 'DISPENSED',
      dispensed_at: new Date().toISOString()
    });
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="صرف وصفة طبية جديدة">
      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="grid grid-cols-2 gap-4">
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
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">اسم الطبيب</label>
            <input
              required
              type="text"
              className="w-full border border-gray-300 dark:border-gray-600 rounded-lg p-2 bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
              value={formData.doctor_name}
              onChange={e => setFormData({ ...formData, doctor_name: e.target.value })}
            />
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">اسم الدواء (للتسجيل)</label>
          <input
            required
            type="text"
            className="w-full border border-gray-300 dark:border-gray-600 rounded-lg p-2 bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
            value={formData.medication_name}
            onChange={e => setFormData({ ...formData, medication_name: e.target.value })}
          />
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">الجرعة</label>
            <input
              required
              type="text"
              placeholder="مثال: حبة مرتين يوميا"
              className="w-full border border-gray-300 dark:border-gray-600 rounded-lg p-2 bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
              value={formData.dosage}
              onChange={e => setFormData({ ...formData, dosage: e.target.value })}
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">الكمية المصروفة</label>
            <input
              required
              type="number"
              min="1"
              className="w-full border border-gray-300 dark:border-gray-600 rounded-lg p-2 bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
              value={formData.quantity}
              onChange={e => setFormData({ ...formData, quantity: parseInt(e.target.value) })}
            />
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">إرشادات إضافية</label>
          <textarea
            className="w-full border border-gray-300 dark:border-gray-600 rounded-lg p-2 bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
            rows={3}
            value={formData.instructions}
            onChange={e => setFormData({ ...formData, instructions: e.target.value })}
          />
        </div>

        <div className="flex justify-end gap-3 pt-4 border-t border-gray-100 dark:border-gray-700">
          <button type="button" onClick={onClose} className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 hover:bg-gray-200 dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600 rounded-xl transition-colors">
            إلغاء
          </button>
          <button type="submit" disabled={mutation.isPending} className="px-4 py-2 text-sm font-medium text-white bg-primary-600 hover:bg-primary-700 disabled:opacity-50 rounded-xl transition-colors">
            {mutation.isPending ? 'جاري الصرف...' : 'صرف الوصفة'}
          </button>
        </div>
      </form>
    </Modal>
  );
}
