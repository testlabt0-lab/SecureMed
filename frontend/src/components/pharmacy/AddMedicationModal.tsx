import React, { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import Modal from '../common/Modal';
import { pharmacyAPI } from '../../api/extendedApis';

export default function AddMedicationModal({ isOpen, onClose }: { isOpen: boolean; onClose: () => void }) {
  const qc = useQueryClient();
  const [formData, setFormData] = useState({
    name: '',
    generic_name: '',
    category: '',
    stock_quantity: 0,
    minimum_stock: 10,
    unit: '',
    price: 0,
    expiry_date: ''
  });

  const mutation = useMutation({
    mutationFn: (data: any) => pharmacyAPI.createMedication(data),
    onSuccess: () => {
      toast.success('تمت إضافة الدواء بنجاح');
      qc.invalidateQueries({ queryKey: ['pharmacy-medications'] });
      qc.invalidateQueries({ queryKey: ['pharmacy-stats'] });
      onClose();
    },
    onError: () => toast.error('فشل في إضافة الدواء')
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    mutation.mutate(formData);
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="إضافة دواء جديد">
      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">اسم الدواء (التجاري)</label>
            <input
              required
              type="text"
              className="w-full border border-gray-300 dark:border-gray-600 rounded-lg p-2 bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
              value={formData.name}
              onChange={e => setFormData({ ...formData, name: e.target.value })}
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">الاسم العلمي</label>
            <input
              type="text"
              className="w-full border border-gray-300 dark:border-gray-600 rounded-lg p-2 bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
              value={formData.generic_name}
              onChange={e => setFormData({ ...formData, generic_name: e.target.value })}
            />
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">التصنيف</label>
            <select
              required
              className="w-full border border-gray-300 dark:border-gray-600 rounded-lg p-2 bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
              value={formData.category}
              onChange={e => setFormData({ ...formData, category: e.target.value })}
            >
              <option value="">اختر التصنيف...</option>
              <option value="ANALGESIC">مسكنات</option>
              <option value="ANTIBIOTIC">مضادات حيوية</option>
              <option value="CARDIOVASCULAR">أدوية قلب</option>
              <option value="RESPIRATORY">جهاز تنفسي</option>
              <option value="GASTROINTESTINAL">جهاز هضمي</option>
              <option value="ENDOCRINE">غدد صماء</option>
              <option value="NEUROLOGICAL">أعصاب</option>
              <option value="PSYCHIATRIC">نفسية</option>
              <option value="DERMATOLOGICAL">جلدية</option>
              <option value="OPHTHALMIC">عيون</option>
              <option value="OTHER">أخرى</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">تاريخ الصلاحية</label>
            <input
              required
              type="date"
              className="w-full border border-gray-300 dark:border-gray-600 rounded-lg p-2 bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
              value={formData.expiry_date}
              onChange={e => setFormData({ ...formData, expiry_date: e.target.value })}
            />
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">الكمية المتوفرة</label>
            <input
              required
              type="number"
              min="0"
              className="w-full border border-gray-300 dark:border-gray-600 rounded-lg p-2 bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
              value={formData.stock_quantity}
              onChange={e => setFormData({ ...formData, stock_quantity: parseInt(e.target.value) })}
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">الحد الأدنى</label>
            <input
              required
              type="number"
              min="0"
              className="w-full border border-gray-300 dark:border-gray-600 rounded-lg p-2 bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
              value={formData.minimum_stock}
              onChange={e => setFormData({ ...formData, minimum_stock: parseInt(e.target.value) })}
            />
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">الوحدة</label>
            <input
              required
              type="text"
              placeholder="شريط، علبة، الخ..."
              className="w-full border border-gray-300 dark:border-gray-600 rounded-lg p-2 bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
              value={formData.unit}
              onChange={e => setFormData({ ...formData, unit: e.target.value })}
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">السعر</label>
            <input
              required
              type="number"
              min="0"
              step="0.01"
              className="w-full border border-gray-300 dark:border-gray-600 rounded-lg p-2 bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
              value={formData.price}
              onChange={e => setFormData({ ...formData, price: parseFloat(e.target.value) })}
            />
          </div>
        </div>

        <div className="flex justify-end gap-3 pt-4 border-t border-gray-100 dark:border-gray-700">
          <button type="button" onClick={onClose} className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 hover:bg-gray-200 dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600 rounded-xl transition-colors">
            إلغاء
          </button>
          <button type="submit" disabled={mutation.isPending} className="px-4 py-2 text-sm font-medium text-white bg-primary-600 hover:bg-primary-700 disabled:opacity-50 rounded-xl transition-colors">
            {mutation.isPending ? 'جاري الحفظ...' : 'حفظ الدواء'}
          </button>
        </div>
      </form>
    </Modal>
  );
}
