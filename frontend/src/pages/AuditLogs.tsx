import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { ScrollText, Filter, Search, FileSpreadsheet } from 'lucide-react';
import { auditAPI } from '../api/client';
import { reportsApi, downloadBlobResponse } from '../api/extendedApis';
import toast from 'react-hot-toast';

const eventTypeLabels: Record<string, string> = {
  LOGIN_SUCCESS: 'تسجيل دخول ناجح',
  LOGIN_FAILED: 'فشل تسجيل الدخول',
  LOGOUT: 'تسجيل خروج',
  BIOMETRIC_LOGIN_SUCCESS: 'دخول بيوميتري ناجح',
  BIOMETRIC_ENROLLMENT: 'تسجيل بصمة',
  BIOMETRIC_CHALLENGE_REQUESTED: 'طلب تحدي بيوميتري',
  BIOMETRIC_REVOKED: 'إلغاء بصمة',
  PASSWORD_CHANGED: 'تغيير كلمة المرور',
  PERMISSION_GRANTED: 'منح صلاحية',
  PERMISSION_MODIFIED: 'تعديل صلاحية',
  PERMISSION_REVOKED: 'سحب صلاحية',
  MEMBERSHIP_CANCELLED: 'إلغاء عضوية',
  CHANNEL_CREATED: 'إنشاء قناة',
  CHANNEL_CLOSED: 'إغلاق قناة',
  PATIENT_DATA_ACCESSED: 'الوصول لبيانات مريض',
  MEDICAL_RECORD_CREATED: 'إنشاء سجل طبي',
  PORT_SCAN_EXECUTED: 'تنفيذ مسح منافذ',
  VULN_SCAN_EXECUTED: 'تنفيذ فحص ثغرات',
  WAF_BLOCKED: 'حظر WAF',
  INVITATION_SENT: 'إرسال دعوة',
  INVITATION_ACCEPTED: 'قبول دعوة',
  INVITATION_REJECTED: 'رفض دعوة',
  USER_DEACTIVATED: 'إلغاء تفعيل مستخدم',
};

const severityColors: Record<string, string> = {
  INFO: 'badge-info',
  WARNING: 'badge-warning',
  CRITICAL: 'badge-danger',
};

export default function AuditLogs() {
  const [search, setSearch] = useState('');
  const [eventType, setEventType] = useState('');
  const [severity, setSeverity] = useState('');
  const [exporting, setExporting] = useState(false);

  const handleExportExcel = async () => {
    setExporting(true);
    const toastId = toast.loading('جاري تصدير سجل التدقيق إلى Excel...');
    try {
      const response = await reportsApi.auditExcel({
        event_type: eventType || undefined,
        severity: severity || undefined,
      });
      downloadBlobResponse(response, 'SecureMed_Audit.xlsx');
      toast.success('تم تنزيل ملف Excel', { id: toastId });
    } catch (err: any) {
      toast.error(
        err.response?.status === 403
          ? 'التصدير متاح للمدير والمراجع الأمني فقط'
          : 'فشل التصدير',
        { id: toastId },
      );
    } finally {
      setExporting(false);
    }
  };

  const { data: logsData, isLoading } = useQuery({
    queryKey: ['audit-logs', { search, eventType, severity }],
    queryFn: () => auditAPI.list({ search, event_type: eventType, severity }),
  });

  const logs = logsData?.data?.results || logsData?.data || [];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <ScrollText className="w-6 h-6 text-primary-600" />
          سجلات التدقيق الأمني
        </h1>
        <p className="text-gray-600 text-sm mt-1">
          تتبع جميع الأحداث الأمنية في النظام (متطلب HIPAA)
        </p>
      </div>

      <div className="flex justify-end">
        <button
          onClick={handleExportExcel}
          disabled={exporting}
          className="btn-secondary text-sm flex items-center gap-2"
        >
          <FileSpreadsheet className="w-4 h-4 text-green-600" />
          {exporting ? 'جاري التصدير...' : 'تصدير Excel'}
        </button>
      </div>

      <div className="card">
        <div className="flex flex-col md:flex-row gap-3 mb-4">
          <div className="relative flex-1">
            <Search className="absolute right-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="بحث في السجلات..."
              className="input-field pr-10"
            />
          </div>
          <select
            value={eventType}
            onChange={(e) => setEventType(e.target.value)}
            className="input-field md:w-56"
          >
            <option value="">كل الأحداث</option>
            {Object.entries(eventTypeLabels).map(([key, label]) => (
              <option key={key} value={key}>{label}</option>
            ))}
          </select>
          <select
            value={severity}
            onChange={(e) => setSeverity(e.target.value)}
            className="input-field md:w-40"
          >
            <option value="">كل المستويات</option>
            <option value="INFO">معلومة</option>
            <option value="WARNING">تحذير</option>
            <option value="CRITICAL">حرج</option>
          </select>
        </div>

        {isLoading ? (
          <div className="text-center py-8 text-gray-500">جاري التحميل...</div>
        ) : logs.length === 0 ? (
          <div className="text-center py-12">
            <ScrollText className="w-12 h-12 text-gray-300 mx-auto mb-3" />
            <p className="text-gray-500">لا توجد سجلات بعد</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-gray-200 text-right text-sm text-gray-500">
                  <th className="pb-3 pr-4 font-medium">الوقت</th>
                  <th className="pb-3 font-medium">المستخدم</th>
                  <th className="pb-3 font-medium">الحدث</th>
                  <th className="pb-3 font-medium">المستوى</th>
                  <th className="pb-3 font-medium">IP</th>
                  <th className="pb-3 font-medium">المسار</th>
                </tr>
              </thead>
              <tbody>
                {logs.map((log: any) => (
                  <tr key={log.id} className="border-b border-gray-100 hover:bg-gray-50">
                    <td className="py-3 pr-4 text-sm text-gray-600">
                      {new Date(log.timestamp).toLocaleString('ar-SA')}
                    </td>
                    <td className="text-sm">
                      {log.user_name || '—'}
                      {log.user_email && (
                        <p className="text-xs text-gray-400">{log.user_email}</p>
                      )}
                    </td>
                    <td className="text-sm">
                      <span className="font-medium">{log.event_type_display}</span>
                    </td>
                    <td>
                      <span className={`badge ${severityColors[log.severity]}`}>
                        {log.severity_display}
                      </span>
                    </td>
                    <td className="text-sm font-mono">{log.ip_address || '—'}</td>
                    <td className="text-sm">
                      <span className="font-mono text-xs">{log.method} {log.path}</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
