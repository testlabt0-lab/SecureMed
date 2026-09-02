import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import {
  FolderKanban, Users, Shield, Activity, Fingerprint, AlertCircle,
  TrendingUp, Clock, CheckCircle, FileText, Stethoscope, Sparkles,
} from 'lucide-react';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, AreaChart, Area,
} from 'recharts';
import { useAuthStore } from '../store/authStore';
import { securityAPI, channelsAPI, patientsAPI } from '../api/client';
import CountUp from '../components/fx/CountUp';
import { StaggerContainer, StaggerItem } from '../components/fx/PageTransition';
import ECGLine from '../components/fx/ECGLine';

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

const statCardStyles: Record<string, { tile: string; glow: string }> = {
  primary: {
    tile: 'bg-gradient-to-br from-primary-500 to-indigo-600 shadow-lg shadow-primary-500/30',
    glow: 'group-hover:shadow-primary-500/20',
  },
  medical: {
    tile: 'bg-gradient-to-br from-medical-500 to-teal-600 shadow-lg shadow-medical-500/30',
    glow: 'group-hover:shadow-medical-500/20',
  },
  blue: {
    tile: 'bg-gradient-to-br from-sky-500 to-blue-600 shadow-lg shadow-sky-500/30',
    glow: 'group-hover:shadow-sky-500/20',
  },
  green: {
    tile: 'bg-gradient-to-br from-emerald-500 to-green-600 shadow-lg shadow-emerald-500/30',
    glow: 'group-hover:shadow-emerald-500/20',
  },
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
  const activities = Array.isArray(activityData?.data?.activities)
    ? activityData.data.activities
    : (Array.isArray(activityData?.data) ? activityData.data : (Array.isArray(activityData?.data?.results) ? activityData.data.results : []));
  const channels = Array.isArray(channelsData?.data?.results)
    ? channelsData.data.results
    : (Array.isArray(channelsData?.data) ? channelsData.data : []);

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

  const today = new Date().toLocaleDateString('ar-SA', {
    weekday: 'long',
    day: 'numeric',
    month: 'long',
    year: 'numeric',
  });

  return (
    <StaggerContainer className="space-y-6">
      {/* ============ Hero welcome banner with animated medical image ============ */}
      <StaggerItem>
        <motion.div
          className="relative overflow-hidden rounded-3xl shadow-xl shadow-primary-900/20"
          whileHover={{ scale: 1.004 }}
          transition={{ type: 'spring', stiffness: 200 }}
        >
          {/* Animated Ken Burns medical image */}
          <img
            src="/images/team.jpg"
            alt="فريق طبي"
            className="absolute inset-0 w-full h-full object-cover animate-ken-burns"
          />
          {/* Gradient overlays */}
          <div className="absolute inset-0 bg-gradient-to-l from-navy-900/95 via-primary-950/75 to-medical-900/40" />
          <div className="absolute inset-0 bg-grid-dark opacity-40" />

          {/* ECG accent */}
          <div className="absolute bottom-0 left-0 right-0 opacity-70">
            <ECGLine height={56} stroke="#5eead4" strokeWidth={2.4} opacity={0.8} duration={4} />
          </div>

          <div className="relative z-10 p-6 sm:p-8 lg:p-10">
            <motion.div
              className="inline-flex items-center gap-2 glass-chip px-3 py-1.5 rounded-full text-xs text-medical-200 mb-4"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2 }}
            >
              <Sparkles className="w-3.5 h-3.5 animate-pulse-slow" />
              {today}
            </motion.div>
            <motion.h1
              className="text-2xl sm:text-3xl lg:text-4xl font-black font-heading text-white leading-snug"
              initial={{ opacity: 0, y: 18 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1, duration: 0.55 }}
            >
              مرحباً، {user?.full_name?.split(' ')[0]}
              <motion.span
                className="inline-block ml-1"
                animate={{ rotate: [0, 14, -8, 12, 0] }}
                transition={{ repeat: Infinity, repeatDelay: 2.4, duration: 0.9 }}
              >
                👋
              </motion.span>
            </motion.h1>
            <motion.p
              className="text-primary-100/85 mt-2 max-w-xl"
              initial={{ opacity: 0, y: 14 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.18, duration: 0.5 }}
            >
              {user?.role === 'DOCTOR' && 'إليك نظرة على حالاتك اليوم — كل شيء تحت السيطرة'}
              {user?.role === 'NURSE' && 'إليك نظرة على واجباتك اليوم — يومك مليء بالخير'}
              {(user?.role === 'SUPER_ADMIN' || user?.role === 'HOSPITAL_ADMIN') &&
                'إليك نظرة شاملة على أداء المنصة اليوم'}
              {user?.role === 'AUDITOR' && 'إليك نظرة على سجلات الأمان والامتثال'}
              {user?.role === 'PATIENT' && 'صحتك أولويتنا — إليك ملخص حالتك اليوم'}
            </motion.p>

            {/* Quick live chips */}
            <motion.div
              className="mt-5 flex flex-wrap items-center gap-2.5"
              initial={{ opacity: 0, y: 14 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.28 }}
            >
              <span className="glass-chip px-3.5 py-1.5 rounded-full text-xs text-white flex items-center gap-2">
                <span className="relative flex h-2 w-2">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-medical-400 opacity-70" />
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-medical-400" />
                </span>
                متصل الآن
              </span>
              <span className="glass-chip px-3.5 py-1.5 rounded-full text-xs text-white flex items-center gap-1.5">
                <Shield className="w-3.5 h-3.5 text-medical-300" />
                تشفير AES-256 نشط
              </span>
              <Link
                to="/patients"
                className="glass-chip px-3.5 py-1.5 rounded-full text-xs text-white flex items-center gap-1.5 hover:bg-white/25 transition-colors"
              >
                <Users className="w-3.5 h-3.5 text-primary-300" />
                استعراض المرضى
              </Link>
            </motion.div>
          </div>
        </motion.div>
      </StaggerItem>

      {/* Stat cards */}
      <StaggerContainer
        className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4"
        delay={0.1}
      >
        {statCards.map((stat) => {
          const styles = statCardStyles[stat.color] || statCardStyles.primary;
          return (
            <StaggerItem key={stat.label}>
              <Link to={stat.link} className="block group">
                <motion.div
                  className={`card card-shine relative h-full transition-all duration-300 group-hover:-translate-y-1.5 group-hover:shadow-card-hover dark:bg-gray-800/70 ${styles.glow}`}
                  whileTap={{ scale: 0.98 }}
                >
                  <div className="flex items-center justify-between mb-4">
                    <motion.div
                      className={`icon-tile ${styles.tile}`}
                      whileHover={{ rotate: -8, scale: 1.1 }}
                      transition={{ type: 'spring', stiffness: 300 }}
                    >
                      <stat.icon className="w-6 h-6 text-white" />
                    </motion.div>
                    <div className="flex items-center gap-1 text-green-500 bg-green-500/10 px-2 py-1 rounded-full">
                      <TrendingUp className="w-3.5 h-3.5" />
                      <span className="text-[11px] font-bold">مباشر</span>
                    </div>
                  </div>
                  <div className="text-3xl font-black font-heading text-gray-900 dark:text-white">
                    <CountUp value={stat.value} />
                  </div>
                  <div className="text-sm font-medium text-gray-600 dark:text-gray-300 mt-1">{stat.label}</div>
                  <div className="text-xs text-gray-400 dark:text-gray-500 mt-0.5">{stat.sub}</div>
                </motion.div>
              </Link>
            </StaggerItem>
          );
        })}
      </StaggerContainer>

      {/* Charts row */}
      <StaggerContainer className="grid grid-cols-1 lg:grid-cols-2 gap-6" delay={0.15}>
        {/* Trends chart */}
        <StaggerItem>
          <div className="card h-full">
            <h2 className="font-bold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
              <span className="icon-tile w-9 h-9 !rounded-lg bg-gradient-to-br from-primary-500 to-indigo-600">
                <Activity className="w-5 h-5 text-white" />
              </span>
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
                      backgroundColor: 'rgb(15, 23, 42)',
                      border: '1px solid rgb(51, 65, 85)',
                      borderRadius: '12px',
                      color: 'white',
                      boxShadow: '0 8px 30px rgba(0,0,0,0.35)',
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
        </StaggerItem>

        {/* Channels by priority */}
        <StaggerItem>
          <div className="card h-full">
            <h2 className="font-bold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
              <span className="icon-tile w-9 h-9 !rounded-lg bg-gradient-to-br from-amber-500 to-orange-600">
                <AlertCircle className="w-5 h-5 text-white" />
              </span>
              القنوات حسب الأولوية
            </h2>
            {priorityData.length > 0 ? (
              <ResponsiveContainer width="100%" height={250}>
                <PieChart>
                  <Pie
                    data={priorityData}
                    cx="50%"
                    cy="50%"
                    innerRadius={55}
                    outerRadius={85}
                    paddingAngle={4}
                    dataKey="value"
                    label={(entry) => `${entry.name}: ${entry.value}`}
                  >
                    {priorityData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} stroke="none" />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{
                      backgroundColor: 'rgb(15, 23, 42)',
                      border: '1px solid rgb(51, 65, 85)',
                      borderRadius: '12px',
                      color: 'white',
                    }}
                  />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-[250px] flex items-center justify-center text-gray-400">
                لا توجد بيانات
              </div>
            )}
          </div>
        </StaggerItem>

        {/* Channels by type */}
        <StaggerItem>
          <div className="card h-full">
            <h2 className="font-bold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
              <span className="icon-tile w-9 h-9 !rounded-lg bg-gradient-to-br from-primary-500 to-blue-700">
                <FolderKanban className="w-5 h-5 text-white" />
              </span>
              القنوات حسب النوع
            </h2>
            {channelsByTypeData.length > 0 ? (
              <ResponsiveContainer width="100%" height={250}>
                <BarChart data={channelsByTypeData}>
                  <CartesianGrid strokeDasharray="3 3" className="dark:opacity-20" />
                  <XAxis dataKey="name" className="text-xs" />
                  <YAxis className="text-xs" />
                  <Tooltip
                    cursor={{ fill: 'rgba(59, 130, 246, 0.06)' }}
                    contentStyle={{
                      backgroundColor: 'rgb(15, 23, 42)',
                      border: '1px solid rgb(51, 65, 85)',
                      borderRadius: '12px',
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
        </StaggerItem>

        {/* Records by type */}
        <StaggerItem>
          <div className="card h-full">
            <h2 className="font-bold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
              <span className="icon-tile w-9 h-9 !rounded-lg bg-gradient-to-br from-medical-500 to-teal-700">
                <FileText className="w-5 h-5 text-white" />
              </span>
              السجلات حسب النوع
            </h2>
            {recordsByTypeData.length > 0 ? (
              <ResponsiveContainer width="100%" height={250}>
                <BarChart data={recordsByTypeData} layout="vertical">
                  <CartesianGrid strokeDasharray="3 3" className="dark:opacity-20" />
                  <XAxis type="number" className="text-xs" />
                  <YAxis dataKey="name" type="category" className="text-xs" width={80} />
                  <Tooltip
                    cursor={{ fill: 'rgba(13, 148, 136, 0.06)' }}
                    contentStyle={{
                      backgroundColor: 'rgb(15, 23, 42)',
                      border: '1px solid rgb(51, 65, 85)',
                      borderRadius: '12px',
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
        </StaggerItem>
      </StaggerContainer>

      {/* Activity feed + recent channels */}
      <StaggerContainer className="grid grid-cols-1 lg:grid-cols-2 gap-6" delay={0.2}>
        {/* Activity feed */}
        <StaggerItem>
          <div className="card h-full">
            <div className="flex items-center justify-between mb-4">
              <h2 className="font-bold text-gray-900 dark:text-white flex items-center gap-2">
                <span className="icon-tile w-9 h-9 !rounded-lg bg-gradient-to-br from-indigo-500 to-purple-600">
                  <Clock className="w-5 h-5 text-white" />
                </span>
                آخر النشاطات
              </h2>
              <Link to="/analytics" className="text-sm text-primary-600 dark:text-primary-400 hover:underline">
                عرض الكل
              </Link>
            </div>
            <div className="space-y-3 max-h-96 overflow-y-auto pl-1">
              {activities.length === 0 ? (
                <p className="text-center text-gray-500 dark:text-gray-400 py-4">لا توجد نشاطات</p>
              ) : (
                activities.map((activity: any, i: number) => (
                  <motion.div
                    key={activity.id}
                    className="flex items-start gap-3 p-3 hover:bg-gray-50 dark:hover:bg-gray-700/50 rounded-xl transition-colors"
                    initial={{ opacity: 0, x: 20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: 0.05 * i, duration: 0.35 }}
                  >
                    <div className={`w-9 h-9 rounded-xl flex items-center justify-center flex-shrink-0 shadow-sm ${
                      activity.is_critical
                        ? 'bg-gradient-to-br from-red-500 to-rose-600'
                        : 'bg-gradient-to-br from-primary-500 to-indigo-600'
                    }`}>
                      {activity.is_critical ? (
                        <AlertCircle className="w-4 h-4 text-white animate-heartbeat" />
                      ) : (
                        <FileText className="w-4 h-4 text-white" />
                      )}
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-semibold text-gray-900 dark:text-white truncate">
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
                  </motion.div>
                ))
              )}
            </div>
          </div>
        </StaggerItem>

        {/* Recent channels */}
        <StaggerItem>
          <div className="card h-full">
            <div className="flex items-center justify-between mb-4">
              <h2 className="font-bold text-gray-900 dark:text-white flex items-center gap-2">
                <span className="icon-tile w-9 h-9 !rounded-lg bg-gradient-to-br from-sky-500 to-primary-600">
                  <FolderKanban className="w-5 h-5 text-white" />
                </span>
                آخر القنوات
              </h2>
              <Link to="/channels" className="text-sm text-primary-600 dark:text-primary-400 hover:underline">
                عرض الكل
              </Link>
            </div>
            <div className="space-y-3">
              {channels.slice(0, 5).map((channel: any, i: number) => (
                <motion.div
                  key={channel.id}
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: 0.05 * i, duration: 0.35 }}
                >
                  <Link
                    to={`/channels/${channel.id}`}
                    className="flex items-center justify-between p-3 hover:bg-primary-50/60 dark:hover:bg-gray-700/50 rounded-xl transition-all duration-200 hover:translate-x-1"
                  >
                    <div className="flex items-center gap-3">
                      <div className="relative">
                        <div className={`w-2.5 h-2.5 rounded-full ${
                          channel.status === 'ACTIVE' ? 'bg-green-500' : 'bg-gray-400'
                        }`} />
                        {channel.status === 'ACTIVE' && (
                          <span className="absolute inset-0 rounded-full bg-green-500/50 animate-ping" />
                        )}
                      </div>
                      <div>
                        <p className="font-semibold text-gray-900 dark:text-white">{channel.name}</p>
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
                </motion.div>
              ))}
              {channels.length === 0 && (
                <p className="text-center text-gray-500 dark:text-gray-400 py-4">لا توجد قنوات بعد</p>
              )}
            </div>
          </div>
        </StaggerItem>
      </StaggerContainer>

      {/* Security status */}
      {securityData?.data && (
        <StaggerItem>
          <div className="card relative overflow-hidden">
            <h2 className="font-bold text-gray-900 dark:text-white flex items-center gap-2 mb-4">
              <span className="icon-tile w-9 h-9 !rounded-lg bg-gradient-to-br from-emerald-500 to-green-700">
                <Shield className="w-5 h-5 text-white" />
              </span>
              حالة الأمان
            </h2>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {[
                { icon: Fingerprint, title: 'البصمة', sub: 'مفعلة' },
                { icon: CheckCircle, title: 'درجة الأمان', sub: `${100 - securityData.data.vulnerability_scan.risk_score}/100` },
                { icon: Shield, title: 'WAF', sub: 'نشط' },
                { icon: Stethoscope, title: 'AES-256', sub: 'مفعلة' },
              ].map((item, i) => (
                <motion.div
                  key={item.title}
                  className="flex items-center gap-3 p-3.5 bg-gradient-to-br from-green-50 to-emerald-50/60 dark:from-green-900/20 dark:to-emerald-900/10 rounded-2xl border border-green-100/80 dark:border-green-800/30 transition-all duration-300 hover:-translate-y-1 hover:shadow-lg hover:shadow-green-500/10"
                  initial={{ opacity: 0, y: 16 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.08 * i }}
                  whileHover={{ scale: 1.02 }}
                >
                  <motion.div
                    animate={{ scale: [1, 1.08, 1] }}
                    transition={{ repeat: Infinity, duration: 2.4, delay: i * 0.4 }}
                  >
                    <item.icon className="w-8 h-8 text-green-600 dark:text-green-400" />
                  </motion.div>
                  <div>
                    <p className="text-sm font-bold text-gray-900 dark:text-white">{item.title}</p>
                    <p className="text-xs text-green-700 dark:text-green-400">{item.sub}</p>
                  </div>
                </motion.div>
              ))}
            </div>
          </div>
        </StaggerItem>
      )}
    </StaggerContainer>
  );
}
