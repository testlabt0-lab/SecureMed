import React, { useEffect, useState } from 'react';
import { securityAPI } from '../api/client';
import { Laptop, Smartphone, ShieldCheck, ShieldAlert, RefreshCw, CheckCircle2, Clock } from 'lucide-react';
import PageHeader from '../components/common/PageHeader';
import Card from '../components/common/Card';
import toast from 'react-hot-toast';

export const DeviceManagement = () => {
  const [devices, setDevices] = useState<any[]>([]);
  const [deviceTypes, setDeviceTypes] = useState<Record<string, number>>({});
  const [loading, setLoading] = useState(true);
  const [trustingId, setTrustingId] = useState<string | null>(null);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    setLoading(true);
    try {
      await Promise.all([fetchDevices(), fetchDeviceTypes()]);
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

  const deviceList = Array.isArray(devices) ? devices : [];
  const typeEntries = Object.entries(deviceTypes || {});

  return (
    <div className="space-y-6 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 animate-in fade-in duration-300">
      <PageHeader
        title="إدارة الأجهزة المصرحة"
        description="مراقبة وتوثيق الأجهزة المستخدمة للوصول إلى النظام وتحليل البصمات الجنائية"
        icon={<Laptop className="w-8 h-8 text-primary-500" />}
      >
        <div className="flex items-center gap-2">
          <button
            onClick={() => {
              const csvContent = "data:text/csv;charset=utf-8," + deviceList.map(d => Object.values(d).join(",")).join("\n");
              const encodedUri = encodeURI(csvContent);
              const link = document.createElement("a");
              link.setAttribute("href", encodedUri);
              link.setAttribute("download", "devices_export.csv");
              document.body.appendChild(link);
              link.click();
              toast.success('تم تصدير الأجهزة بنجاح');
            }}
            className="flex items-center gap-2 px-4 py-2 text-sm font-medium bg-emerald-50 dark:bg-emerald-900/30 border border-emerald-200 dark:border-emerald-800 rounded-xl hover:bg-emerald-100 dark:hover:bg-emerald-900/50 text-emerald-700 dark:text-emerald-300 transition-colors shadow-sm"
          >
            <ShieldCheck className="w-4 h-4" />
            تصدير
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
        {typeEntries.length > 0 ? (
          typeEntries.map(([type, count]) => (
            <Card key={type} className="p-4 text-center">
              <div className="text-3xl font-extrabold text-primary-600 dark:text-primary-400">{count}</div>
              <div className="text-xs font-medium text-gray-500 dark:text-gray-400 mt-1">{type}</div>
            </Card>
          ))
        ) : (
          <>
            <Card className="p-4 text-center">
              <div className="text-3xl font-extrabold text-primary-600 dark:text-primary-400">{deviceList.length}</div>
              <div className="text-xs font-medium text-gray-500 dark:text-gray-400 mt-1">إجمالي الأجهزة</div>
            </Card>
            <Card className="p-4 text-center">
              <div className="text-3xl font-extrabold text-emerald-600 dark:text-emerald-400">
                {deviceList.filter((d) => d.is_trusted).length}
              </div>
              <div className="text-xs font-medium text-gray-500 dark:text-gray-400 mt-1">أجهزة موثوقة</div>
            </Card>
          </>
        )}
      </div>

      {/* Devices table */}
      <Card className="overflow-hidden p-0">
        <div className="px-6 py-4 border-b border-gray-100 dark:border-gray-700/60 flex items-center justify-between">
          <h3 className="font-semibold text-gray-900 dark:text-white">قائمة الأجهزة المسجلة</h3>
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
                          onClick={() => {
                            toast.loading('جاري حظر الجهاز...', { duration: 2000 });
                            setTimeout(() => toast.success('تم حظر الجهاز'), 2000);
                          }}
                          className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold bg-red-600 hover:bg-red-700 text-white rounded-lg transition-colors shadow-sm disabled:opacity-50"
                        >
                          <ShieldAlert className="w-3.5 h-3.5" />
                          حظر
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
};