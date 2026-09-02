import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { ScrollText, Filter, Search, FileSpreadsheet, Download, ShieldAlert, ChevronDown, ChevronUp } from 'lucide-react';
import { auditAPI } from '../api/client';
import api from '../api/client';
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
  DATA_EXPORT: 'تصدير بيانات (SIEM)',
};

const severityColors: Record<string, string> = {
  INFO: 'badge-info',
  WARNING: 'badge-warning',
  CRITICAL: 'badge-danger',
};

function AuditRow({ log }: { log: any }) {
  const [expanded, setExpanded] = useState(false);
  const [blocking, setBlocking] = useState(false);

  const handleBlockDevice = async () => {
    if (!log.device_fingerprint && !log.mac_address) {
      toast.error('لا يوجد معلومات كافية عن الجهاز لحظره');
      return;
    }
    setBlocking(true);
    const toastId = toast.loading('جاري حظر الجهاز...');
    try {
      await api.post('/security/blocked-devices/', {
        device_fingerprint: log.device_fingerprint || '',
        mac_address: log.mac_address || '',
        reason: `محظور من سجلات التدقيق (نشاط مشبوه)`
      });
      toast.success('تم حظر الجهاز وإضافته للقائمة السوداء بنجاح', { id: toastId });
    } catch (err) {
      toast.error('فشل حظر الجهاز، قد يكون محظوراً بالفعل', { id: toastId });
    } finally {
      setBlocking(false);
    }
  };

  return (
    <>
      <tr className={`border-b border-gray-100 hover:bg-gray-50 transition-colors ${expanded ? 'bg-gray-50' : ''}`}>
        <td className="py-3 pr-4 text-sm text-gray-600">
          <button onClick={() => setExpanded(!expanded)} className="p-1 rounded hover:bg-gray-200 mr-1 text-gray-500 transition-colors">
            {expanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
          </button>
          {new Date(log.timestamp).toLocaleString('ar-SA')}
        </td>
        <td className="text-sm">
          {log.user_name || '—'}
          {log.user_email && <p className="text-xs text-gray-400">{log.user_email}</p>}
        </td>
        <td className="text-sm">
          <span className="font-medium">{log.event_type_display || eventTypeLabels[log.event_type] || log.event_type}</span>
        </td>
        <td>
          <span className={`badge ${severityColors[log.severity] || 'badge-gray'}`}>
            {log.severity_display || log.severity}
          </span>
        </td>
        <td className="text-sm font-mono">{log.ip_address || '—'}</td>
        <td className="text-sm">
          <span className="font-mono text-xs">{log.method} {log.path}</span>
        </td>
      </tr>
      
      {expanded && (
        <tr className="bg-gray-50/50 border-b border-gray-200">
          <td colSpan={6} className="py-4 px-8">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 bg-white p-4 rounded-xl shadow-sm border border-gray-100">
              <div>
                <h4 className="text-sm font-semibold text-gray-700 mb-2 border-b pb-1">معلومات الجهاز (DevSecOps)</h4>
                <ul className="text-sm space-y-2 text-gray-600">
                  <li><span className="font-medium">MAC Address:</span> <span className="font-mono text-xs bg-gray-100 px-1 rounded">{log.mac_address || 'غير متوفر'}</span></li>
                  <li><span className="font-medium">بصمة الجهاز (Fingerprint):</span> <span className="font-mono text-xs truncate max-w-[200px] inline-block align-bottom">{log.device_fingerprint || 'غير متوفر'}</span></li>
                  <li><span className="font-medium">نظام التشغيل:</span> {log.os_info || 'غير متوفر'}</li>
                  <li><span className="font-medium">المتصفح:</span> {log.browser_info || 'غير متوفر'}</li>
                  <li><span className="font-medium">معرف الجلسة:</span> <span className="font-mono text-xs">{log.session_id || '—'}</span></li>
                </ul>
              </div>
              <div>
                <h4 className="text-sm font-semibold text-gray-700 mb-2 border-b pb-1">تحليل المخاطر</h4>
                <ul className="text-sm space-y-2 text-gray-600">
                  <li><span className="font-medium">درجة الخطورة:</span> <span className={`font-bold ${log.risk_score > 50 ? 'text-red-500' : 'text-green-500'}`}>{log.risk_score || 0}%</span></li>
                  <li><span className="font-medium">الموقع الجغرافي:</span> {log.geo_location || 'غير معروف'}</li>
                  <li><span className="font-medium">User Agent:</span> <span className="text-xs text-gray-400 line-clamp-1" title={log.user_agent}>{log.user_agent || '—'}</span></li>
                </ul>
                <div className="mt-4 pt-3 border-t">
                  <button 
                    onClick={handleBlockDevice}
                    disabled={blocking || (!log.device_fingerprint && !log.mac_address)}
                    className="btn-danger w-full sm:w-auto text-sm py-1.5 px-3 flex items-center justify-center gap-1.5"
                  >
                    <ShieldAlert className="w-4 h-4" />
                    {blocking ? 'جاري الحظر...' : 'حظر هذا الجهاز (Blocklist)'}
                  </button>
                </div>
              </div>
            </div>
          </td>
        </tr>
      )}
    </>
  );
}

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
      toast.error('فشل التصدير', { id: toastId });
    } finally {
      setExporting(false);
    }
  };

  const handleExportSIEM = async () => {
    setExporting(true);
    const toastId = toast.loading('جاري التصدير بصيغة JSON لبيئات SIEM...');
    try {
      const response = await reportsApi.auditJson({
        event_type: eventType || undefined,
        severity: severity || undefined,
      });
      downloadBlobResponse(response, 'SIEM_Audit_Export.json');
      toast.success('تم تصدير السجلات لـ SIEM بنجاح', { id: toastId });
    } catch (err: any) {
      toast.error('فشل تصدير SIEM', { id: toastId });
    } finally {
      setExporting(false);
    }
  };

  const { data: logsData, isLoading, refetch } = useQuery({
    queryKey: ['audit-logs', { search, eventType, severity }],
    queryFn: () => auditAPI.list({ search, event_type: eventType, severity }),
  });

  const logs = Array.isArray(logsData?.data?.results) ? logsData.data.results : (Array.isArray(logsData?.data) ? logsData.data : []);

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <ScrollText className="w-6 h-6 text-primary-600" />
            سجلات التدقيق الأمني (SIEM)
          </h1>
          <p className="text-gray-600 text-sm mt-1">
            مراقبة شاملة للنشاطات وتتبع الأجهزة (MAC/Fingerprint)
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={handleExportExcel}
            disabled={exporting}
            className="btn-secondary text-sm flex items-center gap-2"
          >
            <FileSpreadsheet className="w-4 h-4 text-green-600" />
            تصدير Excel
          </button>
          <button
            onClick={handleExportSIEM}
            disabled={exporting}
            className="btn-primary text-sm flex items-center gap-2"
          >
            <Download className="w-4 h-4" />
            تصدير SIEM (JSON)
          </button>
        </div>
      </div>

      <div className="card">
        <div className="flex flex-col md:flex-row gap-3 mb-4">
          <div className="relative flex-1">
            <Search className="absolute right-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="بحث بـ IP أو MAC أو مسار..."
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
          <div className="overflow-x-auto rounded-xl border border-gray-100">
            <table className="w-full">
              <thead className="bg-gray-50">
                <tr className="border-b border-gray-200 text-right text-sm text-gray-500">
                  <th className="py-3 pr-4 font-medium">الوقت</th>
                  <th className="py-3 font-medium">المستخدم</th>
                  <th className="py-3 font-medium">الحدث</th>
                  <th className="py-3 font-medium">المستوى</th>
                  <th className="py-3 font-medium">IP Address</th>
                  <th className="py-3 font-medium">المسار</th>
                </tr>
              </thead>
              <tbody>
                {logs.map((log: any) => (
                  <AuditRow key={log.id} log={log} />
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
