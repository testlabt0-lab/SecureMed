import React, { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import Modal from '../common/Modal';
import { labAPI } from '../../api/extendedApis';

export default function CreateLabOrderModal({ isOpen, onClose }: { isOpen: boolean; onClose: () => void }) {
  const qc = useQueryClient();
  const [formData, setFormData] = useState({
    patient_name: '',
    doctor_name: '',
    test_name: '',
    test_category: 'HEMATOLOGY',
    priority: 'ROUTINE',
    clinical_notes: ''
  });

  const mutation = useMutation({
    mutationFn: (data: any) => labAPI.createOrder(data),
    onSuccess: () => {
      toast.success('تم إصدار طلب التحليل بنجاح');
      qc.invalidateQueries({ queryKey: ['lab-orders'] });
      qc.invalidateQueries({ queryKey: ['lab-stats'] });
      onClose();
    },
    onError: () => toast.error('فشل إصدار طلب التحليل')
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    mutation.mutate(formData);
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="طلب تحليل جديد">
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
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">اسم الفحص المطلوب</label>
          <input
            required
            type="text"
            className="w-full border border-gray-300 dark:border-gray-600 rounded-lg p-2 bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
            value={formData.test_name}
            onChange={e => setFormData({ ...formData, test_name: e.target.value })}
          />
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">التصنيف</label>
            <select
              className="w-full border border-gray-300 dark:border-gray-600 rounded-lg p-2 bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
              value={formData.test_category}
              onChange={e => setFormData({ ...formData, test_category: e.target.value })}
            >
              <option value="HEMATOLOGY">أمراض الدم (Hematology)</option>
              <option value="BIOCHEMISTRY">كيمياء حيوية (Biochemistry)</option>
              <option value="MICROBIOLOGY">أحياء دقيقة (Microbiology)</option>
              <option value="PATHOLOGY">علم الأمراض (Pathology)</option>
              <option value="IMMUNOLOGY">علم المناعة (Immunology)</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">الأولوية</label>
            <select
              className="w-full border border-gray-300 dark:border-gray-600 rounded-lg p-2 bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
              value={formData.priority}
              onChange={e => setFormData({ ...formData, priority: e.target.value })}
            >
              <option value="ROUTINE">عادي (Routine)</option>
              <option value="URGENT">عاجل (Urgent)</option>
              <option value="STAT">فوري (STAT)</option>
            </select>
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">ملاحظات سريرية</label>
          <textarea
            className="w-full border border-gray-300 dark:border-gray-600 rounded-lg p-2 bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
            rows={3}
            value={formData.clinical_notes}
            onChange={e => setFormData({ ...formData, clinical_notes: e.target.value })}
          />
        </div>

        <div className="flex justify-end gap-3 pt-4 border-t border-gray-100 dark:border-gray-700">
          <button type="button" onClick={onClose} className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 hover:bg-gray-200 dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600 rounded-xl transition-colors">
            إلغاء
          </button>
          <button type="submit" disabled={mutation.isPending} className="px-4 py-2 text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 rounded-xl transition-colors">
            {mutation.isPending ? 'جاري الإصدار...' : 'إصدار الطلب'}
          </button>
        </div>
      </form>
    </Modal>
  );
}
