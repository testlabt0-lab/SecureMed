import React, { useEffect, useState, useMemo } from 'react';
import { securityAPI } from '../api/client';
import { Shield, ShieldAlert, ShieldCheck, RefreshCw, Smartphone, Laptop, Calendar, Globe, Search, Filter, Download } from 'lucide-react';
import { motion } from 'framer-motion';
import PageHeader from '../components/common/PageHeader';
import Card from '../components/common/Card';
import toast from 'react-hot-toast';

export const LoginHistory = () => {
  const [history, setHistory] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState<'all' | 'success' | 'failed'>('all');

  useEffect(() => {
    fetchHistory();
  }, []);

  const fetchHistory = async () => {
    setLoading(true);
    try {
      const response = await securityAPI.loginHistory.list();
      const data = response?.data;
      const list = Array.isArray(data) ? data : (Array.isArray(data?.results) ? data.results : []);
      setHistory(list);
    } catch (error) {
      console.error('Error fetching login history:', error);
      setHistory([]);
    } finally {
      setLoading(false);
    }
  };

  const historyList = Array.isArray(history) ? history : [];
  const successCount = historyList.filter((r) => r.is_success).length;
  const failedCount = historyList.filter((r) => !r.is_success).length;

  const filteredHistory = useMemo(() => {
    return historyList.filter((record) => {
      const matchesSearch =
        search === '' ||
        (record.user_email && record.user_email.toLowerCase().includes(search.toLowerCase())) ||
        (record.ip_address && record.ip_address.includes(search)) ||
        (record.failure_reason && record.failure_reason.toLowerCase().includes(search.toLowerCase())) ||
        (record.browser_info && record.browser_info.toLowerCase().includes(search.toLowerCase()));

      const matchesStatus =
        statusFilter === 'all' ||
        (statusFilter === 'success' && record.is_success) ||
        (statusFilter === 'failed' && !record.is_success);

      return matchesSearch && matchesStatus;
    });
  }, [historyList, search, statusFilter]);

  const exportCSV = () => {
    if (filteredHistory.length === 0) {
      toast.error('لا توجد بيانات لتصديرها');
      return;
    }
    const headers = ['الوقت', 'البريد الإلكتروني', 'عنوان IP', 'نظام التشغيل', 'المتصفح', 'الحالة', 'السبب'];
    const rows = filteredHistory.map((r) => [
      `"${r.timestamp ? new Date(r.timestamp).toLocaleString('ar-EG') : ''}"`,
      `"${r.user_email || r.email || ''}"`,
      `"${r.ip_address || ''}"`,
      `"${r.os_info || ''}"`,
      `"${r.browser_info || ''}"`,
      `"${r.is_success ? 'ناجح' : 'فاشل'}"`,
      `"${r.failure_reason || ''}"`,
    ]);
    const csvContent = 'data:text/csv;charset=utf-8,\uFEFF' + [headers.join(','), ...rows.map((row) => row.join(','))].join('\n');
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement('a');
    link.setAttribute('href', encodedUri);
    link.setAttribute('download', `login_history_export_${new Date().toISOString().slice(0, 10)}.csv`);
    document.body.appendChild(link);
    link.click();
    toast.success('تم تصدير سجلات الدخول بنجاح');
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 animate-in fade-in duration-300">
      <PageHeader
        title="سجل محاولات الدخول المفصل"
        description="تتبع كافة محاولات تسجيل الدخول الناجحة والفاشلة وعناوين IP وبصمات الأجهزة وتحليل الأنماط المشبوهة"
        icon={<Shield className="w-8 h-8 text-primary-500" />}
      >
        <div className="flex items-center gap-2">
          <button
            onClick={exportCSV}
            className="flex items-center gap-2 px-4 py-2 text-sm font-medium bg-emerald-50 dark:bg-emerald-900/30 border border-emerald-200 dark:border-emerald-800 rounded-xl hover:bg-emerald-100 dark:hover:bg-emerald-900/50 text-emerald-700 dark:text-emerald-300 transition-colors shadow-sm"
          >
            <Download className="w-4 h-4" />
            تصدير CSV
          </button>
          <button
            onClick={fetchHistory}
            disabled={loading}
            className="flex items-center gap-2 px-4 py-2 text-sm font-medium bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl hover:bg-gray-50 dark:hover:bg-gray-700/50 text-gray-700 dark:text-gray-200 transition-colors shadow-sm"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin text-primary-500' : ''}`} />
            تحديث
          </button>
        </div>
      </PageHeader>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <Card className="p-4 text-center cursor-pointer hover:border-primary-300 transition-colors" onClick={() => setStatusFilter('all')}>
          <div className="text-3xl font-extrabold text-primary-600 dark:text-primary-400">{historyList.length}</div>
          <div className="text-xs font-medium text-gray-500 dark:text-gray-400 mt-1">إجمالي المحاولات</div>
        </Card>
        <Card className="p-4 text-center cursor-pointer hover:border-emerald-300 transition-colors" onClick={() => setStatusFilter('success')}>
          <div className="text-3xl font-extrabold text-emerald-600 dark:text-emerald-400">{successCount}</div>
          <div className="text-xs font-medium text-gray-500 dark:text-gray-400 mt-1">محاولات ناجحة</div>
        </Card>
        <Card className="p-4 text-center cursor-pointer hover:border-red-300 transition-colors" onClick={() => setStatusFilter('failed')}>
          <div className="text-3xl font-extrabold text-red-600 dark:text-red-400">{failedCount}</div>
          <div className="text-xs font-medium text-gray-500 dark:text-gray-400 mt-1">محاولات فاشلة / مشبوهة</div>
        </Card>
      </div>

      {/* Search & Filter Toolbar */}
      <div className="flex flex-col sm:flex-row gap-3 items-center justify-between">
        <div className="relative flex-1 w-full">
          <Search className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="بحث بالبريد الإلكتروني، عنوان IP، المتصفح أو السبب..."
            className="input-field pr-9 w-full text-sm"
          />
        </div>
        <div className="flex items-center gap-2 w-full sm:w-auto">
          <Filter className="w-4 h-4 text-gray-400" />
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value as any)}
            className="input-field text-sm"
          >
            <option value="all">جميع الحالات</option>
            <option value="success">دخول ناجح فقط</option>
            <option value="failed">محاولات فاشلة فقط</option>
          </select>
        </div>
      </div>

      {/* Table */}
      <Card className="overflow-hidden p-0">
        <div className="px-6 py-4 border-b border-gray-100 dark:border-gray-700/60 flex items-center justify-between">
          <h3 className="font-semibold text-gray-900 dark:text-white">تفاصيل المحاولات الأخيرة</h3>
          <span className="text-xs bg-primary-50 dark:bg-primary-900/30 text-primary-700 dark:text-primary-300 font-semibold px-2.5 py-1 rounded-full">
            {filteredHistory.length} من أصل {historyList.length} سجل
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700/60">
            <thead className="bg-gray-50/50 dark:bg-gray-900/30">
              <tr>
                <th className="px-6 py-3 text-right text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">الوقت</th>
                <th className="px-6 py-3 text-right text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">المستخدم / IP</th>
                <th className="px-6 py-3 text-right text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">المتصفح ونظام التشغيل</th>
                <th className="px-6 py-3 text-right text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">الحالة</th>
                <th className="px-6 py-3 text-right text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">ملاحظات / السبب</th>
              </tr>
            </thead>
            <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-100 dark:divide-gray-700/40">
              {loading ? (
                <tr>
                  <td colSpan={5} className="px-6 py-12 text-center text-gray-500">
                    <RefreshCw className="w-6 h-6 animate-spin mx-auto mb-2 text-primary-500" />
                    جاري تحميل سجلات الدخول...
                  </td>
                </tr>
              ) : filteredHistory.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-6 py-12 text-center text-gray-500 dark:text-gray-400">
                    <Shield className="w-10 h-10 mx-auto mb-2 opacity-30" />
                    {search || statusFilter !== 'all' ? 'لا توجد نتائج تطابق خيارات البحث' : 'لا توجد محاولات دخول مسجلة حالياً'}
                  </td>
                </tr>
              ) : (
                filteredHistory.map((record: any, index: number) => (
                  <motion.tr
                    key={record.id}
                    initial={{ opacity: 0, y: 5 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: Math.min(index * 0.03, 0.3), duration: 0.2 }}
                    className="hover:bg-gray-50/50 dark:hover:bg-gray-700/30 transition-colors"
                  >
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600 dark:text-gray-300">
                      <div className="flex items-center gap-1.5 font-mono text-xs">
                        <Calendar className="w-3.5 h-3.5 text-gray-400" />
                        {record.timestamp ? new Date(record.timestamp).toLocaleString('ar-EG') : 'الآن'}
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div>
                        <div className="text-sm font-semibold text-gray-900 dark:text-white">
                          {record.user_email || record.email || 'مستخدم غير معروف'}
                        </div>
                        <div className="text-xs font-mono text-gray-400 flex items-center gap-1 mt-0.5">
                          <Globe className="w-3 h-3" />
                          {record.ip_address || '127.0.0.1'}
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600 dark:text-gray-300">
                      <div className="flex items-center gap-2">
                        {record.os_info?.toLowerCase().includes('android') || record.os_info?.toLowerCase().includes('ios') ? (
                          <Smartphone className="w-4 h-4 text-gray-400" />
                        ) : (
                          <Laptop className="w-4 h-4 text-gray-400" />
                        )}
                        <span>{record.browser_info || 'متصفح غير محدد'}</span>
                        <span className="text-xs text-gray-400">({record.os_info || 'نظام غير محدد'})</span>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      {record.is_success ? (
                        <span className="inline-flex items-center gap-1.5 px-3 py-1 text-xs font-semibold rounded-full bg-emerald-50 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800">
                          <ShieldCheck className="w-3.5 h-3.5" />
                          دخول ناجح
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1.5 px-3 py-1 text-xs font-semibold rounded-full bg-red-50 dark:bg-red-900/30 text-red-700 dark:text-red-300 border border-red-200 dark:border-red-800">
                          <ShieldAlert className="w-3.5 h-3.5" />
                          محاولة فاشلة
                        </span>
                      )}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                      {record.failure_reason || (record.is_success ? 'تم تسجيل الدخول بنجاح' : '-')}
                    </td>
                  </motion.tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
};
