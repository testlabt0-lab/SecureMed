import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Pill, AlertTriangle, FileText, Plus, Search, Package, TrendingDown,
  Clock, DollarSign, CheckCircle, XCircle, ArrowUpDown, ChevronDown,
  ShieldCheck, Trash2, Edit, BarChart3, AlertCircle, RefreshCw, X,
} from 'lucide-react';
import toast from 'react-hot-toast';
import PageHeader from '../components/common/PageHeader';
import Card from '../components/common/Card';
import { pharmacyAPI } from '../api/extendedApis';

// ─── Types ───────────────────────────────────────────────────────────────
interface Medication {
  id: string;
  name: string;
  scientific_name: string;
  barcode: string;
  stock_quantity: number;
  reorder_level: number;
  unit_price: number;
  expiry_date: string | null;
  description: string;
  instructions: string;
  is_active: boolean;
  is_low_stock: boolean;
  is_expired: boolean;
}

interface Prescription {
  id: string;
  patient: string;
  patient_name: string;
  doctor: string;
  doctor_name: string;
  diagnosis_code: string;
  is_signed: boolean;
  status: string;
  items: PrescriptionItem[];
  created_at: string;
}

interface PrescriptionItem {
  id: string;
  medication: string;
  medication_name: string;
  medication_stock: number;
  dosage: string;
  frequency: string;
  duration_days: number;
  quantity: number;
}

interface PharmacyStats {
  total_medications: number;
  low_stock_count: number;
  expired_count: number;
  expiring_soon: number;
  total_stock_value: number;
  total_prescriptions: number;
  pending_prescriptions: number;
  dispensed_today: number;
}

// ─── Helper ──────────────────────────────────────────────────────────────
const extractArray = (data: any): any[] =>
  Array.isArray(data) ? data : Array.isArray(data?.results) ? data.results : [];

const statusBadge: Record<string, { label: string; cls: string }> = {
  ISSUED: { label: 'بانتظار الصرف', cls: 'bg-amber-100 text-amber-700 dark:bg-amber-500/20 dark:text-amber-300' },
  DISPENSED: { label: 'تم الصرف', cls: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-500/20 dark:text-emerald-300' },
  CANCELLED: { label: 'ملغاة', cls: 'bg-rose-100 text-rose-700 dark:bg-rose-500/20 dark:text-rose-300' },
};

// ─── Main Component ──────────────────────────────────────────────────────
export default function PharmacyManagement() {
  const qc = useQueryClient();
  const [activeTab, setActiveTab] = useState<'inventory' | 'prescriptions' | 'alerts'>('inventory');
  const [search, setSearch] = useState('');
  const [stockFilter, setStockFilter] = useState('');
  const [showAddModal, setShowAddModal] = useState(false);
  const [showStockModal, setShowStockModal] = useState<Medication | null>(null);
  const [editMed, setEditMed] = useState<Medication | null>(null);

  // Queries
  const { data: statsData } = useQuery({
    queryKey: ['pharmacy-stats'],
    queryFn: () => pharmacyAPI.stats().then(r => r.data),
  });
  const stats: PharmacyStats = statsData || {} as PharmacyStats;

  const { data: medsRaw, isLoading: medsLoading } = useQuery({
    queryKey: ['pharmacy-meds', search, stockFilter],
    queryFn: () => pharmacyAPI.medications({ search, stock_status: stockFilter || undefined }).then(r => r.data),
  });
  const medications: Medication[] = extractArray(medsRaw);

  const { data: rxRaw } = useQuery({
    queryKey: ['pharmacy-rx'],
    queryFn: () => pharmacyAPI.prescriptions().then(r => r.data),
  });
  const prescriptions: Prescription[] = extractArray(rxRaw);

  const { data: lowStockRaw } = useQuery({
    queryKey: ['pharmacy-low-stock'],
    queryFn: () => pharmacyAPI.lowStock().then(r => r.data),
  });
  const lowStockMeds: Medication[] = extractArray(lowStockRaw);

  const { data: expiredRaw } = useQuery({
    queryKey: ['pharmacy-expired'],
    queryFn: () => pharmacyAPI.expired().then(r => r.data),
  });
  const expiredMeds: Medication[] = extractArray(expiredRaw);

  const { data: expiringSoonRaw } = useQuery({
    queryKey: ['pharmacy-expiring-soon'],
    queryFn: () => pharmacyAPI.expiringSoon().then(r => r.data),
  });
  const expiringSoonMeds: Medication[] = extractArray(expiringSoonRaw);

  // Mutations
  const dispenseMutation = useMutation({
    mutationFn: (id: string) => pharmacyAPI.dispensePrescription(id),
    onSuccess: () => {
      toast.success('تم صرف الوصفة بنجاح');
      qc.invalidateQueries({ queryKey: ['pharmacy-rx'] });
      qc.invalidateQueries({ queryKey: ['pharmacy-meds'] });
      qc.invalidateQueries({ queryKey: ['pharmacy-stats'] });
    },
    onError: (err: any) => toast.error(err?.response?.data?.detail || 'فشل صرف الوصفة'),
  });

  const cancelRxMutation = useMutation({
    mutationFn: (id: string) => pharmacyAPI.cancelPrescription(id),
    onSuccess: () => {
      toast.success('تم إلغاء الوصفة');
      qc.invalidateQueries({ queryKey: ['pharmacy-rx'] });
      qc.invalidateQueries({ queryKey: ['pharmacy-stats'] });
    },
    onError: (err: any) => toast.error(err?.response?.data?.detail || 'فشل الإلغاء'),
  });

  const deleteMedMutation = useMutation({
    mutationFn: (id: string) => pharmacyAPI.deleteMedication(id),
    onSuccess: () => {
      toast.success('تم حذف الدواء');
      qc.invalidateQueries({ queryKey: ['pharmacy-meds'] });
      qc.invalidateQueries({ queryKey: ['pharmacy-stats'] });
    },
    onError: () => toast.error('فشل حذف الدواء'),
  });

  const tabs = [
    { key: 'inventory' as const, label: 'المخزون الدوائي', icon: Package },
    { key: 'prescriptions' as const, label: 'الوصفات الإلكترونية', icon: FileText },
    { key: 'alerts' as const, label: 'التنبيهات', icon: AlertTriangle, count: (stats.low_stock_count || 0) + (stats.expired_count || 0) },
  ];

  return (
    <div className="space-y-6 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 animate-in fade-in zoom-in duration-500">
      <PageHeader
        title="الصيدلية الإلكترونية"
        description="إدارة المخزون الدوائي، الوصفات الإلكترونية، وفحص التداخلات الدوائية"
        icon={<Pill className="w-8 h-8 text-indigo-500" />}
      />

      {/* ─── Stats Cards ───────────────────────────────────────────── */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { label: 'إجمالي الأدوية', value: stats.total_medications ?? 0, icon: Package, color: 'indigo' },
          { label: 'مخزون منخفض', value: stats.low_stock_count ?? 0, icon: TrendingDown, color: 'amber' },
          { label: 'أدوية منتهية', value: stats.expired_count ?? 0, icon: AlertCircle, color: 'rose' },
          { label: 'وصفات اليوم', value: stats.dispensed_today ?? 0, icon: CheckCircle, color: 'emerald' },
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
                ? 'border-indigo-500 text-indigo-600 dark:text-indigo-400'
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

      {/* ─── TAB: Inventory ──────────────────────────────────────── */}
      {activeTab === 'inventory' && (
        <Card className="p-6">
          <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 mb-6">
            <div className="relative flex-1 max-w-md">
              <div className="absolute inset-y-0 right-0 pr-3 flex items-center pointer-events-none">
                <Search className="h-5 w-5 text-slate-400" />
              </div>
              <input
                type="text"
                placeholder="ابحث باسم الدواء أو الباركود..."
                value={search}
                onChange={e => setSearch(e.target.value)}
                className="block w-full pr-10 pl-3 py-2.5 border border-slate-200 dark:border-slate-700 rounded-xl bg-slate-50/50 dark:bg-slate-800/50 text-slate-900 dark:text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-colors"
              />
            </div>
            <div className="flex items-center gap-3">
              <select
                value={stockFilter}
                onChange={e => setStockFilter(e.target.value)}
                className="px-3 py-2.5 border border-slate-200 dark:border-slate-700 rounded-xl bg-slate-50/50 dark:bg-slate-800/50 text-slate-700 dark:text-slate-300 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/20"
              >
                <option value="">الكل</option>
                <option value="low">مخزون منخفض</option>
                <option value="out">نفذ المخزون</option>
              </select>
              <button
                onClick={() => setShowAddModal(true)}
                className="inline-flex items-center justify-center px-4 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl shadow-sm hover:shadow transition-all text-sm font-medium"
              >
                <Plus className="w-4 h-4 ml-2" />
                إضافة دواء
              </button>
            </div>
          </div>

          {medsLoading ? (
            <div className="space-y-3">{[1,2,3].map(i => <div key={i} className="h-16 bg-slate-100 dark:bg-slate-800 rounded-xl animate-pulse" />)}</div>
          ) : medications.length === 0 ? (
            <div className="text-center py-16">
              <Pill className="w-16 h-16 text-slate-300 dark:text-slate-600 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-slate-900 dark:text-white mb-1">لا توجد أدوية</h3>
              <p className="text-slate-500 dark:text-slate-400">ابدأ بإضافة الأدوية للمخزون</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-slate-200 dark:border-slate-700">
                    {['اسم الدواء', 'الاسم العلمي', 'الكمية', 'حد الإعادة', 'السعر', 'تاريخ الانتهاء', 'الحالة', 'إجراءات'].map(h => (
                      <th key={h} className="py-3 px-4 text-right text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                  {medications.map(med => (
                    <tr key={med.id} className="hover:bg-slate-50/50 dark:hover:bg-slate-800/50 transition-colors">
                      <td className="py-3 px-4">
                        <div className="font-medium text-slate-900 dark:text-white">{med.name}</div>
                        {med.barcode && <div className="text-xs text-slate-400 mt-0.5">{med.barcode}</div>}
                      </td>
                      <td className="py-3 px-4 text-sm text-slate-600 dark:text-slate-400">{med.scientific_name || '—'}</td>
                      <td className="py-3 px-4">
                        <span className={`font-bold ${med.stock_quantity === 0 ? 'text-rose-600' : med.is_low_stock ? 'text-amber-600' : 'text-emerald-600'}`}>
                          {med.stock_quantity}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-sm text-slate-500">{med.reorder_level}</td>
                      <td className="py-3 px-4 text-sm text-slate-700 dark:text-slate-300">{Number(med.unit_price).toFixed(2)} ر.ي</td>
                      <td className="py-3 px-4 text-sm">
                        {med.expiry_date ? (
                          <span className={med.is_expired ? 'text-rose-600 font-bold' : 'text-slate-600 dark:text-slate-400'}>
                            {new Date(med.expiry_date).toLocaleDateString('ar-YE')}
                          </span>
                        ) : '—'}
                      </td>
                      <td className="py-3 px-4">
                        {med.is_expired ? (
                          <span className="px-2.5 py-1 text-xs rounded-full bg-rose-100 text-rose-700 dark:bg-rose-500/20 dark:text-rose-300 font-bold">منتهي الصلاحية</span>
                        ) : med.is_low_stock ? (
                          <span className="px-2.5 py-1 text-xs rounded-full bg-amber-100 text-amber-700 dark:bg-amber-500/20 dark:text-amber-300 font-bold">مخزون منخفض</span>
                        ) : med.stock_quantity === 0 ? (
                          <span className="px-2.5 py-1 text-xs rounded-full bg-rose-100 text-rose-700 dark:bg-rose-500/20 dark:text-rose-300 font-bold">نفذ</span>
                        ) : (
                          <span className="px-2.5 py-1 text-xs rounded-full bg-emerald-100 text-emerald-700 dark:bg-emerald-500/20 dark:text-emerald-300 font-bold">متوفر</span>
                        )}
                      </td>
                      <td className="py-3 px-4">
                        <div className="flex items-center gap-2">
                          <button
                            onClick={() => setShowStockModal(med)}
                            className="p-1.5 rounded-lg hover:bg-indigo-50 dark:hover:bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 transition-colors"
                            title="تعديل المخزون"
                          >
                            <ArrowUpDown className="w-4 h-4" />
                          </button>
                          <button
                            onClick={() => setEditMed(med)}
                            className="p-1.5 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-700 text-slate-600 dark:text-slate-400 transition-colors"
                            title="تعديل"
                          >
                            <Edit className="w-4 h-4" />
                          </button>
                          <button
                            onClick={() => { if (confirm('حذف هذا الدواء؟')) deleteMedMutation.mutate(med.id); }}
                            className="p-1.5 rounded-lg hover:bg-rose-50 dark:hover:bg-rose-500/10 text-rose-500 transition-colors"
                            title="حذف"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      )}

      {/* ─── TAB: Prescriptions ──────────────────────────────────── */}
      {activeTab === 'prescriptions' && (
        <div className="space-y-4">
          {prescriptions.length === 0 ? (
            <Card className="p-12 text-center">
              <FileText className="w-16 h-16 text-slate-300 dark:text-slate-600 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-slate-900 dark:text-white mb-1">لا توجد وصفات</h3>
              <p className="text-slate-500 dark:text-slate-400">لم يتم إنشاء أي وصفات إلكترونية بعد</p>
            </Card>
          ) : (
            prescriptions.map(rx => (
              <Card key={rx.id} className="p-5 hover:shadow-md transition-shadow">
                <div className="flex flex-col md:flex-row justify-between items-start gap-4">
                  <div className="flex-1">
                    <div className="flex flex-wrap items-center gap-2 mb-2">
                      <span className={`px-2.5 py-1 text-xs rounded-full font-bold ${statusBadge[rx.status]?.cls || 'bg-slate-100 text-slate-700'}`}>
                        {statusBadge[rx.status]?.label || rx.status}
                      </span>
                      {rx.is_signed && (
                        <span className="px-2 py-0.5 text-xs bg-emerald-100 text-emerald-700 dark:bg-emerald-500/20 dark:text-emerald-300 rounded-full flex items-center gap-1">
                          <ShieldCheck className="w-3 h-3" /> موقعة رقمياً
                        </span>
                      )}
                      <span className="text-xs text-slate-400">{new Date(rx.created_at).toLocaleDateString('ar-YE')}</span>
                    </div>
                    <h3 className="text-lg font-bold text-slate-900 dark:text-white">المريض: {rx.patient_name}</h3>
                    <p className="text-sm text-slate-500 dark:text-slate-400 mt-0.5">الطبيب: {rx.doctor_name}</p>
                    {rx.diagnosis_code && (
                      <p className="text-sm text-slate-500 mt-1">التشخيص: <span className="font-mono text-indigo-600 dark:text-indigo-400">{rx.diagnosis_code}</span></p>
                    )}
                    {rx.items.length > 0 && (
                      <div className="mt-3 space-y-2">
                        {rx.items.map(item => (
                          <div key={item.id} className="flex justify-between items-center p-3 bg-slate-50 dark:bg-slate-800/50 rounded-lg">
                            <div>
                              <span className="font-medium text-slate-800 dark:text-slate-200">{item.medication_name}</span>
                              <span className="text-sm text-slate-500 mr-3">{item.dosage} — {item.frequency}</span>
                            </div>
                            <span className="text-sm text-slate-500">{item.quantity} وحدة / {item.duration_days} يوم</span>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                  {rx.status === 'ISSUED' && (
                    <div className="flex gap-2 shrink-0">
                      <button
                        onClick={() => dispenseMutation.mutate(rx.id)}
                        disabled={dispenseMutation.isPending}
                        className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl text-sm font-medium transition-colors disabled:opacity-50"
                      >
                        <CheckCircle className="w-4 h-4 inline ml-1" />
                        صرف الوصفة
                      </button>
                      <button
                        onClick={() => cancelRxMutation.mutate(rx.id)}
                        disabled={cancelRxMutation.isPending}
                        className="px-4 py-2 bg-rose-100 hover:bg-rose-200 text-rose-700 dark:bg-rose-500/20 dark:hover:bg-rose-500/30 dark:text-rose-300 rounded-xl text-sm font-medium transition-colors disabled:opacity-50"
                      >
                        <XCircle className="w-4 h-4 inline ml-1" />
                        إلغاء
                      </button>
                    </div>
                  )}
                </div>
              </Card>
            ))
          )}
        </div>
      )}

      {/* ─── TAB: Alerts ─────────────────────────────────────────── */}
      {activeTab === 'alerts' && (
        <div className="space-y-6">
          {/* Low Stock Alerts */}
          {lowStockMeds.length > 0 && (
            <Card className="p-6 border-r-4 border-r-amber-500">
              <div className="flex items-center gap-3 mb-4">
                <div className="p-2 bg-amber-100 dark:bg-amber-500/20 rounded-xl">
                  <TrendingDown className="w-5 h-5 text-amber-600 dark:text-amber-400" />
                </div>
                <h3 className="text-lg font-semibold text-slate-900 dark:text-white">
                  أدوية بمخزون منخفض ({lowStockMeds.length})
                </h3>
              </div>
              <div className="space-y-2">
                {lowStockMeds.map(m => (
                  <div key={m.id} className="flex justify-between items-center p-3 bg-amber-50/50 dark:bg-amber-500/5 rounded-lg">
                    <div>
                      <span className="font-medium text-slate-800 dark:text-slate-200">{m.name}</span>
                      <span className="text-sm text-slate-500 mr-2">({m.scientific_name})</span>
                    </div>
                    <div className="text-sm">
                      <span className="text-amber-600 font-bold">{m.stock_quantity}</span>
                      <span className="text-slate-400 mx-1">/</span>
                      <span className="text-slate-500">{m.reorder_level} حد الإعادة</span>
                    </div>
                  </div>
                ))}
              </div>
            </Card>
          )}

          {/* Expired Alerts */}
          {expiredMeds.length > 0 && (
            <Card className="p-6 border-r-4 border-r-rose-500">
              <div className="flex items-center gap-3 mb-4">
                <div className="p-2 bg-rose-100 dark:bg-rose-500/20 rounded-xl">
                  <AlertCircle className="w-5 h-5 text-rose-600 dark:text-rose-400" />
                </div>
                <h3 className="text-lg font-semibold text-slate-900 dark:text-white">
                  أدوية منتهية الصلاحية ({expiredMeds.length})
                </h3>
              </div>
              <div className="space-y-2">
                {expiredMeds.map(m => (
                  <div key={m.id} className="flex justify-between items-center p-3 bg-rose-50/50 dark:bg-rose-500/5 rounded-lg">
                    <span className="font-medium text-slate-800 dark:text-slate-200">{m.name}</span>
                    <span className="text-sm text-rose-600 font-bold">
                      انتهت {m.expiry_date ? new Date(m.expiry_date).toLocaleDateString('ar-YE') : ''}
                    </span>
                  </div>
                ))}
              </div>
            </Card>
          )}

          {/* Expiring Soon */}
          {expiringSoonMeds.length > 0 && (
            <Card className="p-6 border-r-4 border-r-orange-500">
              <div className="flex items-center gap-3 mb-4">
                <div className="p-2 bg-orange-100 dark:bg-orange-500/20 rounded-xl">
                  <Clock className="w-5 h-5 text-orange-600 dark:text-orange-400" />
                </div>
                <h3 className="text-lg font-semibold text-slate-900 dark:text-white">
                  أدوية قريبة الانتهاء خلال 30 يوم ({expiringSoonMeds.length})
                </h3>
              </div>
              <div className="space-y-2">
                {expiringSoonMeds.map(m => (
                  <div key={m.id} className="flex justify-between items-center p-3 bg-orange-50/50 dark:bg-orange-500/5 rounded-lg">
                    <span className="font-medium text-slate-800 dark:text-slate-200">{m.name}</span>
                    <span className="text-sm text-orange-600 font-bold">
                      {m.expiry_date ? new Date(m.expiry_date).toLocaleDateString('ar-YE') : ''}
                    </span>
                  </div>
                ))}
              </div>
            </Card>
          )}

          {lowStockMeds.length === 0 && expiredMeds.length === 0 && expiringSoonMeds.length === 0 && (
            <Card className="p-12 text-center">
              <CheckCircle className="w-16 h-16 text-emerald-400 mx-auto mb-4" />
              <h3 className="text-lg font-semibold text-slate-900 dark:text-white">لا توجد تنبيهات</h3>
              <p className="text-slate-500 dark:text-slate-400 mt-1">المخزون الدوائي في حالة جيدة</p>
            </Card>
          )}
        </div>
      )}

      {/* ─── Add/Edit Medication Modal ───────────────────────────── */}
      {(showAddModal || editMed) && (
        <MedicationModal
          medication={editMed}
          onClose={() => { setShowAddModal(false); setEditMed(null); }}
          onSaved={() => {
            setShowAddModal(false);
            setEditMed(null);
            qc.invalidateQueries({ queryKey: ['pharmacy-meds'] });
            qc.invalidateQueries({ queryKey: ['pharmacy-stats'] });
          }}
        />
      )}

      {/* ─── Stock Adjustment Modal ──────────────────────────────── */}
      {showStockModal && (
        <StockAdjustModal
          medication={showStockModal}
          onClose={() => setShowStockModal(null)}
          onSaved={() => {
            setShowStockModal(null);
            qc.invalidateQueries({ queryKey: ['pharmacy-meds'] });
            qc.invalidateQueries({ queryKey: ['pharmacy-stats'] });
            qc.invalidateQueries({ queryKey: ['pharmacy-low-stock'] });
          }}
        />
      )}
    </div>
  );
}

// ─── Medication Modal Component ──────────────────────────────────────────
function MedicationModal({ medication, onClose, onSaved }: { medication: Medication | null; onClose: () => void; onSaved: () => void }) {
  const [form, setForm] = useState({
    name: medication?.name || '',
    scientific_name: medication?.scientific_name || '',
    barcode: medication?.barcode || '',
    stock_quantity: medication?.stock_quantity || 0,
    reorder_level: medication?.reorder_level || 10,
    unit_price: medication?.unit_price || 0,
    expiry_date: medication?.expiry_date || '',
    description: medication?.description || '',
    instructions: medication?.instructions || '',
  });
  const [saving, setSaving] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.name) { toast.error('اسم الدواء مطلوب'); return; }
    setSaving(true);
    try {
      if (medication) {
        await pharmacyAPI.updateMedication(medication.id, form);
        toast.success('تم تعديل الدواء بنجاح');
      } else {
        await pharmacyAPI.createMedication(form);
        toast.success('تم إضافة الدواء بنجاح');
      }
      onSaved();
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || 'حدث خطأ');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4" onClick={onClose}>
      <div className="bg-white dark:bg-slate-900 rounded-2xl shadow-xl max-w-lg w-full max-h-[90vh] overflow-y-auto p-6" onClick={e => e.stopPropagation()}>
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-xl font-bold text-slate-900 dark:text-white">{medication ? 'تعديل الدواء' : 'إضافة دواء جديد'}</h2>
          <button onClick={onClose} className="p-2 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-xl transition-colors">
            <X className="w-5 h-5 text-slate-500" />
          </button>
        </div>
        <form onSubmit={handleSubmit} className="space-y-4">
          {[
            { key: 'name', label: 'اسم الدواء', type: 'text', required: true },
            { key: 'scientific_name', label: 'الاسم العلمي', type: 'text' },
            { key: 'barcode', label: 'الباركود', type: 'text' },
          ].map(f => (
            <div key={f.key}>
              <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">{f.label}</label>
              <input
                type={f.type}
                value={(form as any)[f.key]}
                onChange={e => setForm({ ...form, [f.key]: e.target.value })}
                required={f.required}
                className="w-full px-4 py-2.5 border border-slate-200 dark:border-slate-700 rounded-xl bg-slate-50/50 dark:bg-slate-800/50 text-slate-900 dark:text-white focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-colors"
              />
            </div>
          ))}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">الكمية</label>
              <input type="number" value={form.stock_quantity} onChange={e => setForm({ ...form, stock_quantity: Number(e.target.value) })} min="0"
                className="w-full px-4 py-2.5 border border-slate-200 dark:border-slate-700 rounded-xl bg-slate-50/50 dark:bg-slate-800/50 text-slate-900 dark:text-white focus:ring-2 focus:ring-indigo-500/20 transition-colors" />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">حد إعادة الطلب</label>
              <input type="number" value={form.reorder_level} onChange={e => setForm({ ...form, reorder_level: Number(e.target.value) })} min="0"
                className="w-full px-4 py-2.5 border border-slate-200 dark:border-slate-700 rounded-xl bg-slate-50/50 dark:bg-slate-800/50 text-slate-900 dark:text-white focus:ring-2 focus:ring-indigo-500/20 transition-colors" />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">سعر الوحدة</label>
              <input type="number" step="0.01" value={form.unit_price} onChange={e => setForm({ ...form, unit_price: Number(e.target.value) })} min="0"
                className="w-full px-4 py-2.5 border border-slate-200 dark:border-slate-700 rounded-xl bg-slate-50/50 dark:bg-slate-800/50 text-slate-900 dark:text-white focus:ring-2 focus:ring-indigo-500/20 transition-colors" />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">تاريخ الانتهاء</label>
              <input type="date" value={form.expiry_date || ''} onChange={e => setForm({ ...form, expiry_date: e.target.value })}
                className="w-full px-4 py-2.5 border border-slate-200 dark:border-slate-700 rounded-xl bg-slate-50/50 dark:bg-slate-800/50 text-slate-900 dark:text-white focus:ring-2 focus:ring-indigo-500/20 transition-colors" />
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">الوصف</label>
            <textarea value={form.description} onChange={e => setForm({ ...form, description: e.target.value })} rows={2}
              className="w-full px-4 py-2.5 border border-slate-200 dark:border-slate-700 rounded-xl bg-slate-50/50 dark:bg-slate-800/50 text-slate-900 dark:text-white focus:ring-2 focus:ring-indigo-500/20 transition-colors resize-none" />
          </div>
          <button
            type="submit"
            disabled={saving}
            className="w-full py-3 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl font-medium transition-colors disabled:opacity-50"
          >
            {saving ? 'جارٍ الحفظ...' : medication ? 'حفظ التعديلات' : 'إضافة الدواء'}
          </button>
        </form>
      </div>
    </div>
  );
}

// ─── Stock Adjustment Modal ──────────────────────────────────────────
function StockAdjustModal({ medication, onClose, onSaved }: { medication: Medication; onClose: () => void; onSaved: () => void }) {
  const [type, setType] = useState<'IN' | 'OUT' | 'ADJUSTMENT' | 'RETURN'>('IN');
  const [qty, setQty] = useState(1);
  const [reason, setReason] = useState('');
  const [saving, setSaving] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      await pharmacyAPI.adjustStock(medication.id, {
        medication_id: medication.id,
        quantity: qty,
        movement_type: type,
        reason,
      });
      toast.success('تم تعديل المخزون بنجاح');
      onSaved();
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || 'فشل تعديل المخزون');
    } finally {
      setSaving(false);
    }
  };

  const typeLabels: Record<string, string> = { IN: 'إضافة (وارد)', OUT: 'صرف (صادر)', ADJUSTMENT: 'تعديل يدوي', RETURN: 'إرجاع' };

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4" onClick={onClose}>
      <div className="bg-white dark:bg-slate-900 rounded-2xl shadow-xl max-w-md w-full p-6" onClick={e => e.stopPropagation()}>
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-xl font-bold text-slate-900 dark:text-white">تعديل المخزون</h2>
          <button onClick={onClose} className="p-2 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-xl transition-colors">
            <X className="w-5 h-5 text-slate-500" />
          </button>
        </div>
        <div className="mb-4 p-3 bg-indigo-50 dark:bg-indigo-500/10 rounded-xl">
          <p className="font-medium text-indigo-800 dark:text-indigo-300">{medication.name}</p>
          <p className="text-sm text-indigo-600 dark:text-indigo-400">المخزون الحالي: <span className="font-bold">{medication.stock_quantity}</span></p>
        </div>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">نوع الحركة</label>
            <select
              value={type}
              onChange={e => setType(e.target.value as any)}
              className="w-full px-4 py-2.5 border border-slate-200 dark:border-slate-700 rounded-xl bg-slate-50/50 dark:bg-slate-800/50 text-slate-900 dark:text-white focus:ring-2 focus:ring-indigo-500/20 transition-colors"
            >
              {Object.entries(typeLabels).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">الكمية</label>
            <input type="number" value={qty} onChange={e => setQty(Number(e.target.value))} min={1}
              className="w-full px-4 py-2.5 border border-slate-200 dark:border-slate-700 rounded-xl bg-slate-50/50 dark:bg-slate-800/50 text-slate-900 dark:text-white focus:ring-2 focus:ring-indigo-500/20 transition-colors" />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">السبب (اختياري)</label>
            <input type="text" value={reason} onChange={e => setReason(e.target.value)}
              className="w-full px-4 py-2.5 border border-slate-200 dark:border-slate-700 rounded-xl bg-slate-50/50 dark:bg-slate-800/50 text-slate-900 dark:text-white focus:ring-2 focus:ring-indigo-500/20 transition-colors" />
          </div>
          <button type="submit" disabled={saving} className="w-full py-3 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl font-medium transition-colors disabled:opacity-50">
            {saving ? 'جارٍ التحديث...' : 'تطبيق التعديل'}
          </button>
        </form>
      </div>
    </div>
  );
}
