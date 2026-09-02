import React, { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import Modal from '../common/Modal';
import { billingAPI } from '../../api/extendedApis';

export default function CreateInvoiceModal({ isOpen, onClose }: { isOpen: boolean; onClose: () => void }) {
  const qc = useQueryClient();
  const [formData, setFormData] = useState({
    patient_name: '',
    items: [{ description: '', amount: 0 }]
  });

  const mutation = useMutation({
    mutationFn: (data: any) => {
      const total_amount = data.items.reduce((sum: number, item: any) => sum + item.amount, 0);
      return billingAPI.createInvoice({ ...data, total_amount });
    },
    onSuccess: () => {
      toast.success('تم إصدار الفاتورة بنجاح');
      qc.invalidateQueries({ queryKey: ['billing-invoices'] });
      qc.invalidateQueries({ queryKey: ['billing-stats'] });
      onClose();
    },
    onError: () => toast.error('فشل إصدار الفاتورة')
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    mutation.mutate(formData);
  };

  const addItem = () => setFormData({ ...formData, items: [...formData.items, { description: '', amount: 0 }] });
  const updateItem = (index: number, field: string, value: string | number) => {
    const newItems = [...formData.items];
    newItems[index] = { ...newItems[index], [field]: value };
    setFormData({ ...formData, items: newItems });
  };
  const removeItem = (index: number) => {
    const newItems = formData.items.filter((_, i) => i !== index);
    setFormData({ ...formData, items: newItems });
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="إصدار فاتورة جديدة">
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

        <div className="space-y-2">
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">عناصر الفاتورة</label>
          {formData.items.map((item, idx) => (
            <div key={idx} className="flex gap-2 items-center">
              <input
                required
                type="text"
                placeholder="الوصف (مثال: كشف طبي)"
                className="flex-1 border border-gray-300 dark:border-gray-600 rounded-lg p-2 bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                value={item.description}
                onChange={e => updateItem(idx, 'description', e.target.value)}
              />
              <input
                required
                type="number"
                placeholder="المبلغ"
                min="0"
                step="0.01"
                className="w-32 border border-gray-300 dark:border-gray-600 rounded-lg p-2 bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                value={item.amount}
                onChange={e => updateItem(idx, 'amount', parseFloat(e.target.value))}
              />
              {formData.items.length > 1 && (
                <button type="button" onClick={() => removeItem(idx)} className="p-2 text-red-500 hover:bg-red-50 rounded-lg">
                  &times;
                </button>
              )}
            </div>
          ))}
          <button type="button" onClick={addItem} className="text-sm text-indigo-600 hover:text-indigo-700 font-medium mt-2">
            + إضافة عنصر آخر
          </button>
        </div>

        <div className="flex justify-between items-center bg-gray-50 dark:bg-gray-800 p-3 rounded-lg border border-gray-200 dark:border-gray-700">
          <span className="font-bold text-gray-700 dark:text-gray-300">الإجمالي:</span>
          <span className="font-bold text-indigo-600 dark:text-indigo-400 text-lg">
            {formData.items.reduce((sum, item) => sum + (item.amount || 0), 0).toFixed(2)} ريال
          </span>
        </div>

        <div className="flex justify-end gap-3 pt-4 border-t border-gray-100 dark:border-gray-700">
          <button type="button" onClick={onClose} className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 hover:bg-gray-200 dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600 rounded-xl transition-colors">
            إلغاء
          </button>
          <button type="submit" disabled={mutation.isPending || formData.items.length === 0} className="px-4 py-2 text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 rounded-xl transition-colors">
            {mutation.isPending ? 'جاري الإصدار...' : 'إصدار الفاتورة'}
          </button>
        </div>
      </form>
    </Modal>
  );
}
