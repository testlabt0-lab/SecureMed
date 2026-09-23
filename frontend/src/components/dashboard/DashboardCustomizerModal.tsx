import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { SlidersHorizontal, Eye, EyeOff, ArrowUp, ArrowDown, RotateCcw, Check, Sparkles, LayoutGrid } from 'lucide-react';
import toast from 'react-hot-toast';
import Modal from '../common/Modal';

export interface DashboardWidgetConfig {
  id: string;
  title: string;
  description?: string;
  visible: boolean;
  order: number;
}

export const DEFAULT_WIDGETS: DashboardWidgetConfig[] = [
  {
    id: 'hero',
    title: 'شعار الترحيب والمؤشرات الحية',
    description: 'تحية الطبيب، نبض ECG الطبي، التاريخ، والوصول السريع',
    visible: true,
    order: 0,
  },
  {
    id: 'stat_cards',
    title: 'بطاقات الإحصائيات السريعة',
    description: 'إجمالي القنوات، المرضى، السجلات الطبية، وميزات الأمان',
    visible: true,
    order: 1,
  },
  {
    id: 'activity_charts',
    title: 'مخططات النشاط الأسبوعي والأولويات',
    description: 'الرسم البياني لحركة السجلات وقنوات الطوارئ والعادية',
    visible: true,
    order: 2,
  },
  {
    id: 'distribution_charts',
    title: 'توزيع القنوات والسجلات الطبية',
    description: 'توزيع القنوات حسب التخصص والسجلات حسب الفئة السريرية',
    visible: true,
    order: 3,
  },
  {
    id: 'feeds',
    title: 'خلاصة النشاطات والقنوات النشطة',
    description: 'التحديثات الأخيرة على السجلات الطبية والقنوات قيد المتابعة',
    visible: true,
    order: 4,
  },
  {
    id: 'security_status',
    title: 'مؤشرات الأمان والتشفير الطبي',
    description: 'حالة التشفير AES-256، جدار الحماية، وفحص الأمان والامتثال',
    visible: true,
    order: 5,
  },
];

interface DashboardCustomizerModalProps {
  isOpen: boolean;
  onClose: () => void;
  widgets: DashboardWidgetConfig[];
  onSave: (newWidgets: DashboardWidgetConfig[]) => void;
  onReset: () => void;
}

export default function DashboardCustomizerModal({
  isOpen,
  onClose,
  widgets,
  onSave,
  onReset,
}: DashboardCustomizerModalProps) {
  const [localWidgets, setLocalWidgets] = useState<DashboardWidgetConfig[]>([]);

  useEffect(() => {
    if (isOpen) {
      setLocalWidgets([...widgets].sort((a, b) => a.order - b.order));
    }
  }, [isOpen, widgets]);

  const toggleVisibility = (id: string) => {
    setLocalWidgets(prev =>
      prev.map(w => (w.id === id ? { ...w, visible: !w.visible } : w))
    );
  };

  const moveWidget = (index: number, direction: 'up' | 'down') => {
    const targetIndex = direction === 'up' ? index - 1 : index + 1;
    if (targetIndex < 0 || targetIndex >= localWidgets.length) return;

    const updated = [...localWidgets];
    const [moved] = updated.splice(index, 1);
    updated.splice(targetIndex, 0, moved);

    // Re-assign order indices
    const reordered = updated.map((w, idx) => ({ ...w, order: idx }));
    setLocalWidgets(reordered);
  };

  const handleSave = () => {
    onSave(localWidgets);
    toast.success('تم حفظ ترتيب وتخصيص لوحة التحكم بنجاح');
    onClose();
  };

  const handleReset = () => {
    onReset();
    setLocalWidgets([...DEFAULT_WIDGETS]);
    toast.success('تمت استعادة الترتيب الافتراضي للوحة التحكم');
    onClose();
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="تخصيص لوحة التحكم السريرية"
      maxWidth="max-w-xl"
    >
      <div className="space-y-5">
        <div className="flex items-center justify-between pb-3 border-b border-gray-100 dark:border-gray-800">
          <p className="text-xs text-gray-500 dark:text-gray-400">
            يمكنك إظهار أو إخفاء أي قسم وإعادة ترتيب الأقسام لرفع كفاءة وسرعة وصولك للمعلومات السريرية المهمة.
          </p>
          <button
            onClick={handleReset}
            className="flex items-center gap-1.5 text-xs text-primary-600 hover:text-primary-700 dark:text-primary-400 font-medium px-2.5 py-1.5 rounded-lg hover:bg-primary-50 dark:hover:bg-primary-950/30 transition-colors flex-shrink-0"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            استعادة الافتراضي
          </button>
        </div>

        {/* Widgets List */}
        <div className="space-y-2.5 max-h-[55vh] overflow-y-auto pr-1">
          {localWidgets.map((w, index) => (
            <motion.div
              key={w.id}
              layout
              className={`flex items-center justify-between p-3.5 rounded-2xl border transition-all ${
                w.visible
                  ? 'bg-white dark:bg-gray-800/80 border-gray-200 dark:border-gray-700 shadow-xs'
                  : 'bg-gray-50 dark:bg-gray-900/40 border-dashed border-gray-300 dark:border-gray-800 opacity-60'
              }`}
            >
              <div className="flex items-center gap-3 min-w-0">
                <span className="w-7 h-7 rounded-xl bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 text-xs font-bold flex items-center justify-center flex-shrink-0">
                  {index + 1}
                </span>
                <div className="min-w-0">
                  <h4 className="text-sm font-bold text-gray-900 dark:text-white truncate">
                    {w.title}
                  </h4>
                  <p className="text-xs text-gray-500 dark:text-gray-400 truncate">
                    {w.description}
                  </p>
                </div>
              </div>

              {/* Controls */}
              <div className="flex items-center gap-1.5 flex-shrink-0">
                {/* Move Up */}
                <button
                  onClick={() => moveWidget(index, 'up')}
                  disabled={index === 0}
                  className="p-1.5 text-gray-500 hover:text-gray-900 dark:text-gray-400 dark:hover:text-white disabled:opacity-30 disabled:hover:text-gray-500 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
                  title="تحريك لأعلى"
                >
                  <ArrowUp className="w-4 h-4" />
                </button>

                {/* Move Down */}
                <button
                  onClick={() => moveWidget(index, 'down')}
                  disabled={index === localWidgets.length - 1}
                  className="p-1.5 text-gray-500 hover:text-gray-900 dark:text-gray-400 dark:hover:text-white disabled:opacity-30 disabled:hover:text-gray-500 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
                  title="تحريك لأسفل"
                >
                  <ArrowDown className="w-4 h-4" />
                </button>

                <div className="w-px h-5 bg-gray-200 dark:bg-gray-700 mx-1" />

                {/* Visibility Toggle */}
                <button
                  onClick={() => toggleVisibility(w.id)}
                  className={`p-1.5 rounded-lg transition-colors ${
                    w.visible
                      ? 'text-primary-600 dark:text-primary-400 bg-primary-50 dark:bg-primary-950/40 hover:bg-primary-100'
                      : 'text-gray-400 bg-gray-100 dark:bg-gray-800 hover:bg-gray-200'
                  }`}
                  title={w.visible ? 'إخفاء العنصر' : 'إظهار العنصر'}
                >
                  {w.visible ? <Eye className="w-4 h-4" /> : <EyeOff className="w-4 h-4" />}
                </button>
              </div>
            </motion.div>
          ))}
        </div>

        {/* Footer Actions */}
        <div className="flex items-center justify-end gap-3 pt-3 border-t border-gray-100 dark:border-gray-800">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-xl transition-colors"
          >
            إلغاء
          </button>
          <button
            onClick={handleSave}
            className="btn-primary flex items-center gap-2 text-sm"
          >
            <Check className="w-4 h-4" />
            حفظ التغييرات
          </button>
        </div>
      </div>
    </Modal>
  );
}
