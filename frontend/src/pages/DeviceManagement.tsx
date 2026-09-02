import React, { useEffect, useState } from 'react';
import { securityAPI } from '../api/client';

export const DeviceManagement = () => {
  const [devices, setDevices] = useState<any[]>([]);
  const [deviceTypes, setDeviceTypes] = useState<Record<string, number>>({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchDevices();
    fetchDeviceTypes();
  }, []);

  const fetchDevices = async () => {
    try {
      const response = await securityAPI.devices.list();
      setDevices(response.data);
    } catch (error) {
      console.error('Error fetching devices:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchDeviceTypes = async () => {
    try {
      const response = await securityAPI.deviceTypes.list();
      setDeviceTypes(response.data);
    } catch (error) {
      console.error('Error fetching device types:', error);
    }
  };

  const trustDevice = async (id: string) => {
    try {
      await securityAPI.devices.trust(id);
      fetchDevices();
    } catch (error) {
      console.error('Error trusting device:', error);
    }
  };

  if (loading) return <div className="p-4 text-center">جاري التحميل...</div>;

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold text-gray-800 mb-6">إدارة الأجهزة</h1>
      
      <div className="bg-white shadow rounded-lg overflow-hidden mb-6">
        <h2 className="text-xl font-medium text-gray-700 px-6 py-3">إحصائيات الأجهزة</h2>
        <div className="p-6 grid grid-cols-2 md:grid-cols-4 gap-4">
          {Object.entries(deviceTypes).map(([type, count]) => (
            <div key={type} className="bg-gray-50 rounded-lg p-4 text-center">
              <div className="text-3xl font-bold text-primary-600">{count}</div>
              <div className="text-sm text-gray-500 mt-1">{type}</div>
            </div>
          ))}
        </div>
      </div>
      
      <div className="bg-white shadow rounded-lg overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">الجهاز</th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">نظام التشغيل</th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">المتصفح</th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">IP الأخير</th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">الحالة</th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">إجراءات</th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {devices.map((device) => (
              <tr key={device.id}>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{device.mac_address || 'غير متوفر'}</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{device.os_info}</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{device.browser_info}</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{device.last_ip_address}</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm">
                  {device.is_trusted ? (
                    <span className="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-green-100 text-green-800">
                      موثوق
                    </span>
                  ) : (
                    <span className="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-yellow-100 text-yellow-800">
                      غير موثوق
                    </span>
                  )}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-left">
                  {!device.is_trusted && (
                    <button
                      onClick={() => trustDevice(device.id)}
                      className="text-indigo-600 hover:text-indigo-900 ml-4"
                    >
                      تعيين كموثوق
                    </button>
                  )}
                </td>
              </tr>
            ))}
            {devices.length === 0 && (
              <tr>
                <td colSpan={6} className="px-6 py-4 text-center text-sm text-gray-500">
                  لا توجد أجهزة مسجلة
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};