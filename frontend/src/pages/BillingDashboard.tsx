import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  CreditCard, DollarSign, FileText, Plus, Search, TrendingUp,
  CheckCircle, XCircle, Clock, Building2, Shield, Printer,
  Receipt, AlertCircle, X, ChevronDown, Banknote, Wallet,
} from 'lucide-react';
import toast from 'react-hot-toast';
import PageHeader from '../components/common/PageHeader';
import Card from '../components/common/Card';
import { billingAPI } from '../api/extendedApis';
import CreateInvoiceModal from '../components/billing/CreateInvoiceModal';
import { useAuthStore } from '../store/authStore';

// ─── Types ───────────────────────────────────────────────────────────────
interface Invoice {
  id: string;
  patient: string;
  patient_name: string;
  created_by: string;
  created_by_name: string;
  total_amount: number;
  discount: number;
  insurance_covered: number;
  patient_payable: number;
  vat_amount: number;
  final_total_with_vat: number;
  status: string;
  due_date: string | null;
  items: InvoiceItem[];
  created_at: string;
}

interface InvoiceItem {
  id: string;
  description: string;
  quantity: number;
  unit_price: number;
  total_price: number;
}

interface BillingStats {
  total_invoices: number;
  paid_invoices: number;
  unpaid_invoices: number;
  total_revenue: number;
  pending_amount: number;
  insurance_collected: number;
  today_revenue: number;
  monthly_revenue: number;
}

interface InsuranceProvider {
  id: string;
  name: string;
  contact_email: string;
  contact_phone: string;
  is_active: boolean;
}

// ─── Helpers ─────────────────────────────────────────────────────────────
const extractArray = (data: any): any[] =>
  Array.isArray(data) ? data : Array.isArray(data?.results) ? data.results : [];

const fmt = (n: number) => new Intl.NumberFormat('ar-YE', { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(n);

const statusConfig: Record<string, { label: string; cls: string; icon: any }> = {
  DRAFT: { label: 'مسودة', cls: 'bg-slate-100 text-slate-700 dark:bg-slate-700 dark:text-slate-300', icon: FileText },
  PENDING_INSURANCE: { label: 'بانتظار التأمين', cls: 'bg-blue-100 text-blue-700 dark:bg-blue-500/20 dark:text-blue-300', icon: Shield },
  UNPAID: { label: 'غير مدفوعة', cls: 'bg-amber-100 text-amber-700 dark:bg-amber-500/20 dark:text-amber-300', icon: Clock },
  PARTIAL: { label: 'مدفوعة جزئياً', cls: 'bg-orange-100 text-orange-700 dark:bg-orange-500/20 dark:text-orange-300', icon: Wallet },
  PAID: { label: 'مدفوعة', cls: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-500/20 dark:text-emerald-300', icon: CheckCircle },
  CANCELLED: { label: 'ملغاة', cls: 'bg-rose-100 text-rose-700 dark:bg-rose-500/20 dark:text-rose-300', icon: XCircle },
};

// ─── Main Component ──────────────────────────────────────────────────────
export default function BillingManagement() {
  const qc = useQueryClient();
  const [activeTab, setActiveTab] = useState<'invoices' | 'insurance' | 'reports'>('invoices');
  const [statusFilter, setStatusFilter] = useState('');
  const [selectedInvoice, setSelectedInvoice] = useState<Invoice | null>(null);
  const [showPayModal, setShowPayModal] = useState<Invoice | null>(null);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const user = useAuthStore(state => state.user);

  // Queries
  const { data: statsData } = useQuery({
    queryKey: ['billing-stats'],
    queryFn: () => billingAPI.stats().then(r => r.data),
  });
  const stats: BillingStats = statsData || {} as BillingStats;

  const { data: invoicesRaw, isLoading } = useQuery({
    queryKey: ['billing-invoices', statusFilter],
    queryFn: () => billingAPI.invoices({ status: statusFilter || undefined }).then(r => r.data),
  });
  const invoices: Invoice[] = extractArray(invoicesRaw);

  const { data: providersRaw } = useQuery({
    queryKey: ['insurance-providers'],
    queryFn: () => billingAPI.insuranceProviders().then(r => r.data),
    enabled: activeTab === 'insurance',
  });
  const providers: InsuranceProvider[] = extractArray(providersRaw);

  // Mutations
  const payMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: any }) => billingAPI.payInvoice(id, data),
    onSuccess: () => {
      toast.success('تم تسجيل الدفع بنجاح');
      setShowPayModal(null);
      qc.invalidateQueries({ queryKey: ['billing-invoices'] });
      qc.invalidateQueries({ queryKey: ['billing-stats'] });
    },
    onError: (err: any) => toast.error(err?.response?.data?.detail || 'فشلت عملية الدفع'),
  });

  const cancelMutation = useMutation({
    mutationFn: (id: string) => billingAPI.cancelInvoice(id),
    onSuccess: () => {
      toast.success('تم إلغاء الفاتورة');
      qc.invalidateQueries({ queryKey: ['billing-invoices'] });
      qc.invalidateQueries({ queryKey: ['billing-stats'] });
    },
    onError: (err: any) => toast.error(err?.response?.data?.detail || 'فشل الإلغاء'),
  });

  const tabs = [
    { key: 'invoices' as const, label: 'الفواتير', icon: Receipt },
    { key: 'insurance' as const, label: 'شركات التأمين', icon: Shield },
    { key: 'reports' as const, label: 'التقارير المالية', icon: TrendingUp },
  ];

  return (
    <div className="space-y-6 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 animate-in fade-in zoom-in duration-500">
      <PageHeader
        title="الفوترة والتأمين الصحي"
        description="إدارة الفواتير، تأمينات المرضى، والتقارير المالية"
        icon={<CreditCard className="w-8 h-8 text-emerald-500" />}
      />

      {/* ─── Stats Cards ───────────────────────────────────────────── */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { label: 'إيرادات اليوم', value: `${fmt(stats.today_revenue ?? 0)} ر.ي`, icon: DollarSign, color: 'emerald', gradient: 'from-emerald-500 to-teal-600' },
          { label: 'إيرادات الشهر', value: `${fmt(stats.monthly_revenue ?? 0)} ر.ي`, icon: TrendingUp, color: 'blue', gradient: 'from-blue-500 to-indigo-600' },
          { label: 'فواتير معلقة', value: String(stats.unpaid_invoices ?? 0), icon: Clock, color: 'amber', gradient: 'from-amber-500 to-orange-600' },
          { label: 'تغطية التأمين', value: `${fmt(stats.insurance_collected ?? 0)} ر.ي`, icon: Shield, color: 'violet', gradient: 'from-violet-500 to-purple-600' },
        ].map((s, i) => (
          <div key={i} className="relative overflow-hidden rounded-2xl bg-white dark:bg-slate-900 border border-slate-200/60 dark:border-slate-700/60 p-5 shadow-sm">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-slate-500 dark:text-slate-400">{s.label}</p>
                <p className="text-xl font-bold text-slate-900 dark:text-white mt-1">{s.value}</p>
              </div>
              <div className={`p-3 rounded-xl bg-gradient-to-br ${s.gradient} shadow-sm`}>
                <s.icon className="w-6 h-6 text-white" />
              </div>
            </div>
            <div className={`absolute bottom-0 left-0 right-0 h-1 bg-gradient-to-r ${s.gradient}`} />
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
                ? 'border-emerald-500 text-emerald-600 dark:text-emerald-400'
                : 'border-transparent text-slate-500 hover:text-slate-700 dark:text-slate-400'
            }`}
          >
            <t.icon className="w-4 h-4" />
            {t.label}
          </button>
        ))}
      </div>

      {/* ─── TAB: Invoices ───────────────────────────────────────── */}
      {activeTab === 'invoices' && (
        <Card className="p-6">
          <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 mb-6">
            <select
              value={statusFilter}
              onChange={e => setStatusFilter(e.target.value)}
              className="px-4 py-2.5 border border-slate-200 dark:border-slate-700 rounded-xl bg-slate-50/50 dark:bg-slate-800/50 text-slate-700 dark:text-slate-300 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500/20"
            >
              <option value="">كل الفواتير</option>
              <option value="UNPAID">غير مدفوعة</option>
              <option value="PAID">مدفوعة</option>
              <option value="PARTIAL">مدفوعة جزئياً</option>
              <option value="CANCELLED">ملغاة</option>
              <option value="PENDING_INSURANCE">بانتظار التأمين</option>
            </select>
            {user && ['SUPER_ADMIN', 'HOSPITAL_ADMIN', 'CENTER_ADMIN', 'ACCOUNTANT', 'RECEPTIONIST'].includes(user.role) && (
              <button 
                onClick={() => setShowCreateModal(true)}
                className="flex items-center gap-2 px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-sm font-medium transition-colors"
              >
                <Plus className="w-4 h-4" />
                إصدار فاتورة
              </button>
            )}
          </div>

          {isLoading ? (
            <div className="space-y-3">{[1,2,3].map(i => <div key={i} className="h-20 bg-slate-100 dark:bg-slate-800 rounded-xl animate-pulse" />)}</div>
          ) : invoices.length === 0 ? (
            <div className="text-center py-16">
              <Receipt className="w-16 h-16 text-slate-300 dark:text-slate-600 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-slate-900 dark:text-white mb-1">لا توجد فواتير</h3>
              <p className="text-slate-500 dark:text-slate-400">لم يتم إنشاء أي فواتير بعد</p>
            </div>
          ) : (
            <div className="space-y-3">
              {invoices.map(inv => {
                const sc = statusConfig[inv.status] || statusConfig.DRAFT;
                const StatusIcon = sc.icon;
                return (
                  <div
                    key={inv.id}
                    className="border border-slate-200 dark:border-slate-700 rounded-xl p-4 hover:shadow-md transition-all cursor-pointer bg-white dark:bg-slate-900"
                    onClick={() => setSelectedInvoice(selectedInvoice?.id === inv.id ? null : inv)}
                  >
                    <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-3">
                      <div className="flex items-center gap-3">
                        <div className={`p-2 rounded-xl ${sc.cls}`}>
                          <StatusIcon className="w-5 h-5" />
                        </div>
                        <div>
                          <h4 className="font-bold text-slate-900 dark:text-white">{inv.patient_name}</h4>
                          <p className="text-xs text-slate-500">
                            {new Date(inv.created_at).toLocaleDateString('ar-YE')} — #{inv.id.slice(0, 8)}
                          </p>
                        </div>
                      </div>
                      <div className="flex items-center gap-4">
                        <div className="text-left">
                          <p className="text-xs text-slate-500 dark:text-slate-400">الإجمالي</p>
                          <p className="font-bold text-lg text-slate-900 dark:text-white">{fmt(inv.total_amount)} ر.ي</p>
                        </div>
                        {inv.insurance_covered > 0 && (
                          <div className="text-left">
                            <p className="text-xs text-slate-500 dark:text-slate-400">تغطية التأمين</p>
                            <p className="font-bold text-emerald-600">{fmt(inv.insurance_covered)} ر.ي</p>
                          </div>
                        )}
                        <div className="text-left">
                          <p className="text-xs text-slate-500 dark:text-slate-400">المستحق</p>
                          <p className="font-bold text-indigo-600 dark:text-indigo-400">{fmt(inv.final_total_with_vat)} ر.ي</p>
                        </div>
                        <span className={`px-3 py-1 text-xs rounded-full font-bold ${sc.cls}`}>{sc.label}</span>
                      </div>
                    </div>

                    {/* Expanded Details */}
                    {selectedInvoice?.id === inv.id && (
                      <div className="mt-4 pt-4 border-t border-slate-200 dark:border-slate-700 animate-in slide-in-from-top-2 duration-300">
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
                          <div className="p-3 bg-slate-50 dark:bg-slate-800 rounded-lg">
                            <p className="text-xs text-slate-500">المبلغ الإجمالي</p>
                            <p className="font-bold text-slate-900 dark:text-white">{fmt(inv.total_amount)} ر.ي</p>
                          </div>
                          <div className="p-3 bg-slate-50 dark:bg-slate-800 rounded-lg">
                            <p className="text-xs text-slate-500">الخصم</p>
                            <p className="font-bold text-slate-900 dark:text-white">{fmt(inv.discount)} ر.ي</p>
                          </div>
                          <div className="p-3 bg-slate-50 dark:bg-slate-800 rounded-lg">
                            <p className="text-xs text-slate-500">ض.ق.م (15%)</p>
                            <p className="font-bold text-slate-900 dark:text-white">{fmt(inv.vat_amount)} ر.ي</p>
                          </div>
                          <div className="p-3 bg-emerald-50 dark:bg-emerald-500/10 rounded-lg">
                            <p className="text-xs text-emerald-700 dark:text-emerald-300">الصافي المطلوب</p>
                            <p className="font-bold text-emerald-700 dark:text-emerald-400">{fmt(inv.final_total_with_vat)} ر.ي</p>
                          </div>
                        </div>

                        {inv.items.length > 0 && (
                          <table className="w-full mb-4">
                            <thead>
                              <tr className="border-b border-slate-200 dark:border-slate-700">
                                <th className="text-right py-2 text-xs font-semibold text-slate-500">البند</th>
                                <th className="text-right py-2 text-xs font-semibold text-slate-500">الكمية</th>
                                <th className="text-right py-2 text-xs font-semibold text-slate-500">سعر الوحدة</th>
                                <th className="text-right py-2 text-xs font-semibold text-slate-500">الإجمالي</th>
                              </tr>
                            </thead>
                            <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                              {inv.items.map(item => (
                                <tr key={item.id}>
                                  <td className="py-2 text-sm text-slate-800 dark:text-slate-200">{item.description}</td>
                                  <td className="py-2 text-sm text-slate-600 dark:text-slate-400">{item.quantity}</td>
                                  <td className="py-2 text-sm text-slate-600 dark:text-slate-400">{fmt(item.unit_price)}</td>
                                  <td className="py-2 text-sm font-medium text-slate-800 dark:text-slate-200">{fmt(item.total_price)}</td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        )}

                        <div className="flex gap-3 justify-end">
                          <button
                            onClick={e => { e.stopPropagation(); window.print(); }}
                            className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 dark:bg-slate-800 dark:hover:bg-slate-700 dark:text-slate-300 rounded-xl text-sm font-medium transition-colors"
                          >
                            <Printer className="w-4 h-4 inline ml-1" />
                            طباعة الفاتورة
                          </button>
                          {user && ['SUPER_ADMIN', 'HOSPITAL_ADMIN', 'CENTER_ADMIN', 'ACCOUNTANT', 'RECEPTIONIST'].includes(user.role) && (
                            <>
                              {inv.status === 'UNPAID' && (
                                <button
                                  onClick={e => { e.stopPropagation(); setShowPayModal(inv); }}
                                  className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl text-sm font-medium transition-colors"
                                >
                                  <Banknote className="w-4 h-4 inline ml-1" />
                                  تسجيل دفع
                                </button>
                              )}
                              {inv.status !== 'PAID' && inv.status !== 'CANCELLED' && (
                                <button
                                  onClick={e => { e.stopPropagation(); if (confirm('إلغاء هذه الفاتورة؟')) cancelMutation.mutate(inv.id); }}
                                  className="px-4 py-2 bg-rose-100 hover:bg-rose-200 text-rose-700 dark:bg-rose-500/20 dark:text-rose-300 rounded-xl text-sm font-medium transition-colors"
                                >
                                  <XCircle className="w-4 h-4 inline ml-1" />
                                  إلغاء الفاتورة
                                </button>
                              )}
                            </>
                          )}
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </Card>
      )}

      {/* ─── TAB: Insurance Providers ────────────────────────────── */}
      {activeTab === 'insurance' && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {providers.length === 0 ? (
            <Card className="col-span-full p-12 text-center">
              <Shield className="w-16 h-16 text-slate-300 dark:text-slate-600 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-slate-900 dark:text-white mb-1">لا توجد شركات تأمين</h3>
              <p className="text-slate-500 dark:text-slate-400">أضف شركات التأمين الصحي للبدء</p>
            </Card>
          ) : (
            providers.map(p => (
              <Card key={p.id} className="p-5">
                <div className="flex items-start justify-between mb-3">
                  <div className="flex items-center gap-3">
                    <div className="p-2.5 bg-violet-100 dark:bg-violet-500/20 rounded-xl">
                      <Building2 className="w-5 h-5 text-violet-600 dark:text-violet-400" />
                    </div>
                    <div>
                      <h4 className="font-bold text-slate-900 dark:text-white">{p.name}</h4>
                      <span className={`text-xs px-2 py-0.5 rounded-full ${p.is_active ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-500/20 dark:text-emerald-300' : 'bg-slate-100 text-slate-500'}`}>
                        {p.is_active ? 'نشط' : 'غير نشط'}
                      </span>
                    </div>
                  </div>
                </div>
                {p.contact_email && (
                  <p className="text-sm text-slate-500 dark:text-slate-400 mt-2">📧 {p.contact_email}</p>
                )}
                {p.contact_phone && (
                  <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">📞 {p.contact_phone}</p>
                )}
              </Card>
            ))
          )}
        </div>
      )}

      {/* ─── TAB: Financial Reports ──────────────────────────────── */}
      {activeTab === 'reports' && (
        <Card className="p-6">
          <h3 className="text-lg font-semibold text-slate-900 dark:text-white mb-6 flex items-center gap-2">
            <TrendingUp className="w-5 h-5 text-emerald-500" />
            ملخص مالي
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="space-y-4">
              {[
                { label: 'إجمالي الفواتير', value: stats.total_invoices ?? 0, type: 'number' },
                { label: 'الفواتير المدفوعة', value: stats.paid_invoices ?? 0, type: 'number' },
                { label: 'الفواتير المعلقة', value: stats.unpaid_invoices ?? 0, type: 'number' },
              ].map((item, i) => (
                <div key={i} className="flex justify-between items-center p-4 bg-slate-50 dark:bg-slate-800/50 rounded-xl">
                  <span className="text-slate-600 dark:text-slate-400">{item.label}</span>
                  <span className="text-xl font-bold text-slate-900 dark:text-white">{item.value}</span>
                </div>
              ))}
            </div>
            <div className="space-y-4">
              {[
                { label: 'إجمالي الإيرادات', value: `${fmt(stats.total_revenue ?? 0)} ر.ي`, color: 'text-emerald-600' },
                { label: 'المبالغ المعلقة', value: `${fmt(stats.pending_amount ?? 0)} ر.ي`, color: 'text-amber-600' },
                { label: 'إيرادات من التأمين', value: `${fmt(stats.insurance_collected ?? 0)} ر.ي`, color: 'text-violet-600' },
              ].map((item, i) => (
                <div key={i} className="flex justify-between items-center p-4 bg-slate-50 dark:bg-slate-800/50 rounded-xl">
                  <span className="text-slate-600 dark:text-slate-400">{item.label}</span>
                  <span className={`text-xl font-bold ${item.color}`}>{item.value}</span>
                </div>
              ))}
            </div>
          </div>
        </Card>
      )}

      {/* ─── Payment Modal ───────────────────────────────────────── */}
      {showPayModal && (
        <PaymentModal
          invoice={showPayModal}
          onClose={() => setShowPayModal(null)}
          onPay={(data) => payMutation.mutate({ id: showPayModal.id, data })}
          isPending={payMutation.isPending}
        />
      )}

      <CreateInvoiceModal isOpen={showCreateModal} onClose={() => setShowCreateModal(false)} />
    </div>
  );
}

// ─── Payment Modal ───────────────────────────────────────────────────────
function PaymentModal({ invoice, onClose, onPay, isPending }: {
  invoice: Invoice; onClose: () => void; onPay: (data: any) => void; isPending: boolean;
}) {
  const [method, setMethod] = useState('CASH');

  const methods = [
    { value: 'CASH', label: 'نقدي', icon: Banknote },
    { value: 'CREDIT_CARD', label: 'بطاقة ائتمان', icon: CreditCard },
    { value: 'BANK_TRANSFER', label: 'تحويل بنكي', icon: Building2 },
    { value: 'INSURANCE', label: 'تأمين', icon: Shield },
  ];

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4" onClick={onClose}>
      <div className="bg-white dark:bg-slate-900 rounded-2xl shadow-xl max-w-md w-full p-6" onClick={e => e.stopPropagation()}>
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-xl font-bold text-slate-900 dark:text-white">تسجيل دفع</h2>
          <button onClick={onClose} className="p-2 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-xl transition-colors">
            <X className="w-5 h-5 text-slate-500" />
          </button>
        </div>

        <div className="mb-6 p-4 bg-emerald-50 dark:bg-emerald-500/10 rounded-xl text-center">
          <p className="text-sm text-emerald-700 dark:text-emerald-300">المبلغ المستحق</p>
          <p className="text-3xl font-bold text-emerald-700 dark:text-emerald-400 mt-1">{fmt(invoice.final_total_with_vat)} ر.ي</p>
          <p className="text-xs text-emerald-600/70 dark:text-emerald-400/70 mt-1">شامل ض.ق.م 15%</p>
        </div>

        <div className="mb-6">
          <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-3">طريقة الدفع</label>
          <div className="grid grid-cols-2 gap-3">
            {methods.map(m => (
              <button
                key={m.value}
                onClick={() => setMethod(m.value)}
                className={`p-3 rounded-xl border-2 flex flex-col items-center gap-2 transition-all ${
                  method === m.value
                    ? 'border-emerald-500 bg-emerald-50 dark:bg-emerald-500/10'
                    : 'border-slate-200 dark:border-slate-700 hover:border-slate-300'
                }`}
              >
                <m.icon className={`w-5 h-5 ${method === m.value ? 'text-emerald-600 dark:text-emerald-400' : 'text-slate-400'}`} />
                <span className={`text-sm font-medium ${method === m.value ? 'text-emerald-700 dark:text-emerald-300' : 'text-slate-600 dark:text-slate-400'}`}>{m.label}</span>
              </button>
            ))}
          </div>
        </div>

        <button
          onClick={() => onPay({ payment_method: method })}
          disabled={isPending}
          className="w-full py-3 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl font-medium transition-colors disabled:opacity-50"
        >
          {isPending ? 'جارٍ المعالجة...' : 'تأكيد الدفع'}
        </button>
      </div>
    </div>
  );
}
