import React, { useState } from 'react';
import { CreditCard, Receipt, ShieldCheck, Plus, Search, CheckCircle2 } from 'lucide-react';
import PageHeader from '../components/common/PageHeader';
import Card from '../components/common/Card';

const BillingDashboard = () => {
  const [activeTab, setActiveTab] = useState<'invoices' | 'insurance' | 'reports'>('invoices');

  return (
    <div className="space-y-6 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 animate-in fade-in zoom-in duration-500">
      <PageHeader
        title="الفواتير والتأمين"
        description="إدارة المطالبات المالية، فواتير المرضى، وشركات التأمين الصحي"
        icon={<CreditCard className="w-8 h-8 text-emerald-500" />}
      />

      {/* Tabs */}
      <div className="flex space-x-4 space-x-reverse border-b border-slate-200/50 dark:border-slate-700/50 pb-2">
        <button
          onClick={() => setActiveTab('invoices')}
          className={`pb-2 px-4 text-sm font-medium transition-colors border-b-2 ${
            activeTab === 'invoices'
              ? 'border-emerald-500 text-emerald-600 dark:text-emerald-400'
              : 'border-transparent text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-300'
          }`}
        >
          الفواتير والمطالبات
        </button>
        <button
          onClick={() => setActiveTab('insurance')}
          className={`pb-2 px-4 text-sm font-medium transition-colors border-b-2 ${
            activeTab === 'insurance'
              ? 'border-emerald-500 text-emerald-600 dark:text-emerald-400'
              : 'border-transparent text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-300'
          }`}
        >
          شركات التأمين
        </button>
        <button
          onClick={() => setActiveTab('reports')}
          className={`pb-2 px-4 text-sm font-medium transition-colors border-b-2 ${
            activeTab === 'reports'
              ? 'border-emerald-500 text-emerald-600 dark:text-emerald-400'
              : 'border-transparent text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-300'
          }`}
        >
          التقارير المالية
        </button>
      </div>

      {activeTab === 'invoices' && (
        <Card className="p-6">
          <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 mb-6">
            <div className="relative flex-1 max-w-md">
              <div className="absolute inset-y-0 right-0 pr-3 flex items-center pointer-events-none">
                <Search className="h-5 w-5 text-slate-400" />
              </div>
              <input
                type="text"
                placeholder="ابحث برقم الفاتورة أو اسم المريض..."
                className="block w-full pr-10 pl-3 py-2.5 border border-slate-200 dark:border-slate-700 rounded-xl bg-slate-50/50 dark:bg-slate-800/50 text-slate-900 dark:text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 transition-colors"
              />
            </div>
            <button className="inline-flex items-center justify-center px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl shadow-sm hover:shadow transition-all text-sm font-medium">
              <Plus className="w-4 h-4 ml-2" />
              إصدار فاتورة جديدة
            </button>
          </div>
          
          <div className="text-center py-12 border-2 border-dashed border-slate-200 dark:border-slate-700 rounded-xl">
            <Receipt className="w-12 h-12 text-slate-300 dark:text-slate-600 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-slate-900 dark:text-white mb-1">لا توجد فواتير</h3>
            <p className="text-slate-500 dark:text-slate-400 max-w-sm mx-auto">
              قم بإصدار الفواتير للمرضى وربطها بشركات التأمين الخاصة بهم.
            </p>
          </div>
        </Card>
      )}

      {activeTab === 'insurance' && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {/* Mock data for visualization */}
          {[1, 2, 3].map((i) => (
             <Card key={i} className="p-6 hover:border-emerald-500/50 transition-colors cursor-pointer group">
               <div className="flex items-start justify-between mb-4">
                 <div className="p-3 bg-emerald-50 dark:bg-emerald-500/10 rounded-xl text-emerald-600 dark:text-emerald-400 group-hover:scale-110 transition-transform">
                   <ShieldCheck className="w-6 h-6" />
                 </div>
                 <span className="px-2.5 py-1 bg-emerald-100 dark:bg-emerald-500/20 text-emerald-700 dark:text-emerald-300 text-xs font-medium rounded-full flex items-center">
                   <CheckCircle2 className="w-3 h-3 ml-1" />
                   مفعل
                 </span>
               </div>
               <h3 className="text-lg font-bold text-slate-900 dark:text-white mb-1">شركة التأمين {i}</h3>
               <p className="text-sm text-slate-500 dark:text-slate-400 mb-4">تغطية شاملة لجميع الخدمات الأساسية مع نسبة تحمل 20%</p>
               <div className="pt-4 border-t border-slate-100 dark:border-slate-700/50 flex justify-between items-center">
                 <span className="text-xs text-slate-500 dark:text-slate-400">آخر تحديث للربط الآلي: اليوم</span>
                 <button className="text-emerald-600 dark:text-emerald-400 text-sm font-medium hover:underline">
                   إدارة البوليصة
                 </button>
               </div>
             </Card>
          ))}
        </div>
      )}

      {activeTab === 'reports' && (
        <Card className="p-6">
          <div className="text-center py-12">
            <p className="text-slate-500 dark:text-slate-400">
              سيتم عرض إحصائيات الإيرادات والمطالبات المعلقة هنا قريباً.
            </p>
          </div>
        </Card>
      )}
    </div>
  );
};

export default BillingDashboard;
