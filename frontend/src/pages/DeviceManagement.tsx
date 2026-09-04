import React, { useEffect, useState } from 'react';
import { securityAPI } from '../api/client';
import { Laptop, Smartphone, ShieldCheck, ShieldAlert, RefreshCw, CheckCircle2, Ban, Unlock, Download, Network } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import PageHeader from '../components/common/PageHeader';
import Card from '../components/common/Card';
import toast from 'react-hot-toast';

export const DeviceManagement = () => {
  const [activeTab, setActiveTab] = useState<'registered' | 'blocked' | 'ips'>('registered');
  const [devices, setDevices] = useState<any[]>([]);
  const [blockedDevices, setBlockedDevices] = useState<any[]>([]);
  const [blockedIps, setBlockedIps] = useState<any[]>([]);
  const [deviceTypes, setDeviceTypes] = useState<Record<string, number>>({});
  const [loading, setLoading] = useState(true);
  const [trustingId, setTrustingId] = useState<string | null>(null);
  const [blockingId, setBlockingId] = useState<string | null>(null);
  const [unblockingId, setUnblockingId] = useState<string | null>(null);
  const [ipInput, setIpInput] = useState('');
  const [ipReason, setIpReason] = useState('');

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    setLoading(true);
    try {
      await Promise.all([fetchDevices(), fetchDeviceTypes(), fetchBlockedDevices(), fetchBlockedIps()]);
    } finally {
      setLoading(false);
    }
  };

  const fetchDevices = async () => {
    try {
      const response = await securityAPI.devices.list();
      const data = response?.data;
      const list = Array.isArray(data) ? data : (Array.isArray(data?.results) ? data.results : []);
      setDevices(list);
    } catch (error) {
      console.error('Error fetching devices:', error);
      setDevices([]);
    }
  };

  const fetchBlockedDevices = async () => {
    try {
      const response = await securityAPI.blockedDevices.list();
      const data = response?.data;
      const list = Array.isArray(data) ? data : (Array.isArray(data?.results) ? data.results : []);
      setBlockedDevices(list);
    } catch (error) {
      console.error('Error fetching blocked devices:', error);
      setBlockedDevices([]);
    }
  };

  const fetchDeviceTypes = async () => {
    try {
      const response = await securityAPI.deviceTypes.list();
      const data = response?.data;
      const types = data && typeof data === 'object' && !Array.isArray(data) ? data : {};
      setDeviceTypes(types);
    } catch (error) {
      console.error('Error fetching device types:', error);
      setDeviceTypes({});
    }
  };

  const trustDevice = async (id: string) => {
    setTrustingId(id);
    const toastId = toast.loading('جاري توثيق الجهاز...');
    try {
      await securityAPI.devices.trust(id);
      toast.success('تم تعيين الجهاز كموثوق بنجاح', { id: toastId });
      await fetchDevices();
    } catch (error) {
      toast.error('فشل توثيق الجهاز', { id: toastId });
      console.error('Error trusting device:', error);
    } finally {
      setTrustingId(null);
    }
  };

  const blockDevice = async (device: any) => {
    const fingerprint = device.device_fingerprint || '';
    const mac = device.mac_address || '';
    if (!fingerprint && !mac) {
      toast.error('لا تتوفر معلومات كافية لحظر هذا الجهاز');
      return;
    }

    if (!confirm(`هل أنت متأكد من رغبتك في حظر هذا الجهاز وإضافته للقائمة السوداء؟`)) {
      return;
    }

    setBlockingId(device.id);
    const toastId = toast.loading('جاري حظر الجهاز وإضافته للقائمة السوداء...');
    try {
      await securityAPI.blockedDevices.create({
        device_fingerprint: fingerprint,
        mac_address: mac,
        reason: `حظر أمني من لوحة التحكم بواسطة المسؤول (${device.hostname || 'جهاز بدون اسم'})`,
        is_active: true,
      });
      toast.success('تم حظر الجهاز وإضافته للقائمة السوداء بنجاح', { id: toastId });
      await Promise.all([fetchDevices(), fetchBlockedDevices()]);
    } catch (error: any) {
      const msg = error.response?.data?.detail || 'فشل حظر الجهاز، قد يكون محظوراً مسبقاً';
      toast.error(msg, { id: toastId });
    } finally {
      setBlockingId(null);
    }
  };

  const unblockDevice = async (id: string) => {
    setUnblockingId(id);
    const toastId = toast.loading('جاري إلغاء حظر الجهاز...');
    try {
      await securityAPI.blockedDevices.unblock(id);
      toast.success('تم إلغاء حظر الجهاز بنجاح', { id: toastId });
      await Promise.all([fetchDevices(), fetchBlockedDevices()]);
    } catch (error: any) {
      toast.error('فشل إلغاء الحظر', { id: toastId });
    } finally {
      setUnblockingId(null);
    }
  };

  const fetchBlockedIps = async () => {
    try {
      const response = await securityAPI.blockedIps.list();
      const data = response?.data;
      const list = Array.isArray(data) ? data : (Array.isArray(data?.results) ? data.results : []);
      setBlockedIps(list);
    } catch (error) {
      console.error('Error fetching blocked IPs:', error);
      setBlockedIps([]);
    }
  };

  const blockIp = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!ipInput.trim()) return toast.error('يرجى إدخال عنوان IP');
    const toastId = toast.loading('جاري حظر IP...');
    try {
      await securityAPI.blockedIps.create({
        ip_address: ipInput.trim(),
        reason: ipReason.trim() || 'حظر يدوي',
        is_active: true
      });
      toast.success('تم حظر الـ IP بنجاح', { id: toastId });
      setIpInput('');
      setIpReason('');
      await fetchBlockedIps();
    } catch (error: any) {
      const msg = error.response?.data?.detail || error.response?.data?.ip_address?.[0] || 'فشل الحظر';
      toast.error(msg, { id: toastId });
    }
  };

  const unblockIp = async (id: string) => {
    setUnblockingId(id);
    const toastId = toast.loading('جاري إلغاء الحظر...');
    try {
      await securityAPI.blockedIps.unblock(id);
      toast.success('تم إلغاء الحظر بنجاح', { id: toastId });
      await fetchBlockedIps();
    } catch (error: any) {
      toast.error('فشل إلغاء الحظر', { id: toastId });
    } finally {
      setUnblockingId(null);
    }
  };

  const deviceList = Array.isArray(devices) ? devices : [];
  const blockedList = Array.isArray(blockedDevices) ? blockedDevices : [];
  const typeEntries = Object.entries(deviceTypes || {});

  return (
    <div className="space-y-6 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 animate-in fade-in duration-300">
      <PageHeader
        title="إدارة الأجهزة المصرحة"
        description="مراقبة وتوثيق الأجهزة المستخدمة للوصول إلى النظام وإدارة القائمة السوداء للأجهزة"
        icon={<Laptop className="w-8 h-8 text-primary-500" />}
      >
        <div className="flex items-center gap-2">
          <button
            onClick={() => {
              const exportSource = activeTab === 'registered' ? deviceList : blockedList;
              if (exportSource.length === 0) {
                toast.error('لا توجد بيانات لتصديرها');
                return;
              }
              const keys = Object.keys(exportSource[0]);
              const csvContent = "data:text/csv;charset=utf-8," + 
                [keys.join(','), ...exportSource.map(d => keys.map(k => `"${d[k] ?? ''}"`).join(','))].join("\n");
              const encodedUri = encodeURI(csvContent);
              const link = document.createElement("a");
              link.setAttribute("href", encodedUri);
              link.setAttribute("download", `${activeTab === 'registered' ? 'registered_devices' : 'blocked_devices'}_export.csv`);
              document.body.appendChild(link);
              link.click();
              toast.success('تم تصدير ملف CSV بنجاح');
            }}
            className="flex items-center gap-2 px-4 py-2 text-sm font-medium bg-emerald-50 dark:bg-emerald-900/30 border border-emerald-200 dark:border-emerald-800 rounded-xl hover:bg-emerald-100 dark:hover:bg-emerald-900/50 text-emerald-700 dark:text-emerald-300 transition-colors shadow-sm"
          >
            <Download className="w-4 h-4" />
            تصدير CSV
          </button>
          <button
            onClick={fetchData}
            disabled={loading}
            className="flex items-center gap-2 px-4 py-2 text-sm font-medium bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl hover:bg-gray-50 dark:hover:bg-gray-700/50 text-gray-700 dark:text-gray-200 transition-colors shadow-sm"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin text-primary-500' : ''}`} />
            تحديث
          </button>
        </div>
      </PageHeader>

      {/* Device statistics */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <Card className="p-4 text-center">
          <div className="text-3xl font-extrabold text-primary-600 dark:text-primary-400">{deviceList.length}</div>
          <div className="text-xs font-medium text-gray-500 dark:text-gray-400 mt-1">إجمالي الأجهزة المسجلة</div>
        </Card>
        <Card className="p-4 text-center">
          <div className="text-3xl font-extrabold text-emerald-600 dark:text-emerald-400">
            {deviceList.filter((d) => d.is_trusted).length}
          </div>
          <div className="text-xs font-medium text-gray-500 dark:text-gray-400 mt-1">أجهزة موثوقة</div>
        </Card>
        <Card className="p-4 text-center">
          <div className="text-3xl font-extrabold text-amber-600 dark:text-amber-400">
            {deviceList.filter((d) => !d.is_trusted).length}
          </div>
          <div className="text-xs font-medium text-gray-500 dark:text-gray-400 mt-1">أجهزة قيد المراجعة</div>
        </Card>
        <Card className="p-4 text-center">
          <div className="text-3xl font-extrabold text-red-600 dark:text-red-400">
            {blockedList.filter((d) => d.is_active !== false).length}
          </div>
          <div className="text-xs font-medium text-gray-500 dark:text-gray-400 mt-1">أجهزة محظورة (Blacklist)</div>
        </Card>
      </div>

      {/* Tab Navigation */}
      <div className="flex border-b border-gray-200 dark:border-gray-700">
        <button
          onClick={() => setActiveTab('registered')}
          className={`pb-3 px-4 text-sm font-semibold flex items-center gap-2 border-b-2 transition-all ${
            activeTab === 'registered'
              ? 'border-primary-600 text-primary-600 dark:text-primary-400'
              : 'border-transparent text-gray-500 hover:text-gray-700 dark:hover:text-gray-300'
          }`}
        >
          <Laptop className="w-4 h-4" />
          الأجهزة المسجلة ({deviceList.length})
        </button>
        <button
          onClick={() => setActiveTab('blocked')}
          className={`pb-3 px-4 text-sm font-semibold flex items-center gap-2 border-b-2 transition-all ${
            activeTab === 'blocked'
              ? 'border-red-600 text-red-600 dark:text-red-400'
              : 'border-transparent text-gray-500 hover:text-gray-700 dark:hover:text-gray-300'
          }`}
        >
          <Ban className="w-4 h-4" />
          القائمة السوداء للأجهزة ({blockedList.length})
        </button>
        <button
          onClick={() => setActiveTab('ips')}
          className={`pb-3 px-4 text-sm font-semibold flex items-center gap-2 border-b-2 transition-all ${
            activeTab === 'ips'
              ? 'border-indigo-600 text-indigo-600 dark:text-indigo-400'
              : 'border-transparent text-gray-500 hover:text-gray-700 dark:hover:text-gray-300'
          }`}
        >
          <Network className="w-4 h-4" />
          حظر الـ IPs ({blockedIps.length})
        </button>
      </div>

      {/* Devices table */}
      <Card className="overflow-hidden p-0">
        <AnimatePresence mode="wait">
          {activeTab === 'registered' ? (
            <motion.div
              key="registered"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.2 }}
            >
              <div className="px-6 py-4 border-b border-gray-100 dark:border-gray-700/60 flex items-center justify-between">
                <h3 className="font-semibold text-gray-900 dark:text-white">قائمة الأجهزة المسجلة والنشطة</h3>
                <span className="text-xs bg-primary-50 dark:bg-primary-900/30 text-primary-700 dark:text-primary-300 font-semibold px-2.5 py-1 rounded-full">
                  {deviceList.length} جهاز
                </span>
              </div>

              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700/60">
                  <thead className="bg-gray-50/50 dark:bg-gray-900/30">
                    <tr>
                      <th className="px-6 py-3 text-right text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">الجهاز</th>
                      <th className="px-6 py-3 text-right text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">نظام التشغيل</th>
                      <th className="px-6 py-3 text-right text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">المتصفح</th>
                      <th className="px-6 py-3 text-right text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">آخر IP</th>
                      <th className="px-6 py-3 text-right text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">الحالة</th>
                      <th className="px-6 py-3 text-right text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">الإجراءات</th>
                    </tr>
                  </thead>
                  <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-100 dark:divide-gray-700/40">
                    {loading ? (
                      <tr>
                        <td colSpan={6} className="px-6 py-12 text-center text-gray-500">
                          <RefreshCw className="w-6 h-6 animate-spin mx-auto mb-2 text-primary-500" />
                          جاري تحميل الأجهزة...
                        </td>
                      </tr>
                    ) : deviceList.length === 0 ? (
                      <tr>
                        <td colSpan={6} className="px-6 py-12 text-center text-gray-500 dark:text-gray-400">
                          <Laptop className="w-10 h-10 mx-auto mb-2 opacity-30" />
                          لا توجد أجهزة مسجلة في الوقت الحالي
                        </td>
                      </tr>
                    ) : (
                      deviceList.map((device: any) => (
                        <tr key={device.id} className="hover:bg-gray-50/50 dark:hover:bg-gray-700/30 transition-colors">
                          <td className="px-6 py-4 whitespace-nowrap">
                            <div className="flex items-center gap-3">
                              <div className="p-2 bg-gray-100 dark:bg-gray-700 rounded-xl text-gray-600 dark:text-gray-300">
                                {device.os_info?.toLowerCase().includes('android') || device.os_info?.toLowerCase().includes('ios') ? (
                                  <Smartphone className="w-4 h-4" />
                                ) : (
                                  <Laptop className="w-4 h-4" />
                                )}
                              </div>
                              <div>
                                <div className="text-sm font-semibold text-gray-900 dark:text-white font-mono">
                                  {device.mac_address || device.device_fingerprint?.substring(0, 16) || 'غير متوفر'}
                                </div>
                                <div className="text-xs text-gray-400">{device.hostname || 'جهاز غير مسمى'}</div>
                              </div>
                            </div>
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600 dark:text-gray-300">
                            {device.os_info || 'غير معروف'}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600 dark:text-gray-300">
                            {device.browser_info || 'غير معروف'}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm font-mono text-gray-500 dark:text-gray-400">
                            {device.last_ip_address || '127.0.0.1'}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap">
                            {device.is_trusted ? (
                              <span className="inline-flex items-center gap-1.5 px-3 py-1 text-xs font-semibold rounded-full bg-emerald-50 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800">
                                <ShieldCheck className="w-3.5 h-3.5" />
                                موثوق
                              </span>
                            ) : (
                              <span className="inline-flex items-center gap-1.5 px-3 py-1 text-xs font-semibold rounded-full bg-amber-50 dark:bg-amber-900/30 text-amber-700 dark:text-amber-300 border border-amber-200 dark:border-amber-800">
                                <ShieldAlert className="w-3.5 h-3.5" />
                                غير موثوق
                              </span>
                            )}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                            <div className="flex items-center gap-2">
                              {!device.is_trusted && (
                                <button
                                  onClick={() => trustDevice(device.id)}
                                  disabled={trustingId === device.id}
                                  className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg transition-colors shadow-sm disabled:opacity-50"
                                >
                                  <CheckCircle2 className="w-3.5 h-3.5" />
                                  توثيق
                                </button>
                              )}
                              <button
                                onClick={() => blockDevice(device)}
                                disabled={blockingId === device.id}
                                className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold bg-red-600 hover:bg-red-700 text-white rounded-lg transition-colors shadow-sm disabled:opacity-50"
                              >
                                <Ban className="w-3.5 h-3.5" />
                                {blockingId === device.id ? 'جاري الحظر...' : 'حظر'}
                              </button>
                            </div>
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </motion.div>
          ) : activeTab === 'blocked' ? (
            <motion.div
              key="blocked"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.2 }}
            >
              <div className="px-6 py-4 border-b border-gray-100 dark:border-gray-700/60 flex items-center justify-between">
                <h3 className="font-semibold text-gray-900 dark:text-white">الأجهزة المحظورة في القائمة السوداء</h3>
                <span className="text-xs bg-red-50 dark:bg-red-900/30 text-red-700 dark:text-red-300 font-semibold px-2.5 py-1 rounded-full">
                  {blockedList.length} جهاز محظور
                </span>
              </div>

              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700/60">
                  <thead className="bg-gray-50/50 dark:bg-gray-900/30">
                    <tr>
                      <th className="px-6 py-3 text-right text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">بصمة الجهاز / MAC</th>
                      <th className="px-6 py-3 text-right text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">سبب الحظر</th>
                      <th className="px-6 py-3 text-right text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">تاريخ الحظر</th>
                      <th className="px-6 py-3 text-right text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">الحالة</th>
                      <th className="px-6 py-3 text-right text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">الإجراءات</th>
                    </tr>
                  </thead>
                  <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-100 dark:divide-gray-700/40">
                    {loading ? (
                      <tr>
                        <td colSpan={5} className="px-6 py-12 text-center text-gray-500">
                          <RefreshCw className="w-6 h-6 animate-spin mx-auto mb-2 text-primary-500" />
                          جاري تحميل الأجهزة المحظورة...
                        </td>
                      </tr>
                    ) : blockedList.length === 0 ? (
                      <tr>
                        <td colSpan={5} className="px-6 py-12 text-center text-gray-500 dark:text-gray-400">
                          <ShieldCheck className="w-10 h-10 mx-auto mb-2 text-emerald-500 opacity-60" />
                          القائمة السوداء نظيفة، لا توجد أجهزة محظورة
                        </td>
                      </tr>
                    ) : (
                      blockedList.map((blocked: any) => (
                        <tr key={blocked.id} className="hover:bg-gray-50/50 dark:hover:bg-gray-700/30 transition-colors">
                          <td className="px-6 py-4 whitespace-nowrap">
                            <div className="font-mono text-xs font-bold text-red-600 dark:text-red-400">
                              {blocked.mac_address || blocked.device_fingerprint?.substring(0, 24) || '—'}
                            </div>
                          </td>
                          <td className="px-6 py-4 text-sm text-gray-700 dark:text-gray-300">
                            {blocked.reason || 'حظر يدوي'}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-xs text-gray-500">
                            {blocked.created_at ? new Date(blocked.created_at).toLocaleString('ar-SA') : '—'}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap">
                            {blocked.is_active !== false ? (
                              <span className="inline-flex items-center gap-1.5 px-3 py-1 text-xs font-semibold rounded-full bg-red-50 dark:bg-red-900/30 text-red-700 dark:text-red-300 border border-red-200 dark:border-red-800">
                                <Ban className="w-3.5 h-3.5" />
                                محظور حالياً
                              </span>
                            ) : (
                              <span className="inline-flex items-center gap-1.5 px-3 py-1 text-xs font-semibold rounded-full bg-gray-50 dark:bg-gray-800 text-gray-600 dark:text-gray-400 border border-gray-200 dark:border-gray-700">
                                غير نشط
                              </span>
                            )}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                            <button
                              onClick={() => unblockDevice(blocked.id)}
                              disabled={unblockingId === blocked.id}
                              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg transition-colors shadow-sm disabled:opacity-50"
                            >
                              <Unlock className="w-3.5 h-3.5" />
                              {unblockingId === blocked.id ? 'جاري الإلغاء...' : 'إلغاء الحظر'}
                            </button>
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </motion.div>
          ) : (
            <motion.div
              key="ips"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.2 }}
              className="p-6"
            >
              <div className="mb-8 p-6 bg-gray-50 dark:bg-gray-900/50 rounded-xl border border-gray-200 dark:border-gray-700">
                <h4 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">حظر عنوان IP جديد</h4>
                <form onSubmit={blockIp} className="flex flex-col md:flex-row gap-4 items-end">
                  <div className="flex-1 w-full">
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">عنوان IP</label>
                    <input
                      type="text"
                      required
                      placeholder="مثال: 192.168.1.100"
                      value={ipInput}
                      onChange={(e) => setIpInput(e.target.value)}
                      className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-primary-500 dark:bg-gray-800 dark:border-gray-700 dark:text-white"
                    />
                  </div>
                  <div className="flex-1 w-full">
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">سبب الحظر (اختياري)</label>
                    <input
                      type="text"
                      placeholder="مثال: محاولات اختراق متكررة"
                      value={ipReason}
                      onChange={(e) => setIpReason(e.target.value)}
                      className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-primary-500 dark:bg-gray-800 dark:border-gray-700 dark:text-white"
                    />
                  </div>
                  <button type="submit" className="w-full md:w-auto px-6 py-2.5 bg-red-600 text-white rounded-lg hover:bg-red-700 font-semibold shadow-sm transition-colors">
                    إضافة للقائمة السوداء
                  </button>
                </form>
              </div>

              <div className="overflow-x-auto">
                 <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700/60">
                  <thead className="bg-gray-50/50 dark:bg-gray-900/30">
                    <tr>
                      <th className="px-6 py-3 text-right text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase">عنوان IP</th>
                      <th className="px-6 py-3 text-right text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase">السبب</th>
                      <th className="px-6 py-3 text-right text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase">تاريخ الحظر</th>
                      <th className="px-6 py-3 text-right text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase">الحالة</th>
                      <th className="px-6 py-3 text-right text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase">الإجراءات</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100 dark:divide-gray-700/40">
                    {blockedIps.length === 0 ? (
                      <tr>
                        <td colSpan={5} className="px-6 py-12 text-center text-gray-500">لا توجد عناوين IP محظورة حالياً</td>
                      </tr>
                    ) : (
                      blockedIps.map((ip: any) => (
                        <tr key={ip.id} className="hover:bg-gray-50/50 dark:hover:bg-gray-700/30">
                          <td className="px-6 py-4 font-mono font-bold text-red-600 dark:text-red-400">{ip.ip_address}</td>
                          <td className="px-6 py-4 text-sm dark:text-gray-300">{ip.reason || 'حظر يدوي'}</td>
                          <td className="px-6 py-4 text-xs text-gray-500">{new Date(ip.created_at).toLocaleString('ar-SA')}</td>
                          <td className="px-6 py-4">
                              {ip.is_active ? 
                                <span className="text-xs bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300 px-3 py-1 rounded-full font-semibold">محظور</span> : 
                                <span className="text-xs bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400 px-3 py-1 rounded-full font-semibold">غير نشط</span>
                              }
                          </td>
                          <td className="px-6 py-4">
                            <button 
                              onClick={() => unblockIp(ip.id)} 
                              disabled={unblockingId === ip.id}
                              className="text-xs font-semibold bg-indigo-600 text-white px-3 py-1.5 rounded-lg hover:bg-indigo-700 disabled:opacity-50 flex items-center gap-1.5 shadow-sm"
                            >
                              <Unlock className="w-3.5 h-3.5" />
                              إلغاء الحظر
                            </button>
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                 </table>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </Card>
    </div>
  );
};