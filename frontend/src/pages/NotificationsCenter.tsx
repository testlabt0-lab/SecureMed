import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Bell, CheckCheck, Trash2, AlertCircle, Info, AlertTriangle,
  Shield, FileText, UserPlus, Fingerprint, X, Mail, Send, BarChart3
} from 'lucide-react';
import { notificationsApi, reportsApi } from '../api/extendedApis';
import { useAuthStore } from '../store/authStore';
import { useThemeStore } from '../store/themeStore';
import toast from 'react-hot-toast';

const notificationIcons: Record<string, any> = {
  CHANNEL_INVITATION: UserPlus,
  CHANNEL_UPDATE: Bell,
  CHANNEL_CLOSED: X,
  PERMISSION_GRANTED: Shield,
  PERMISSION_REVOKED: AlertTriangle,
  NEW_MEDICAL_RECORD: FileText,
  CRITICAL_PATIENT: AlertCircle,
  SECURITY_ALERT: Shield,
  BIOMETRIC_ENROLLED: Fingerprint,
  LOGIN_ALERT: Info,
  SYSTEM_ANNOUNCEMENT: Info,
};

const priorityColors: Record<string, string> = {
  LOW: 'text-blue-600',
  MEDIUM: 'text-yellow-600',
  HIGH: 'text-orange-600',
  CRITICAL: 'text-red-600',
};

export default function NotificationsCenter() {
  const queryClient = useQueryClient();
  const { theme } = useThemeStore();
  const { user } = useAuthStore();
  const isDark = theme === 'dark';

  const [filter, setFilter] = useState<'all' | 'unread' | 'critical'>('all');

  const canEmailReports = ['SUPER_ADMIN', 'HOSPITAL_ADMIN', 'AUDITOR'].includes(user?.role || '');

  const testEmailMutation = useMutation({
    mutationFn: () => notificationsApi.testEmail(),
    onSuccess: (res) => toast.success(res.data?.detail || 'تم إرسال رسالة الاختبار'),
    onError: () => toast.error('فشل إرسال رسالة الاختبار — راجع إعدادات البريد'),
  });

  const emailReportMutation = useMutation({
    mutationFn: () => reportsApi.emailMonthly(),
    onSuccess: (res) => toast.success(res.data?.detail || 'تم إرسال التقرير الشهري بالبريد'),
    onError: () => toast.error('فشل إرسال التقرير الشهري'),
  });

  const { data: notificationsData, isLoading } = useQuery({
    queryKey: ['notifications', filter],
    queryFn: () => notificationsApi.list({
      is_read: filter === 'unread' ? 'false' : undefined,
      priority: filter === 'critical' ? 'CRITICAL' : undefined,
    }),
    refetchInterval: 10000,
  });

  const { data: unreadData } = useQuery({
    queryKey: ['unread-count'],
    queryFn: () => notificationsApi.unreadCount(),
    refetchInterval: 5000,
  });

  const markAllReadMutation = useMutation({
    mutationFn: () => notificationsApi.markAllRead(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notifications'] });
      queryClient.invalidateQueries({ queryKey: ['unread-count'] });
      toast.success('تم تعليم جميع الإشعارات كمقروءة');
    },
  });

  const markReadMutation = useMutation({
    mutationFn: (id: string) => notificationsApi.markRead(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notifications'] });
      queryClient.invalidateQueries({ queryKey: ['unread-count'] });
    },
  });

  const dismissMutation = useMutation({
    mutationFn: (id: string) => notificationsApi.dismiss(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notifications'] });
      queryClient.invalidateQueries({ queryKey: ['unread-count'] });
      toast.success('تم حذف الإشعار');
    },
  });

  const notifications = notificationsData?.data?.results || notificationsData?.data || [];
  const unreadCount = unreadData?.data?.unread_count || 0;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className={`text-2xl font-bold flex items-center gap-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>
            <Bell className="w-6 h-6" />
            مركز الإشعارات
          </h1>
          <p className={`text-sm mt-1 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
            {unreadCount > 0 ? `لديك ${unreadCount} إشعار غير مقروء` : 'لا توجد إشعارات غير مقروءة'}
          </p>
        </div>
        {unreadCount > 0 && (
          <button
            onClick={() => markAllReadMutation.mutate()}
            disabled={markAllReadMutation.isPending}
            className="flex items-center gap-2 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors disabled:opacity-50"
          >
            <CheckCheck className="w-4 h-4" />
            تعليم الكل كمقروء
          </button>
        )}
      </div>

      {/* Filter Tabs */}
      <div className="flex gap-2">
        {[
          { value: 'all', label: 'الكل' },
          { value: 'unread', label: `غير مقروء (${unreadCount})` },
          { value: 'critical', label: 'حرجة' },
        ].map((tab) => (
          <button
            key={tab.value}
            onClick={() => setFilter(tab.value as any)}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              filter === tab.value
                ? 'bg-primary-600 text-white'
                : isDark
                ? 'bg-gray-800 text-gray-300 hover:bg-gray-700'
                : 'bg-white text-gray-700 hover:bg-gray-100 border border-gray-200'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Email settings card */}
      <div className={`p-4 rounded-xl border flex flex-col md:flex-row md:items-center gap-4 ${
        isDark ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-200'
      }`}>
        <div className="flex items-center gap-3 flex-1">
          <div className="p-2.5 bg-gradient-to-br from-primary-500 to-medical-500 rounded-lg flex-shrink-0">
            <Mail className="w-5 h-5 text-white" />
          </div>
          <div>
            <h3 className={`font-bold text-sm ${isDark ? 'text-white' : 'text-gray-900'}`}>
              إشعارات البريد الإلكتروني
            </h3>
            <p className={`text-xs mt-0.5 ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
              الإشعارات المهمة (تنبيهات أمنية، تحديثات القنوات، السجلات الجديدة) تُرسل تلقائياً إلى بريدك
              {user?.email && <> — <span dir="ltr">{user.email}</span></>}
            </p>
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <button
            onClick={() => testEmailMutation.mutate()}
            disabled={testEmailMutation.isPending}
            className="flex items-center gap-2 px-3.5 py-2 text-sm font-medium rounded-lg border border-primary-300 text-primary-700 hover:bg-primary-50 dark:border-primary-600 dark:text-primary-300 dark:hover:bg-primary-900/20 transition-colors disabled:opacity-50"
          >
            <Send className={`w-4 h-4 ${testEmailMutation.isPending ? 'animate-pulse' : ''}`} />
            اختبار البريد
          </button>
          {canEmailReports && (
            <button
              onClick={() => emailReportMutation.mutate()}
              disabled={emailReportMutation.isPending}
              className="flex items-center gap-2 px-3.5 py-2 text-sm font-medium rounded-lg bg-primary-600 text-white hover:bg-primary-700 transition-colors disabled:opacity-50"
            >
              <BarChart3 className={`w-4 h-4 ${emailReportMutation.isPending ? 'animate-pulse' : ''}`} />
              إرسال التقرير الشهري بالبريد
            </button>
          )}
        </div>
      </div>

      {/* Notifications List */}
      <div className="space-y-3">
        {isLoading ? (
          <div className="text-center py-12">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600 mx-auto"></div>
          </div>
        ) : notifications.length === 0 ? (
          <div className={`text-center py-12 rounded-xl border ${
            isDark ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-200'
          }`}>
            <Bell className="w-12 h-12 text-gray-300 mx-auto mb-3" />
            <p className={isDark ? 'text-gray-400' : 'text-gray-500'}>
              لا توجد إشعارات
            </p>
          </div>
        ) : (
          notifications.map((notification: any) => {
            const Icon = notificationIcons[notification.notification_type] || Bell;
            return (
              <div
                key={notification.id}
                className={`p-4 rounded-xl border transition-all ${
                  notification.is_read
                    ? isDark
                      ? 'bg-gray-800/50 border-gray-700'
                      : 'bg-white border-gray-200'
                    : isDark
                    ? 'bg-primary-900/20 border-primary-700'
                    : 'bg-primary-50 border-primary-200'
                }`}
              >
                <div className="flex items-start gap-3">
                  <div className={`p-2 rounded-lg ${
                    notification.priority === 'CRITICAL'
                      ? 'bg-red-100 dark:bg-red-900/30'
                      : notification.priority === 'HIGH'
                      ? 'bg-orange-100 dark:bg-orange-900/30'
                      : isDark ? 'bg-gray-700' : 'bg-gray-100'
                  }`}>
                    <Icon className={`w-5 h-5 ${
                      notification.priority === 'CRITICAL' ? 'text-red-600' :
                      notification.priority === 'HIGH' ? 'text-orange-600' :
                      isDark ? 'text-gray-300' : 'text-gray-600'
                    }`} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-start justify-between gap-2">
                      <div>
                        <h3 className={`font-medium ${isDark ? 'text-white' : 'text-gray-900'} ${!notification.is_read ? 'font-bold' : ''}`}>
                          {notification.title}
                        </h3>
                        <p className={`text-sm mt-1 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
                          {notification.message}
                        </p>
                      </div>
                      <div className="flex items-center gap-1">
                        <span className={`text-xs ${priorityColors[notification.priority]}`}>
                          {notification.priority}
                        </span>
                      </div>
                    </div>
                    <div className="flex items-center justify-between mt-3">
                      <span className={`text-xs ${isDark ? 'text-gray-500' : 'text-gray-400'}`}>
                        {new Date(notification.created_at).toLocaleString('ar-SA')}
                      </span>
                      <div className="flex items-center gap-2">
                        {!notification.is_read && (
                          <button
                            onClick={() => markReadMutation.mutate(notification.id)}
                            className="text-xs text-primary-600 hover:text-primary-700 flex items-center gap-1"
                          >
                            <CheckCheck className="w-3 h-3" />
                            تعليم كمقروء
                          </button>
                        )}
                        <button
                          onClick={() => dismissMutation.mutate(notification.id)}
                          className="text-xs text-red-600 hover:text-red-700 flex items-center gap-1"
                        >
                          <Trash2 className="w-3 h-3" />
                          حذف
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
