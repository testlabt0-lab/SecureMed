import React, { useState } from 'react';
import { Pill, AlertTriangle, FileText, Plus, Search, ChevronRight, ShieldCheck } from 'lucide-react';
import PageHeader from '../components/common/PageHeader';
import Card from '../components/common/Card';

const PharmacyDashboard = () => {
  const [activeTab, setActiveTab] = useState<'inventory' | 'prescriptions' | 'alerts'>('inventory');

  return (
    <div className="space-y-6 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 animate-in fade-in zoom-in duration-500">
      <PageHeader
        title="الصيدلية والوصفات الطبية"
        description="إدارة المخزون، الوصفات الإلكترونية، والتحقق من التداخلات الدوائية"
        icon={<Pill className="w-8 h-8 text-indigo-500" />}
      />

      {/* Tabs */}
      <div className="flex space-x-4 space-x-reverse border-b border-slate-200/50 dark:border-slate-700/50 pb-2">
        <button
          onClick={() => setActiveTab('inventory')}
          className={`pb-2 px-4 text-sm font-medium transition-colors border-b-2 ${
            activeTab === 'inventory'
              ? 'border-indigo-500 text-indigo-600 dark:text-indigo-400'
              : 'border-transparent text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-300'
          }`}
        >
          المخزون الدوائي
        </button>
        <button
          onClick={() => setActiveTab('prescriptions')}
          className={`pb-2 px-4 text-sm font-medium transition-colors border-b-2 ${
            activeTab === 'prescriptions'
              ? 'border-indigo-500 text-indigo-600 dark:text-indigo-400'
              : 'border-transparent text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-300'
          }`}
        >
          الوصفات الإلكترونية (e-Prescribing)
        </button>
        <button
          onClick={() => setActiveTab('alerts')}
          className={`pb-2 px-4 text-sm font-medium transition-colors border-b-2 ${
            activeTab === 'alerts'
              ? 'border-rose-500 text-rose-600 dark:text-rose-400'
              : 'border-transparent text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-300'
          }`}
        >
          تنبيهات التداخلات
        </button>
      </div>

      {activeTab === 'inventory' && (
        <Card className="p-6">
          <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 mb-6">
            <div className="relative flex-1 max-w-md">
              <div className="absolute inset-y-0 right-0 pr-3 flex items-center pointer-events-none">
                <Search className="h-5 w-5 text-slate-400" />
              </div>
              <input
                type="text"
                placeholder="ابحث عن دواء..."
                className="block w-full pr-10 pl-3 py-2.5 border border-slate-200 dark:border-slate-700 rounded-xl bg-slate-50/50 dark:bg-slate-800/50 text-slate-900 dark:text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-colors"
              />
            </div>
            <button className="inline-flex items-center justify-center px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl shadow-sm hover:shadow transition-all text-sm font-medium">
              <Plus className="w-4 h-4 ml-2" />
              إضافة دواء جديد
            </button>
          </div>
          
          <div className="text-center py-12">
            <Pill className="w-12 h-12 text-slate-300 dark:text-slate-600 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-slate-900 dark:text-white mb-1">لا توجد أدوية</h3>
            <p className="text-slate-500 dark:text-slate-400 max-w-sm mx-auto">
              المخزون فارغ حالياً. قم بإضافة الأدوية لتبدأ في إدارة الصيدلية.
            </p>
          </div>
        </Card>
      )}

      {activeTab === 'prescriptions' && (
        <Card className="p-6">
          <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 mb-6">
             <h2 className="text-lg font-semibold text-slate-800 dark:text-slate-100 flex items-center">
                <FileText className="w-5 h-5 ml-2 text-indigo-500" />
                الوصفات الواردة
             </h2>
             <button className="inline-flex items-center justify-center px-4 py-2 bg-indigo-50 dark:bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 rounded-xl hover:bg-indigo-100 dark:hover:bg-indigo-500/20 transition-colors text-sm font-medium">
              إنشاء وصفة جديدة (للطبيب)
            </button>
          </div>
          
          {/* Example Prescription with QR Code */}
          <div className="border border-slate-200 dark:border-slate-700 rounded-xl p-4 mb-4 hover:border-indigo-300 dark:hover:border-indigo-600 transition-colors bg-white dark:bg-slate-900">
            <div className="flex flex-col sm:flex-row justify-between items-start gap-4">
              <div>
                <div className="flex items-center space-x-2 space-x-reverse mb-2">
                  <span className="px-2.5 py-1 bg-indigo-100 dark:bg-indigo-500/20 text-indigo-700 dark:text-indigo-300 text-xs font-bold rounded-full">وصفة إلكترونية</span>
                  <span className="text-sm text-slate-500">د. أحمد خالد (استشاري قلب)</span>
                </div>
                <h3 className="text-lg font-bold text-slate-900 dark:text-white">المريض: محمد عبدالله</h3>
                <p className="text-sm text-slate-600 dark:text-slate-400 mt-1">التشخيص: I10 - ارتفاع ضغط الدم الأساسي</p>
                <div className="mt-4 space-y-2">
                  <div className="p-3 bg-slate-50 dark:bg-slate-800 rounded-lg flex justify-between items-center">
                    <span className="font-medium text-slate-800 dark:text-slate-200">Aspirin 81mg</span>
                    <span className="text-sm text-slate-500">حبة يومياً (30 حبة)</span>
                  </div>
                </div>
              </div>
              
              <div className="flex flex-col items-center justify-center p-4 bg-slate-50 dark:bg-slate-800 rounded-xl min-w-[140px]">
                {/* Simulated QR Code generated from Backend get_qr_code_base64() */}
                <div className="w-24 h-24 bg-white p-2 rounded-lg shadow-sm border border-slate-200 flex items-center justify-center">
                  <img src={`https://api.qrserver.com/v1/create-qr-code/?size=100x100&data=Prescription-12345-Signed`} alt="QR Code" className="w-full h-full object-contain" />
                </div>
                <span className="text-xs text-slate-500 mt-2 flex items-center">
                  <ShieldCheck className="w-3 h-3 ml-1 text-emerald-500" /> موثقة رقمياً
                </span>
                <button className="mt-3 w-full px-3 py-1.5 bg-slate-200 hover:bg-slate-300 dark:bg-slate-700 dark:hover:bg-slate-600 text-slate-700 dark:text-slate-200 text-xs font-medium rounded-lg transition-colors">
                  طباعة الوصفة
                </button>
              </div>
            </div>
          </div>
        </Card>
      )}

      {activeTab === 'alerts' && (
        <Card className="p-6 border-l-4 border-l-rose-500">
          <div className="flex items-center space-x-4 space-x-reverse mb-4">
            <div className="p-3 bg-rose-100 dark:bg-rose-500/20 rounded-full">
              <AlertTriangle className="w-6 h-6 text-rose-600 dark:text-rose-400" />
            </div>
            <div>
              <h3 className="text-lg font-semibold text-slate-900 dark:text-white">التداخلات الدوائية ومخاطر الوصفات</h3>
              <p className="text-sm text-slate-500 dark:text-slate-400">
                قواعد الذكاء الاصطناعي لفحص توافق الأدوية قبل الصرف
              </p>
            </div>
          </div>
          <div className="mt-6 bg-slate-50 dark:bg-slate-800/50 rounded-xl p-6 text-center">
             <p className="text-slate-500 dark:text-slate-400">لم يتم رصد أي تداخلات خطيرة حديثاً.</p>
          </div>
        </Card>
      )}
    </div>
  );
};

export default PharmacyDashboard;
