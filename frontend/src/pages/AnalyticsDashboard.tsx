import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  Users, FolderKanban, Activity, Shield, AlertCircle,
  TrendingUp, TrendingDown, FileText, UserPlus, Fingerprint, Lock, CalendarClock
} from 'lucide-react';
import { useAuthStore } from '../store/authStore';
import { analyticsApi, reportsApi, downloadBlobResponse } from '../api/extendedApis';
import { useThemeStore } from '../store/themeStore';
import toast from 'react-hot-toast';
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  BarChart, Bar, PieChart, Pie, Cell, Legend
} from 'recharts';

const COLORS = ['#0ea5e9', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899', '#6366f1', '#14b8a6'];

const roleLabels: Record<string, string> = {
  SUPER_ADMIN: 'مدير النظام',
  HOSPITAL_ADMIN: 'مدير المستشفى',
  DOCTOR: 'طبيب',
  NURSE: 'ممرض',
  LAB_TECH: 'فني مختبر',
  PHARMACIST: 'صيدلي',
  AUDITOR: 'مراجع أمني',
  PATIENT: 'مريض',
};

const channelTypeLabels: Record<string, string> = {
  EMERGENCY: 'طارئة',
  INPATIENT: 'مقيم',
  OUTPATIENT: 'خارجي',
  CONSULTATION: 'استشارة',
  FOLLOW_UP: 'متابعة',
};

export default function AnalyticsDashboard() {
  const user = useAuthStore(state => state.user);
  const { theme } = useThemeStore();
  const isDark = theme === 'dark';
  const [downloadingMonthly, setDownloadingMonthly] = useState(false);

  const handleMonthlyReport = async () => {
    setDownloadingMonthly(true);
    const toastId = toast.loading('جاري توليد التقرير الشهري (PDF + رسوم بيانية)...');
    try {
      const response = await reportsApi.monthlyPdf();
      downloadBlobResponse(response, 'SecureMed_Monthly_Report.pdf');
      toast.success('تم تنزيل التقرير الشهري', { id: toastId });
    } catch (err: any) {
      toast.error(
        err.response?.status === 403
          ? 'التقرير متاح للمدير والمراجع الأمني فقط'
          : 'فشل توليد التقرير',
        { id: toastId },
      );
    } finally {
      setDownloadingMonthly(false);
    }
  };

  const { data: overview, isLoading } = useQuery({
    queryKey: ['analytics-overview'],
    queryFn: () => analyticsApi.overview(),
    refetchInterval: 30000, // Refresh every 30 seconds
  });

  const { data: activityFeed } = useQuery({
    queryKey: ['activity-feed'],
    queryFn: () => analyticsApi.activityFeed(10),
    refetchInterval: 10000,
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
      </div>
    );
  }

  const data = overview?.data;
  const activities = Array.isArray(activityFeed?.data?.activities)
    ? activityFeed.data.activities
    : (Array.isArray(activityFeed?.data) ? activityFeed.data : (Array.isArray(activityFeed?.data?.results) ? activityFeed.data.results : []));

  // Calculate trend indicators
  const todayActivity = data?.activity_trend?.[data.activity_trend.length - 1]?.count || 0;
  const yesterdayActivity = data?.activity_trend?.[data.activity_trend.length - 2]?.count || 0;
  const activityTrend = yesterdayActivity > 0
    ? ((todayActivity - yesterdayActivity) / yesterdayActivity * 100).toFixed(1)
    : '0';

  const stats = [
    {
      label: 'إجمالي المستخدمين',
      value: data?.total_users || 0,
      sub: `${data?.active_users || 0} نشط`,
      icon: Users,
      color: 'primary',
      trend: '+12%',
      trendUp: true,
    },
    {
      label: 'القنوات النشطة',
      value: data?.active_channels || 0,
      sub: `من ${data?.total_channels || 0}`,
      icon: FolderKanban,
      color: 'medical',
      trend: '+8%',
      trendUp: true,
    },
    {
      label: 'إجمالي المرضى',
      value: data?.total_patients || 0,
      sub: `${data?.new_patients_today || 0} جديد اليوم`,
      icon: UserPlus,
      color: 'blue',
      trend: '+15%',
      trendUp: true,
    },
    {
      label: 'السجلات الطبية',
      value: data?.total_medical_records || 0,
      sub: `${data?.critical_records || 0} حرج`,
      icon: FileText,
      color: 'orange',
      trend: '+5%',
      trendUp: true,
    },
  ];

  const securityStats = [
    {
      label: 'تنبيهات الأمان اليوم',
      value: data?.security_alerts_today || 0,
      icon: Shield,
      color: 'red',
    },
    {
      label: 'حظر WAF اليوم',
      value: data?.waf_blocks_today || 0,
      icon: Lock,
      color: 'orange',
    },
    {
      label: 'دخول فاشل اليوم',
      value: data?.failed_logins_today || 0,
      icon: AlertCircle,
      color: 'yellow',
    },
    {
      label: 'دخول بيوميتري اليوم',
      value: data?.biometric_logins_today || 0,
      icon: Fingerprint,
      color: 'green',
    },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className={`text-2xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>
            لوحة التحليلات
          </h1>
          <p className={`text-sm mt-1 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
            إحصائيات شاملة وتحديثات في الوقت الفعلي
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={handleMonthlyReport}
            disabled={downloadingMonthly}
            className="btn-primary text-sm flex items-center gap-2"
          >
            <CalendarClock className="w-4 h-4" />
            {downloadingMonthly ? 'جاري التوليد...' : 'التقرير الشهري'}
          </button>
          <div className="flex items-center gap-2 px-3 py-1.5 bg-green-100 dark:bg-green-900/30 rounded-lg">
            <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></span>
            <span className="text-sm text-green-700 dark:text-green-400">مباشر</span>
          </div>
        </div>
      </div>

      {/* Main Stats */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {stats.map((stat) => (
          <div
            key={stat.label}
            className={`p-5 rounded-xl border ${
              isDark
                ? 'bg-gray-800 border-gray-700'
                : 'bg-white border-gray-200'
            } shadow-sm hover:shadow-md transition-shadow`}
          >
            <div className="flex items-start justify-between mb-3">
              <div className={`p-2 rounded-lg bg-${stat.color}-100 dark:bg-${stat.color}-900/30`}>
                <stat.icon className={`w-5 h-5 text-${stat.color}-600 dark:text-${stat.color}-400`} />
              </div>
              <div className={`flex items-center gap-1 text-xs ${
                stat.trendUp ? 'text-green-600' : 'text-red-600'
              }`}>
                {stat.trendUp ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
                {stat.trend}
              </div>
            </div>
            <div className={`text-3xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>
              {stat.value}
            </div>
            <div className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-600'} mt-1`}>
              {stat.label}
            </div>
            <div className={`text-xs ${isDark ? 'text-gray-500' : 'text-gray-500'} mt-2`}>
              {stat.sub}
            </div>
          </div>
        ))}
      </div>

      {/* Security Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {securityStats.map((stat) => (
          <div
            key={stat.label}
            className={`p-4 rounded-lg border ${
              isDark ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-200'
            }`}
          >
            <div className="flex items-center gap-2 mb-2">
              <stat.icon className={`w-4 h-4 text-${stat.color}-600`} />
              <span className={`text-xs ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
                {stat.label}
              </span>
            </div>
            <div className={`text-2xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>
              {stat.value}
            </div>
          </div>
        ))}
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Activity Trend Chart */}
        <div className={`p-5 rounded-xl border ${
          isDark ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-200'
        }`}>
          <h3 className={`font-bold mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>
            نشاط النظام (آخر 8 أيام)
          </h3>
          <SystemActivityChart data={data?.activity_trend || []} isDark={isDark} />
        </div>

        {/* Channels Trend Chart */}
        <div className={`p-5 rounded-xl border ${
          isDark ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-200'
        }`}>
          <h3 className={`font-bold mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>
            القنوات الجديدة (آخر 8 أيام)
          </h3>
          <ChannelsActivityChart data={data?.channels_trend || []} isDark={isDark} />
        </div>
        {/* Security Events Trend Chart */}
        <div className={`p-5 rounded-xl border ${
          isDark ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-200'
        }`}>
          <h3 className={`font-bold mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>
            الأحداث الأمنية حسب الخطورة
          </h3>
          <SecurityEventsChart data={data?.security_events_by_severity || {}} isDark={isDark} />
        </div>
      </div>

      {/* Two-column layout */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Activity Feed */}
        <div className={`lg:col-span-2 p-5 rounded-xl border ${
          isDark ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-200'
        }`}>
          <div className="flex items-center justify-between mb-4">
            <h3 className={`font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>
              آخر الأنشطة
            </h3>
            <Activity className="w-5 h-5 text-gray-400" />
          </div>
          <div className="space-y-3 max-h-96 overflow-y-auto">
            {activities.length === 0 ? (
              <p className={`text-center py-8 ${isDark ? 'text-gray-500' : 'text-gray-400'}`}>
                لا توجد أنشطة حديثة
              </p>
            ) : (
              activities.map((activity: any) => (
                <div
                  key={activity.id}
                  className={`flex items-start gap-3 p-3 rounded-lg ${
                    isDark ? 'bg-gray-700/50' : 'bg-gray-50'
                  }`}
                >
                  <div className={`w-2 h-2 rounded-full mt-2 ${
                    activity.severity === 'CRITICAL' ? 'bg-red-500' :
                    activity.severity === 'WARNING' ? 'bg-yellow-500' : 'bg-blue-500'
                  }`} />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between">
                      <span className={`text-sm font-medium ${isDark ? 'text-white' : 'text-gray-900'}`}>
                        {activity.user_name || 'النظام'}
                      </span>
                      <span className={`text-xs ${isDark ? 'text-gray-500' : 'text-gray-400'}`}>
                        {new Date(activity.timestamp).toLocaleTimeString('ar-SA', {
                          hour: '2-digit',
                          minute: '2-digit',
                        })}
                      </span>
                    </div>
                    <p className={`text-sm ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
                      {activity.event_type_display}
                    </p>
                    {activity.ip_address && (
                      <p className={`text-xs ${isDark ? 'text-gray-500' : 'text-gray-400'} font-mono`}>
                        {activity.ip_address}
                      </p>
                    )}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Users by Role */}
        <div className={`p-5 rounded-xl border ${
          isDark ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-200'
        }`}>
          <h3 className={`font-bold mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>
            المستخدمون حسب الدور
          </h3>
          <div className="h-[280px]">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={Object.entries(data?.users_by_role || {}).map(([role, count]) => ({
                    name: roleLabels[role] || role,
                    value: count
                  }))}
                  cx="50%"
                  cy="50%"
                  innerRadius={70}
                  outerRadius={90}
                  paddingAngle={5}
                  dataKey="value"
                >
                  {Object.entries(data?.users_by_role || {}).map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{ backgroundColor: isDark ? '#1F2937' : '#FFFFFF', borderColor: isDark ? '#374151' : '#E5E7EB', borderRadius: '8px' }}
                  itemStyle={{ color: isDark ? '#F3F4F6' : '#111827' }}
                />
                <Legend wrapperStyle={{ fontSize: '12px', color: isDark ? '#D1D5DB' : '#374151' }} />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Channels by Type */}
      <div className={`p-5 rounded-xl border ${
        isDark ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-200'
      }`}>
        <h3 className={`font-bold mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          القنوات حسب النوع
        </h3>
        <div className="h-[250px] mt-2">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart
              data={Object.entries(data?.channels_by_type || {}).map(([type, count]) => ({
                name: channelTypeLabels[type] || type,
                value: count
              }))}
              margin={{ top: 20, right: 30, left: 20, bottom: 5 }}
              barSize={40}
            >
              <CartesianGrid strokeDasharray="3 3" stroke={isDark ? '#374151' : '#E5E7EB'} vertical={false} />
              <XAxis dataKey="name" stroke={isDark ? '#9CA3AF' : '#6B7280'} tick={{ fill: isDark ? '#9CA3AF' : '#6B7280' }} />
              <YAxis allowDecimals={false} stroke={isDark ? '#9CA3AF' : '#6B7280'} tick={{ fill: isDark ? '#9CA3AF' : '#6B7280' }} />
              <Tooltip
                cursor={{ fill: isDark ? '#374151' : '#F3F4F6' }}
                contentStyle={{ backgroundColor: isDark ? '#1F2937' : '#FFFFFF', borderColor: isDark ? '#374151' : '#E5E7EB', borderRadius: '8px' }}
                itemStyle={{ color: isDark ? '#F3F4F6' : '#111827' }}
              />
              <Bar dataKey="value" name="عدد القنوات" fill="#14b8a6" radius={[4, 4, 0, 0]}>
                {Object.entries(data?.channels_by_type || {}).map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}

function SystemActivityChart({ data, isDark }: { data: any[]; isDark: boolean }) {
  if (!data || data.length === 0) {
    return <div className={`h-64 flex items-center justify-center ${isDark ? 'text-gray-500' : 'text-gray-400'}`}>لا توجد بيانات</div>;
  }
  const formattedData = data.map(d => ({ ...d, dateFormatted: new Date(d.date).toLocaleDateString('ar-SA', { day: 'numeric', month: 'short' }) }));
  
  return (
    <div className="h-64">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={formattedData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
          <defs>
            <linearGradient id="colorCount" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.8}/>
              <stop offset="95%" stopColor="#3b82f6" stopOpacity={0}/>
            </linearGradient>
          </defs>
          <XAxis dataKey="dateFormatted" stroke={isDark ? '#9CA3AF' : '#6B7280'} tick={{ fill: isDark ? '#9CA3AF' : '#6B7280' }} />
          <YAxis stroke={isDark ? '#9CA3AF' : '#6B7280'} tick={{ fill: isDark ? '#9CA3AF' : '#6B7280' }} allowDecimals={false} />
          <CartesianGrid strokeDasharray="3 3" stroke={isDark ? '#374151' : '#E5E7EB'} vertical={false} />
          <Tooltip 
            contentStyle={{ backgroundColor: isDark ? '#1F2937' : '#FFFFFF', borderColor: isDark ? '#374151' : '#E5E7EB', borderRadius: '8px' }}
            itemStyle={{ color: isDark ? '#F3F4F6' : '#111827' }}
          />
          <Area type="monotone" dataKey="count" name="النشاط" stroke="#3b82f6" fillOpacity={1} fill="url(#colorCount)" />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}

function ChannelsActivityChart({ data, isDark }: { data: any[]; isDark: boolean }) {
  if (!data || data.length === 0) {
    return <div className={`h-64 flex items-center justify-center ${isDark ? 'text-gray-500' : 'text-gray-400'}`}>لا توجد بيانات</div>;
  }
  const formattedData = data.map(d => ({ ...d, dateFormatted: new Date(d.date).toLocaleDateString('ar-SA', { day: 'numeric', month: 'short' }) }));
  
  return (
    <div className="h-64">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={formattedData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
          <XAxis dataKey="dateFormatted" stroke={isDark ? '#9CA3AF' : '#6B7280'} tick={{ fill: isDark ? '#9CA3AF' : '#6B7280' }} />
          <YAxis stroke={isDark ? '#9CA3AF' : '#6B7280'} tick={{ fill: isDark ? '#9CA3AF' : '#6B7280' }} allowDecimals={false} />
          <CartesianGrid strokeDasharray="3 3" stroke={isDark ? '#374151' : '#E5E7EB'} vertical={false} />
          <Tooltip 
            cursor={{ fill: isDark ? '#374151' : '#F3F4F6' }}
            contentStyle={{ backgroundColor: isDark ? '#1F2937' : '#FFFFFF', borderColor: isDark ? '#374151' : '#E5E7EB', borderRadius: '8px' }}
            itemStyle={{ color: isDark ? '#F3F4F6' : '#111827' }}
          />
          <Bar dataKey="count" name="القنوات" fill="#0D9488" radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

function SecurityEventsChart({ data, isDark }: { data: any; isDark: boolean }) {
  const chartData = [
    { name: 'خطير (Critical)', count: data['CRITICAL'] || 0, fill: '#ef4444' },
    { name: 'تحذير (Warning)', count: data['WARNING'] || 0, fill: '#f59e0b' },
    { name: 'معلومات (Info)', count: data['INFO'] || 0, fill: '#3b82f6' }
  ];

  if (!data || Object.keys(data).length === 0) {
    return <div className={`h-64 flex items-center justify-center ${isDark ? 'text-gray-500' : 'text-gray-400'}`}>لا توجد بيانات</div>;
  }

  return (
    <div className="h-64">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }} layout="vertical">
          <XAxis type="number" stroke={isDark ? '#9CA3AF' : '#6B7280'} tick={{ fill: isDark ? '#9CA3AF' : '#6B7280' }} allowDecimals={false} />
          <YAxis type="category" dataKey="name" stroke={isDark ? '#9CA3AF' : '#6B7280'} tick={{ fill: isDark ? '#9CA3AF' : '#6B7280' }} width={100} />
          <CartesianGrid strokeDasharray="3 3" stroke={isDark ? '#374151' : '#E5E7EB'} horizontal={false} />
          <Tooltip 
            cursor={{ fill: isDark ? '#374151' : '#F3F4F6' }}
            contentStyle={{ backgroundColor: isDark ? '#1F2937' : '#FFFFFF', borderColor: isDark ? '#374151' : '#E5E7EB', borderRadius: '8px' }}
            itemStyle={{ color: isDark ? '#F3F4F6' : '#111827' }}
          />
          <Bar dataKey="count" name="عدد الأحداث" radius={[0, 4, 4, 0]}>
            {chartData.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={entry.fill} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
