import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Microscope, TestTube, TestTubes, AlertTriangle, FileText, CheckCircle,
  XCircle, Clock, PlayCircle, Plus, Search, AlertCircle, X, ChevronDown,
} from 'lucide-react';
import toast from 'react-hot-toast';
import PageHeader from '../components/common/PageHeader';
import Card from '../components/common/Card';
import { labAPI } from '../api/extendedApis';

// ─── Types ───────────────────────────────────────────────────────────────
interface LabTest {
  id: string;
  name: string;
  code: string;
  category: string;
  description: string;
  unit: string;
  normal_range_min: number | null;
  normal_range_max: number | null;
  normal_range_text: string;
  price: number;
  is_active: boolean;
}

interface LabOrder {
  id: string;
  patient: string;
  patient_name: string;
  doctor: string;
  doctor_name: string;
  test_name: string;
  test_category: string;
  test_unit: string;
  test_normal_range_min: number | null;
  test_normal_range_max: number | null;
  status: string;
  priority: string;
  clinical_notes: string;
  created_at: string;
  result?: LabResult;
}

interface LabResult {
  id: string;
  numeric_value: number | null;
  text_value: string;
  is_abnormal: boolean;
  is_critical: boolean;
  notes: string;
  performed_by_name: string;
  validated_by_name: string | null;
  created_at: string;
}

interface LabStats {
  total_tests: number;
  pending_orders: number;
  in_progress: number;
  completed_today: number;
  critical_results: number;
  abnormal_results: number;
}

// ─── Helpers ─────────────────────────────────────────────────────────────
const extractArray = (data: any): any[] =>
  Array.isArray(data) ? data : Array.isArray(data?.results) ? data.results : [];

const statusConfig: Record<string, { label: string; cls: string; icon: any }> = {
  ORDERED: { label: 'مطلوب', cls: 'bg-slate-100 text-slate-700 dark:bg-slate-700 dark:text-slate-300', icon: FileText },
  SAMPLE_COLLECTED: { label: 'تم جمع العينة', cls: 'bg-amber-100 text-amber-700 dark:bg-amber-500/20 dark:text-amber-300', icon: TestTube },
  IN_PROGRESS: { label: 'قيد التنفيذ', cls: 'bg-blue-100 text-blue-700 dark:bg-blue-500/20 dark:text-blue-300', icon: PlayCircle },
  COMPLETED: { label: 'مكتمل (بانتظار المصادقة)', cls: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-500/20 dark:text-emerald-300', icon: CheckCircle },
  VALIDATED: { label: 'مصادق عليه', cls: 'bg-indigo-100 text-indigo-700 dark:bg-indigo-500/20 dark:text-indigo-300', icon: CheckCircle },
  CANCELLED: { label: 'ملغى', cls: 'bg-rose-100 text-rose-700 dark:bg-rose-500/20 dark:text-rose-300', icon: XCircle },
};

const priorityConfig: Record<string, { label: string; cls: string }> = {
  ROUTINE: { label: 'عادي', cls: 'text-slate-500' },
  URGENT: { label: 'مستعجل', cls: 'text-orange-500 font-bold' },
  STAT: { label: 'فوري (STAT)', cls: 'text-rose-600 font-bold' },
};

// ─── Main Component ──────────────────────────────────────────────────────
export default function LabDashboard() {
  const qc = useQueryClient();
  const [activeTab, setActiveTab] = useState<'orders' | 'catalog' | 'alerts'>('orders');
  const [statusFilter, setStatusFilter] = useState('');
  const [showResultModal, setShowResultModal] = useState<LabOrder | null>(null);

  // Queries
  const { data: statsData } = useQuery({
    queryKey: ['lab-stats'],
    queryFn: () => labAPI.stats().then(r => r.data),
  });
  const stats: LabStats = statsData || {} as LabStats;

  const { data: ordersRaw, isLoading } = useQuery({
    queryKey: ['lab-orders', statusFilter],
    queryFn: () => labAPI.orders({ status: statusFilter || undefined }).then(r => r.data),
  });
  const orders: LabOrder[] = extractArray(ordersRaw);

  const { data: catalogRaw } = useQuery({
    queryKey: ['lab-catalog'],
    queryFn: () => labAPI.tests().then(r => r.data),
    enabled: activeTab === 'catalog',
  });
  const catalog: LabTest[] = extractArray(catalogRaw);

  const { data: criticalRaw } = useQuery({
    queryKey: ['lab-critical'],
    queryFn: () => labAPI.criticalResults().then(r => r.data),
    enabled: activeTab === 'alerts',
  });
  const criticalResults: LabResult[] = extractArray(criticalRaw);

  // Mutations
  const actionMutation = useMutation({
    mutationFn: ({ id, action }: { id: string; action: 'collect_sample' | 'start_processing' | 'cancel' | 'validate' }) => {
      if (action === 'collect_sample') return labAPI.collectSample(id);
      if (action === 'start_processing') return labAPI.startProcessing(id);
      if (action === 'validate') return labAPI.validateResult(id);
      return labAPI.cancelOrder(id);
    },
    onSuccess: () => {
      toast.success('تم التحديث بنجاح');
      qc.invalidateQueries({ queryKey: ['lab-orders'] });
      qc.invalidateQueries({ queryKey: ['lab-stats'] });
    },
    onError: (err: any) => toast.error(err?.response?.data?.detail || 'فشل التحديث'),
  });

  const tabs = [
    { key: 'orders' as const, label: 'طلبات التحاليل', icon: TestTubes },
    { key: 'catalog' as const, label: 'فهرس التحاليل', icon: Microscope },
    { key: 'alerts' as const, label: 'التنبيهات الحرجة', icon: AlertTriangle, count: stats.critical_results || 0 },
  ];

  return (
    <div className="space-y-6 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 animate-in fade-in zoom-in duration-500">
      <PageHeader
        title="إدارة المختبرات والتحاليل"
        description="إدارة طلبات التحاليل، إدخال النتائج، والتنبيهات للقيم الحرجة"
        icon={<Microscope className="w-8 h-8 text-blue-500" />}
      />

      {/* ─── Stats Cards ───────────────────────────────────────────── */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { label: 'طلبات بانتظار العينة', value: stats.pending_orders ?? 0, icon: TestTube, color: 'amber' },
          { label: 'تحاليل قيد التنفيذ', value: stats.in_progress ?? 0, icon: PlayCircle, color: 'blue' },
          { label: 'مكتملة اليوم', value: stats.completed_today ?? 0, icon: CheckCircle, color: 'emerald' },
          { label: 'نتائج حرجة', value: stats.critical_results ?? 0, icon: AlertCircle, color: 'rose' },
        ].map((s, i) => (
          <div key={i} className={`relative overflow-hidden rounded-2xl border border-slate-200/60 dark:border-slate-700/60 bg-white dark:bg-slate-900 p-5 shadow-sm`}>
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-slate-500 dark:text-slate-400">{s.label}</p>
                <p className="text-2xl font-bold text-slate-900 dark:text-white mt-1">{s.value}</p>
              </div>
              <div className={`p-3 rounded-xl bg-${s.color}-100 dark:bg-${s.color}-500/20`}>
                <s.icon className={`w-6 h-6 text-${s.color}-600 dark:text-${s.color}-400`} />
              </div>
            </div>
            <div className={`absolute bottom-0 left-0 right-0 h-1 bg-gradient-to-r from-${s.color}-400 to-${s.color}-600`} />
          </div>
        ))}
      </div>

      {/* ─── Tabs ───────────────────────────────────────────────── */}
      <div className="flex space-x-4 space-x-reverse border-b border-slate-200/50 dark:border-slate-700/50">
        {tabs.map(t => (
          <button
            key={t.key}
            onClick={() => setActiveTab(t.key)}
            className={`flex items-center gap-2 pb-3 px-4 text-sm font-medium transition-colors border-b-2 ${
              activeTab === t.key
                ? 'border-blue-500 text-blue-600 dark:text-blue-400'
                : 'border-transparent text-slate-500 hover:text-slate-700 dark:text-slate-400'
            }`}
          >
            <t.icon className="w-4 h-4" />
            {t.label}
            {t.count !== undefined && t.count > 0 && (
              <span className="px-2 py-0.5 text-xs rounded-full bg-rose-100 text-rose-700 dark:bg-rose-500/20 dark:text-rose-300 font-bold">
                {t.count}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* ─── TAB: Orders ───────────────────────────────────────── */}
      {activeTab === 'orders' && (
        <Card className="p-6">
          <div className="flex justify-between items-center mb-6">
            <select
              value={statusFilter}
              onChange={e => setStatusFilter(e.target.value)}
              className="px-4 py-2.5 border border-slate-200 dark:border-slate-700 rounded-xl bg-slate-50/50 dark:bg-slate-800/50 text-slate-700 dark:text-slate-300 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20"
            >
              <option value="">كل الطلبات</option>
              <option value="ORDERED">مطلوب (بانتظار سحب العينة)</option>
              <option value="SAMPLE_COLLECTED">تم سحب العينة</option>
              <option value="IN_PROGRESS">قيد التنفيذ</option>
              <option value="COMPLETED">مكتمل (للمصادقة)</option>
              <option value="VALIDATED">مصادق عليه</option>
            </select>
          </div>

          {isLoading ? (
            <div className="space-y-3">{[1,2,3].map(i => <div key={i} className="h-24 bg-slate-100 dark:bg-slate-800 rounded-xl animate-pulse" />)}</div>
          ) : orders.length === 0 ? (
            <div className="text-center py-16">
              <TestTubes className="w-16 h-16 text-slate-300 dark:text-slate-600 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-slate-900 dark:text-white mb-1">لا توجد طلبات</h3>
              <p className="text-slate-500 dark:text-slate-400">لا يوجد أي طلبات تحاليل بالفلتر المحدد</p>
            </div>
          ) : (
            <div className="space-y-3">
              {orders.map(order => {
                const sc = statusConfig[order.status] || statusConfig.ORDERED;
                const StatusIcon = sc.icon;
                const pc = priorityConfig[order.priority] || priorityConfig.ROUTINE;

                return (
                  <div key={order.id} className="border border-slate-200 dark:border-slate-700 rounded-xl p-4 bg-white dark:bg-slate-900">
                    <div className="flex flex-col md:flex-row justify-between items-start gap-4">
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-2">
                          <span className={`px-2.5 py-1 text-xs rounded-full font-bold ${sc.cls}`}>
                            {sc.label}
                          </span>
                          <span className={`text-xs ${pc.cls}`}>{pc.label}</span>
                          <span className="text-xs text-slate-400">{new Date(order.created_at).toLocaleDateString('ar-YE')}</span>
                        </div>
                        <h4 className="text-lg font-bold text-slate-900 dark:text-white mb-1">
                          {order.test_name} <span className="text-sm font-normal text-slate-500">({order.test_category})</span>
                        </h4>
                        <div className="text-sm text-slate-600 dark:text-slate-400 space-y-1">
                          <p>المريض: <span className="font-medium text-slate-900 dark:text-white">{order.patient_name}</span></p>
                          <p>الطبيب المعالج: {order.doctor_name}</p>
                          {order.clinical_notes && <p className="text-slate-500 italic mt-2">"{order.clinical_notes}"</p>}
                        </div>

                        {/* Result Section if Completed/Validated */}
                        {order.result && (
                          <div className={`mt-4 p-3 rounded-lg border ${order.result.is_critical ? 'bg-rose-50 border-rose-200 dark:bg-rose-500/10 dark:border-rose-500/20' : order.result.is_abnormal ? 'bg-amber-50 border-amber-200 dark:bg-amber-500/10 dark:border-amber-500/20' : 'bg-slate-50 border-slate-200 dark:bg-slate-800 dark:border-slate-700'}`}>
                            <div className="flex items-center justify-between">
                              <div>
                                <span className="text-xs text-slate-500 block mb-1">النتيجة:</span>
                                <span className={`text-xl font-bold ${order.result.is_critical ? 'text-rose-700 dark:text-rose-400' : order.result.is_abnormal ? 'text-amber-700 dark:text-amber-400' : 'text-slate-900 dark:text-white'}`}>
                                  {order.result.numeric_value !== null ? order.result.numeric_value : order.result.text_value}
                                </span>
                                {order.test_unit && <span className="text-sm text-slate-500 mr-2">{order.test_unit}</span>}
                              </div>
                              <div className="text-left">
                                <span className="text-xs text-slate-500 block mb-1">المعدل الطبيعي:</span>
                                <span className="text-sm text-slate-700 dark:text-slate-300">
                                  {order.test_normal_range_min !== null ? `${order.test_normal_range_min} - ${order.test_normal_range_max}` : order.test_normal_range_text}
                                </span>
                              </div>
                            </div>
                            {(order.result.is_abnormal || order.result.is_critical) && (
                              <div className={`mt-2 text-sm font-bold ${order.result.is_critical ? 'text-rose-600' : 'text-amber-600'}`}>
                                <AlertTriangle className="w-4 h-4 inline ml-1" />
                                {order.result.is_critical ? 'نتيجة حرجة!' : 'نتيجة غير طبيعية'}
                              </div>
                            )}
                          </div>
                        )}
                      </div>

                      {/* Actions */}
                      <div className="flex flex-wrap gap-2 shrink-0">
                        {order.status === 'ORDERED' && (
                          <button
                            onClick={() => actionMutation.mutate({ id: order.id, action: 'collect_sample' })}
                            disabled={actionMutation.isPending}
                            className="px-4 py-2 bg-amber-500 hover:bg-amber-600 text-white rounded-xl text-sm font-medium transition-colors"
                          >
                            <TestTube className="w-4 h-4 inline ml-1" /> سحب العينة
                          </button>
                        )}
                        {order.status === 'SAMPLE_COLLECTED' && (
                          <button
                            onClick={() => actionMutation.mutate({ id: order.id, action: 'start_processing' })}
                            disabled={actionMutation.isPending}
                            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-xl text-sm font-medium transition-colors"
                          >
                            <PlayCircle className="w-4 h-4 inline ml-1" /> بدء التنفيذ
                          </button>
                        )}
                        {order.status === 'IN_PROGRESS' && (
                          <button
                            onClick={() => setShowResultModal(order)}
                            className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl text-sm font-medium transition-colors"
                          >
                            <Plus className="w-4 h-4 inline ml-1" /> إدخال النتيجة
                          </button>
                        )}
                        {order.status === 'COMPLETED' && (
                          <button
                            onClick={() => actionMutation.mutate({ id: order.result!.id, action: 'validate' })}
                            disabled={actionMutation.isPending}
                            className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl text-sm font-medium transition-colors"
                          >
                            <CheckCircle className="w-4 h-4 inline ml-1" /> مصادقة (طبيب)
                          </button>
                        )}
                        {['ORDERED', 'SAMPLE_COLLECTED', 'IN_PROGRESS'].includes(order.status) && (
                          <button
                            onClick={() => { if (confirm('إلغاء الطلب؟')) actionMutation.mutate({ id: order.id, action: 'cancel' }); }}
                            disabled={actionMutation.isPending}
                            className="p-2 bg-rose-50 hover:bg-rose-100 text-rose-600 dark:bg-rose-500/10 dark:hover:bg-rose-500/20 rounded-xl transition-colors"
                            title="إلغاء"
                          >
                            <XCircle className="w-5 h-5" />
                          </button>
                        )}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </Card>
      )}

      {/* ─── TAB: Catalog ────────────────────────────────────────── */}
      {activeTab === 'catalog' && (
        <Card className="p-6">
          <div className="flex justify-between items-center mb-6">
            <h3 className="text-lg font-bold text-slate-900 dark:text-white">فهرس التحاليل المختبرية المتاحة</h3>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-slate-200 dark:border-slate-700">
                  <th className="py-3 px-4 text-right text-xs font-semibold text-slate-500 uppercase tracking-wider">التصنيف</th>
                  <th className="py-3 px-4 text-right text-xs font-semibold text-slate-500 uppercase tracking-wider">اسم التحليل</th>
                  <th className="py-3 px-4 text-right text-xs font-semibold text-slate-500 uppercase tracking-wider">رمز LOINC</th>
                  <th className="py-3 px-4 text-right text-xs font-semibold text-slate-500 uppercase tracking-wider">المعدل الطبيعي</th>
                  <th className="py-3 px-4 text-right text-xs font-semibold text-slate-500 uppercase tracking-wider">السعر</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                {catalog.map(test => (
                  <tr key={test.id} className="hover:bg-slate-50/50 dark:hover:bg-slate-800/50 transition-colors">
                    <td className="py-3 px-4 text-sm font-medium text-slate-900 dark:text-white">{test.category}</td>
                    <td className="py-3 px-4 text-sm font-medium text-blue-600 dark:text-blue-400">{test.name}</td>
                    <td className="py-3 px-4 text-sm text-slate-500">{test.code || '—'}</td>
                    <td className="py-3 px-4 text-sm text-slate-600 dark:text-slate-400">
                      {test.normal_range_min !== null
                        ? `${test.normal_range_min} - ${test.normal_range_max} ${test.unit}`
                        : test.normal_range_text || '—'}
                    </td>
                    <td className="py-3 px-4 text-sm text-slate-700 dark:text-slate-300">{test.price} ر.ي</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {/* ─── TAB: Critical Alerts ────────────────────────────────── */}
      {activeTab === 'alerts' && (
        <div className="space-y-4">
          {criticalResults.length === 0 ? (
            <Card className="p-12 text-center">
              <CheckCircle className="w-16 h-16 text-emerald-400 mx-auto mb-4" />
              <h3 className="text-lg font-semibold text-slate-900 dark:text-white">لا توجد نتائج حرجة</h3>
              <p className="text-slate-500 mt-1">جميع النتائج الأخيرة ضمن الحدود الطبيعية أو مقبولة</p>
            </Card>
          ) : (
            criticalResults.map(res => (
              <Card key={res.id} className="p-5 border-r-4 border-r-rose-500">
                <div className="flex items-center gap-3">
                  <div className="p-3 bg-rose-100 dark:bg-rose-500/20 rounded-full">
                    <AlertTriangle className="w-6 h-6 text-rose-600 dark:text-rose-400" />
                  </div>
                  <div className="flex-1">
                    <h4 className="text-lg font-bold text-slate-900 dark:text-white">
                      نتيجة حرجة: {res.numeric_value !== null ? res.numeric_value : res.text_value}
                    </h4>
                    <p className="text-sm text-slate-500 mt-1">تم الإدخال بواسطة: {res.performed_by_name} — {new Date(res.created_at).toLocaleString('ar-YE')}</p>
                    {res.notes && <p className="text-sm text-rose-700 bg-rose-50 p-2 rounded mt-2 dark:bg-rose-500/10 dark:text-rose-300">ملاحظة: {res.notes}</p>}
                  </div>
                </div>
              </Card>
            ))
          )}
        </div>
      )}

      {/* ─── Result Entry Modal ──────────────────────────────────── */}
      {showResultModal && (
        <ResultModal
          order={showResultModal}
          onClose={() => setShowResultModal(null)}
          onSaved={() => {
            setShowResultModal(null);
            qc.invalidateQueries({ queryKey: ['lab-orders'] });
            qc.invalidateQueries({ queryKey: ['lab-stats'] });
            qc.invalidateQueries({ queryKey: ['lab-critical'] });
          }}
        />
      )}
    </div>
  );
}

// ─── Result Entry Modal Component ──────────────────────────────────────────
function ResultModal({ order, onClose, onSaved }: { order: LabOrder; onClose: () => void; onSaved: () => void }) {
  const [valNum, setValNum] = useState<string>('');
  const [valText, setValText] = useState<string>('');
  const [notes, setNotes] = useState('');
  const [saving, setSaving] = useState(false);

  const isNumeric = order.test_normal_range_min !== null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (isNumeric && !valNum) { toast.error('الرجاء إدخال القيمة الرقمية'); return; }
    if (!isNumeric && !valText) { toast.error('الرجاء إدخال القيمة النصية'); return; }
    
    setSaving(true);
    try {
      await labAPI.createResult({
        order: order.id,
        numeric_value: isNumeric ? Number(valNum) : null,
        text_value: isNumeric ? '' : valText,
        notes,
      });
      toast.success('تم إدخال النتيجة بنجاح');
      onSaved();
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || 'فشل الحفظ');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4" onClick={onClose}>
      <div className="bg-white dark:bg-slate-900 rounded-2xl shadow-xl max-w-md w-full p-6" onClick={e => e.stopPropagation()}>
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-xl font-bold text-slate-900 dark:text-white">إدخال نتيجة مختبرية</h2>
          <button onClick={onClose} className="p-2 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-xl transition-colors">
            <X className="w-5 h-5 text-slate-500" />
          </button>
        </div>
        
        <div className="mb-6 p-4 bg-blue-50 dark:bg-blue-500/10 rounded-xl">
          <h4 className="font-bold text-blue-900 dark:text-blue-300 mb-1">{order.test_name}</h4>
          <div className="text-sm text-blue-700 dark:text-blue-400">
            <span className="block mb-1">المريض: {order.patient_name}</span>
            <span>المعدل الطبيعي: {isNumeric ? `${order.test_normal_range_min} - ${order.test_normal_range_max} ${order.test_unit}` : 'نصي'}</span>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          {isNumeric ? (
            <div>
              <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">القيمة الرقمية</label>
              <div className="relative">
                <input
                  type="number"
                  step="0.001"
                  value={valNum}
                  onChange={e => setValNum(e.target.value)}
                  className="w-full px-4 py-2.5 border border-slate-200 dark:border-slate-700 rounded-xl bg-slate-50/50 dark:bg-slate-800/50 text-slate-900 dark:text-white focus:ring-2 focus:ring-blue-500/20"
                />
                <span className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 text-sm">{order.test_unit}</span>
              </div>
            </div>
          ) : (
            <div>
              <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">القيمة النصية</label>
              <input
                type="text"
                value={valText}
                onChange={e => setValText(e.target.value)}
                className="w-full px-4 py-2.5 border border-slate-200 dark:border-slate-700 rounded-xl bg-slate-50/50 dark:bg-slate-800/50 text-slate-900 dark:text-white focus:ring-2 focus:ring-blue-500/20"
              />
            </div>
          )}
          <div>
            <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">ملاحظات الفني (اختياري)</label>
            <textarea
              value={notes}
              onChange={e => setNotes(e.target.value)}
              rows={2}
              className="w-full px-4 py-2.5 border border-slate-200 dark:border-slate-700 rounded-xl bg-slate-50/50 dark:bg-slate-800/50 text-slate-900 dark:text-white focus:ring-2 focus:ring-blue-500/20 resize-none"
            />
          </div>
          <button type="submit" disabled={saving} className="w-full py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-xl font-medium transition-colors disabled:opacity-50">
            {saving ? 'جارٍ الحفظ...' : 'اعتماد النتيجة'}
          </button>
        </form>
      </div>
    </div>
  );
}
