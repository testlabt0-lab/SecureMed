import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import {
  FolderKanban, Users, Shield, Activity, Fingerprint, AlertCircle,
  TrendingUp, Clock, CheckCircle, FileText, Stethoscope
} from 'lucide-react';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, LineChart, Line, Area, AreaChart, Legend
} from 'recharts';
import { useAuthStore } from '../store/authStore';
import { securityAPI, channelsAPI, patientsAPI } from '../api/client';

const COLORS = ['#3b82f6', '#0d9488', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899'];

const channelTypeLabels: Record<string, string> = {
  EMERGENCY: 'طارئة',
  INPATIENT: 'مقيم',
  OUTPATIENT: 'خارجي',
  CONSULTATION: 'استشارة',
  FOLLOW_UP: 'متابعة',
};

const recordTypeLabels: Record<string, string> = {
  DIAGNOSIS: 'تشخيص',
  PRESCRIPTION: 'وصفة',
  LAB_ORDER: 'طلب تحاليل',
  LAB_RESULT: 'نتيجة تحاليل',
  IMAGING: 'تصوير',
  NOTES: 'ملاحظات',
  VITALS: 'علامات حيوية',
  PROCEDURE: 'إجراء',
};

export default function Dashboard() {
  const { user } = useAuthStore();

  const { data: statsData } = useQuery({
    queryKey: ['dashboard-stats'],
    queryFn: () => securityAPI.stats(),
  });

  const { data: activityData } = useQuery({
    queryKey: ['activity-feed'],
    queryFn: () => securityAPI.activity(),
  });

  const { data: channelsData } = useQuery({
    queryKey: ['channels-dashboard'],
    queryFn: () => channelsAPI.list(),
  });

  const { data: securityData } = useQuery({
    queryKey: ['security-dashboard'],
    queryFn: () => securityAPI.dashboard(),
    enabled: ['SUPER_ADMIN', 'HOSPITAL_ADMIN', 'AUDITOR'].includes(user?.role || ''),
  });

  const stats = statsData?.data;
  const activities = activityData?.data?.activities || [];
  const channels = channelsData?.data?.results || channelsData?.data || [];

  const statCards = [
    {
      label: 'إجمالي القنوات',
      value: stats?.channels?.total || 0,
      sub: `${stats?.channels?.active || 0} نشطة`,
      icon: FolderKanban,
      color: 'primary',
      link: '/channels',
    },
    {
      label: 'المرضى',
      value: stats?.patients?.total || 0,
      sub: 'مسجلون',
      icon: Users,
      color: 'medical',
      link: '/patients',
    },
    {
      label: 'السجلات الطبية',
      value: stats?.records?.total || 0,
      sub: `${stats?.records?.critical || 0} حرجة`,
      icon: FileText,
      color: 'blue',
      link: '/analytics',
    },
    {
      label: 'ميزات الأمان',
      value: 6,
      sub: 'جميعها مفعلة',
      icon: Shield,
      color: 'green',
      link: '/security',
    },
  ];

  // Chart data
  const channelsByTypeData = stats?.channels?.by_type
    ? Object.entries(stats.channels.by_type).map(([key, value]) => ({
        name: channelTypeLabels[key] || key,
        value: value as number,
      }))
    : [];

  const recordsByTypeData = stats?.records?.by_type
    ? Object.entries(stats.records.by_type).map(([key, value]) => ({
        name: recordTypeLabels[key] || key,
        value: value as number,
      }))
    : [];

  const trendsData = stats?.trends?.map((t: any) => ({
    date: new Date(t.date).toLocaleDateString('ar-SA', { day: 'numeric', month: 'short' }),
    channels: t.channels,
    records: t.records,
  })) || [];

  const priorityData = stats?.channels?.by_priority
    ? Object.entries(stats.channels.by_priority).map(([key, value]) => ({
        name: key === 'LOW' ? 'منخفضة' : key === 'MEDIUM' ? 'متوسطة' : key === 'HIGH' ? 'عالية' : 'عاجلة',
        value: value as number,
        color: key === 'LOW' ? '#10b981' : key === 'MEDIUM' ? '#3b82f6' : key === 'HIGH' ? '#f59e0b' : '#ef4444',
      }))
    : [];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
          مرحباً، {user?.full_name} 👋
        </h1>
        <p className="text-gray-600 dark:text-gray-400 mt-1">
          {user?.role === 'DOCTOR' && 'إليك نظرة على حالاتك اليوم'}
          {user?.role === 'NURSE' && 'إليك نظرة على واجباتك اليوم'}
          {(user?.role === 'SUPER_ADMIN' || user?.role === 'HOSPITAL_ADMIN') &&
            'إليك نظرة شاملة على المنصة'}
          {user?.role === 'AUDITOR' && 'إليك نظرة على سجلات الأمان'}
        </p>
      </div>

      {/* Stat cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {statCards.map((stat) => (
          <Link
            key={stat.label}
            to={stat.link}
            className="card hover:shadow-lg transition-shadow"
          >
            <div className="flex items-center justify-between mb-4">
              <div className={`w-12 h-12 rounded-xl flex items-center justify-center bg-${stat.color}-100 dark:bg-${stat.color}-900/30`}>
                <stat.icon className={`w-6 h-6 text-${stat.color}-600 dark:text-${stat.color}-400`} />
              </div>
              <TrendingUp className="w-5 h-5 text-green-500" />
            </div>
            <div className="text-3xl font-bold text-gray-900 dark:text-white">{stat.value}</div>
            <div className="text-sm text-gray-500 dark:text-gray-400 mt-1">{stat.label}</div>
            <div className="text-xs text-gray-400 dark:text-gray-500 mt-1">{stat.sub}</div>
          </Link>
        ))}
      </div>

      {/* Charts row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Trends chart */}
        <div className="card">
          <h2 className="font-bold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
            <Activity className="w-5 h-5 text-primary-600" />
            النشاط الأسبوعي
          </h2>
          {trendsData.length > 0 ? (
            <ResponsiveContainer width="100%" height={250}>
              <AreaChart data={trendsData}>
                <defs>
                  <linearGradient id="colorRecords" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.8} />
                    <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
                  </linearGradient>
                  <linearGradient id="colorChannels" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#0d9488" stopOpacity={0.8} />
                    <stop offset="95%" stopColor="#0d9488" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" className="dark:opacity-20" />
                <XAxis dataKey="date" className="text-xs" />
                <YAxis className="text-xs" />
                <Tooltip
                  contentStyle={{
                    backgroundColor: 'rgb(31, 41, 55)',
                    border: 'none',
                    borderRadius: '8px',
                    color: 'white',
                  }}
                />
                <Area type="monotone" dataKey="records" stroke="#3b82f6" fill="url(#colorRecords)" name="السجلات" />
                <Area type="monotone" dataKey="channels" stroke="#0d9488" fill="url(#colorChannels)" name="القنوات" />
              </AreaChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-[250px] flex items-center justify-center text-gray-400">
              لا توجد بيانات
            </div>
          )}
        </div>

        {/* Channels by priority */}
        <div className="card">
          <h2 className="font-bold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
            <AlertCircle className="w-5 h-5 text-orange-500" />
            القنوات حسب الأولوية
          </h2>
          {priorityData.length > 0 ? (
            <ResponsiveContainer width="100%" height={250}>
              <PieChart>
                <Pie
                  data={priorityData}
                  cx="50%"
                  cy="50%"
                  outerRadius={80}
                  dataKey="value"
                  label={(entry) => `${entry.name}: ${entry.value}`}
                >
                  {priorityData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-[250px] flex items-center justify-center text-gray-400">
              لا توجد بيانات
            </div>
          )}
        </div>

        {/* Channels by type */}
        <div className="card">
          <h2 className="font-bold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
            <FolderKanban className="w-5 h-5 text-primary-600" />
            القنوات حسب النوع
          </h2>
          {channelsByTypeData.length > 0 ? (
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={channelsByTypeData}>
                <CartesianGrid strokeDasharray="3 3" className="dark:opacity-20" />
                <XAxis dataKey="name" className="text-xs" />
                <YAxis className="text-xs" />
                <Tooltip
                  contentStyle={{
                    backgroundColor: 'rgb(31, 41, 55)',
                    border: 'none',
                    borderRadius: '8px',
                    color: 'white',
                  }}
                />
                <Bar dataKey="value" fill="#3b82f6" radius={[8, 8, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-[250px] flex items-center justify-center text-gray-400">
              لا توجد بيانات
            </div>
          )}
        </div>

        {/* Records by type */}
        <div className="card">
          <h2 className="font-bold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
            <FileText className="w-5 h-5 text-medical-600" />
            السجلات حسب النوع
          </h2>
          {recordsByTypeData.length > 0 ? (
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={recordsByTypeData} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" className="dark:opacity-20" />
                <XAxis type="number" className="text-xs" />
                <YAxis dataKey="name" type="category" className="text-xs" width={80} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: 'rgb(31, 41, 55)',
                    border: 'none',
                    borderRadius: '8px',
                    color: 'white',
                  }}
                />
                <Bar dataKey="value" fill="#0d9488" radius={[0, 8, 8, 0]} />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-[250px] flex items-center justify-center text-gray-400">
              لا توجد بيانات
            </div>
          )}
        </div>
      </div>

      {/* Activity feed + recent channels */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Activity feed */}
        <div className="card">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-bold text-gray-900 dark:text-white flex items-center gap-2">
              <Clock className="w-5 h-5 text-primary-600" />
              آخر النشاطات
            </h2>
            <Link to="/analytics" className="text-sm text-primary-600 dark:text-primary-400 hover:underline">
              عرض الكل
            </Link>
          </div>
          <div className="space-y-3 max-h-96 overflow-y-auto">
            {activities.length === 0 ? (
              <p className="text-center text-gray-500 dark:text-gray-400 py-4">لا توجد نشاطات</p>
            ) : (
              activities.map((activity: any) => (
                <div
                  key={activity.id}
                  className="flex items-start gap-3 p-3 hover:bg-gray-50 dark:hover:bg-gray-700/50 rounded-lg transition-colors"
                >
                  <div className={`w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 ${
                    activity.is_critical
                      ? 'bg-red-100 dark:bg-red-900/30'
                      : 'bg-primary-100 dark:bg-primary-900/30'
                  }`}>
                    {activity.is_critical ? (
                      <AlertCircle className="w-4 h-4 text-red-600 dark:text-red-400" />
                    ) : (
                      <FileText className="w-4 h-4 text-primary-600 dark:text-primary-400" />
                    )}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-900 dark:text-white truncate">
                      {activity.title}
                    </p>
                    <p className="text-xs text-gray-500 dark:text-gray-400 truncate">
                      {activity.channel_name} • {activity.created_by}
                    </p>
                    <p className="text-xs text-gray-400 dark:text-gray-500 mt-1">
                      {new Date(activity.timestamp).toLocaleString('ar-SA')}
                    </p>
                  </div>
                  <span className="badge badge-info flex-shrink-0">
                    {activity.record_type_display}
                  </span>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Recent channels */}
        <div className="card">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-bold text-gray-900 dark:text-white flex items-center gap-2">
              <FolderKanban className="w-5 h-5 text-primary-600" />
              آخر القنوات
            </h2>
            <Link to="/channels" className="text-sm text-primary-600 dark:text-primary-400 hover:underline">
              عرض الكل
            </Link>
          </div>
          <div className="space-y-3">
            {channels.slice(0, 5).map((channel: any) => (
              <Link
                key={channel.id}
                to={`/channels/${channel.id}`}
                className="flex items-center justify-between p-3 hover:bg-gray-50 dark:hover:bg-gray-700/50 rounded-lg transition-colors"
              >
                <div className="flex items-center gap-3">
                  <div className={`w-2 h-2 rounded-full ${
                    channel.status === 'ACTIVE' ? 'bg-green-500' : 'bg-gray-400'
                  }`} />
                  <div>
                    <p className="font-medium text-gray-900 dark:text-white">{channel.name}</p>
                    <p className="text-xs text-gray-500 dark:text-gray-400">{channel.channel_type_display}</p>
                  </div>
                </div>
                <span className={`badge ${
                  channel.priority === 'URGENT' ? 'badge-danger' :
                  channel.priority === 'HIGH' ? 'badge-warning' : 'badge-info'
                }`}>
                  {channel.priority}
                </span>
              </Link>
            ))}
            {channels.length === 0 && (
              <p className="text-center text-gray-500 dark:text-gray-400 py-4">لا توجد قنوات بعد</p>
            )}
          </div>
        </div>
      </div>

      {/* Security status */}
      {securityData?.data && (
        <div className="card">
          <h2 className="font-bold text-gray-900 dark:text-white flex items-center gap-2 mb-4">
            <Shield className="w-5 h-5 text-medical-600" />
            حالة الأمان
          </h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="flex items-center gap-3 p-3 bg-green-50 dark:bg-green-900/20 rounded-lg">
              <Fingerprint className="w-8 h-8 text-green-600" />
              <div>
                <p className="text-sm font-bold text-gray-900 dark:text-white">البصمة</p>
                <p className="text-xs text-green-700 dark:text-green-400">مفعلة</p>
              </div>
            </div>
            <div className="flex items-center gap-3 p-3 bg-green-50 dark:bg-green-900/20 rounded-lg">
              <CheckCircle className="w-8 h-8 text-green-600" />
              <div>
                <p className="text-sm font-bold text-gray-900 dark:text-white">درجة الأمان</p>
                <p className="text-xs text-green-700 dark:text-green-400">
                  {100 - securityData.data.vulnerability_scan.risk_score}/100
                </p>
              </div>
            </div>
            <div className="flex items-center gap-3 p-3 bg-green-50 dark:bg-green-900/20 rounded-lg">
              <Shield className="w-8 h-8 text-green-600" />
              <div>
                <p className="text-sm font-bold text-gray-900 dark:text-white">WAF</p>
                <p className="text-xs text-green-700 dark:text-green-400">نشط</p>
              </div>
            </div>
            <div className="flex items-center gap-3 p-3 bg-green-50 dark:bg-green-900/20 rounded-lg">
              <Stethoscope className="w-8 h-8 text-green-600" />
              <div>
                <p className="text-sm font-bold text-gray-900 dark:text-white">AES-256</p>
                <p className="text-xs text-green-700 dark:text-green-400">مفعلة</p>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
