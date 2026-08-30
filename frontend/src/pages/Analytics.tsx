import { useQuery } from '@tanstack/react-query';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, Legend, LineChart, Line, Area, AreaChart
} from 'recharts';
import { Activity, Users, FolderKanban, FileText, TrendingUp } from 'lucide-react';
import { securityAPI } from '../api/client';

const COLORS = ['#3b82f6', '#0d9488', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899', '#14b8a6', '#f97316'];

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

export default function Analytics() {
  const { data: statsData, isLoading } = useQuery({
    queryKey: ['analytics-stats'],
    queryFn: () => securityAPI.stats(),
  });

  const { data: activityData } = useQuery({
    queryKey: ['analytics-activity'],
    queryFn: () => securityAPI.activity(),
  });

  const stats = statsData?.data;
  const activities = activityData?.data?.activities || [];

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

  const usersByRoleData = stats?.users?.by_role
    ? Object.entries(stats.users.by_role).map(([key, value]) => ({
        name: roleLabels[key] || key,
        value: value as number,
      }))
    : [];

  const trendsData = stats?.trends?.map((t: any) => ({
    date: new Date(t.date).toLocaleDateString('ar-SA', { day: 'numeric', month: 'short' }),
    channels: t.channels,
    records: t.records,
  })) || [];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
          <Activity className="w-7 h-7 text-primary-600" />
          التحليلات والإحصائيات
        </h1>
        <p className="text-gray-600 dark:text-gray-400 text-sm mt-1">
          تحليل شامل للبيانات والنشاطات في النظام
        </p>
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="card text-center">
          <FolderKanban className="w-10 h-10 text-primary-600 mx-auto mb-2" />
          <div className="text-3xl font-bold text-gray-900 dark:text-white">
            {stats?.channels?.total || 0}
          </div>
          <div className="text-sm text-gray-500 dark:text-gray-400">إجمالي القنوات</div>
        </div>
        <div className="card text-center">
          <Users className="w-10 h-10 text-medical-600 mx-auto mb-2" />
          <div className="text-3xl font-bold text-gray-900 dark:text-white">
            {stats?.patients?.total || 0}
          </div>
          <div className="text-sm text-gray-500 dark:text-gray-400">المرضى</div>
        </div>
        <div className="card text-center">
          <FileText className="w-10 h-10 text-blue-600 mx-auto mb-2" />
          <div className="text-3xl font-bold text-gray-900 dark:text-white">
            {stats?.records?.total || 0}
          </div>
          <div className="text-sm text-gray-500 dark:text-gray-400">السجلات الطبية</div>
        </div>
        <div className="card text-center">
          <TrendingUp className="w-10 h-10 text-green-600 mx-auto mb-2" />
          <div className="text-3xl font-bold text-gray-900 dark:text-white">
            {stats?.users?.total_users || 0}
          </div>
          <div className="text-sm text-gray-500 dark:text-gray-400">المستخدمون</div>
        </div>
      </div>

      {/* Weekly trends */}
      <div className="card">
        <h2 className="font-bold text-gray-900 dark:text-white mb-4">
          النشاط خلال الأسبوع الماضي
        </h2>
        {trendsData.length > 0 ? (
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={trendsData}>
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
              <Legend />
              <Line type="monotone" dataKey="records" stroke="#3b82f6" strokeWidth={2} name="السجلات" />
              <Line type="monotone" dataKey="channels" stroke="#0d9488" strokeWidth={2} name="القنوات" />
            </LineChart>
          </ResponsiveContainer>
        ) : (
          <div className="h-[300px] flex items-center justify-center text-gray-400">
            لا توجد بيانات
          </div>
        )}
      </div>

      {/* Charts grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Channels by type */}
        <div className="card">
          <h2 className="font-bold text-gray-900 dark:text-white mb-4">
            توزيع القنوات حسب النوع
          </h2>
          {channelsByTypeData.length > 0 ? (
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie
                  data={channelsByTypeData}
                  cx="50%"
                  cy="50%"
                  outerRadius={100}
                  dataKey="value"
                  label={(entry) => `${entry.name}: ${entry.value}`}
                >
                  {channelsByTypeData.map((_, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-[300px] flex items-center justify-center text-gray-400">
              لا توجد بيانات
            </div>
          )}
        </div>

        {/* Records by type */}
        <div className="card">
          <h2 className="font-bold text-gray-900 dark:text-white mb-4">
            توزيع السجلات حسب النوع
          </h2>
          {recordsByTypeData.length > 0 ? (
            <ResponsiveContainer width="100%" height={300}>
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
            <div className="h-[300px] flex items-center justify-center text-gray-400">
              لا توجد بيانات
            </div>
          )}
        </div>

        {/* Users by role (admin only) */}
        {usersByRoleData.length > 0 && (
          <div className="card">
            <h2 className="font-bold text-gray-900 dark:text-white mb-4">
              المستخدمون حسب الدور
            </h2>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={usersByRoleData}>
                <CartesianGrid strokeDasharray="3 3" className="dark:opacity-20" />
                <XAxis dataKey="name" className="text-xs" angle={-15} textAnchor="end" height={60} />
                <YAxis className="text-xs" />
                <Tooltip
                  contentStyle={{
                    backgroundColor: 'rgb(31, 41, 55)',
                    border: 'none',
                    borderRadius: '8px',
                    color: 'white',
                  }}
                />
                <Bar dataKey="value" fill="#8b5cf6" radius={[8, 8, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}

        {/* Activity feed */}
        <div className="card">
          <h2 className="font-bold text-gray-900 dark:text-white mb-4">
            سجل النشاطات
          </h2>
          <div className="space-y-2 max-h-[300px] overflow-y-auto">
            {activities.map((activity: any) => (
              <div
                key={activity.id}
                className="flex items-start gap-3 p-2 hover:bg-gray-50 dark:hover:bg-gray-700/50 rounded-lg"
              >
                <div className={`w-2 h-2 rounded-full mt-2 ${
                  activity.is_critical ? 'bg-red-500' : 'bg-primary-500'
                }`} />
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-gray-900 dark:text-white truncate">
                    {activity.title}
                  </p>
                  <p className="text-xs text-gray-500 dark:text-gray-400">
                    {activity.channel_name} • {activity.created_by}
                  </p>
                </div>
                <span className="text-xs text-gray-400 dark:text-gray-500">
                  {new Date(activity.timestamp).toLocaleDateString('ar-SA')}
                </span>
              </div>
            ))}
            {activities.length === 0 && (
              <p className="text-center text-gray-500 dark:text-gray-400 py-4">
                لا توجد نشاطات
              </p>
            )}
          </div>
        </div>
      </div>

      {/* Audit stats */}
      {stats?.audit && (
        <div className="card">
          <h2 className="font-bold text-gray-900 dark:text-white mb-4">
            إحصائيات التدقيق (آخر 7 أيام)
          </h2>
          <div className="grid grid-cols-3 gap-4">
            <div className="text-center p-4 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
              <div className="text-3xl font-bold text-gray-900 dark:text-white">
                {stats.audit.total_events}
              </div>
              <div className="text-sm text-gray-500 dark:text-gray-400">إجمالي الأحداث</div>
            </div>
            <div className="text-center p-4 bg-red-50 dark:bg-red-900/20 rounded-lg">
              <div className="text-3xl font-bold text-red-600 dark:text-red-400">
                {stats.audit.critical_events}
              </div>
              <div className="text-sm text-red-700 dark:text-red-400">أحداث حرجة</div>
            </div>
            <div className="text-center p-4 bg-yellow-50 dark:bg-yellow-900/20 rounded-lg">
              <div className="text-3xl font-bold text-yellow-600 dark:text-yellow-400">
                {stats.audit.warnings}
              </div>
              <div className="text-sm text-yellow-700 dark:text-yellow-400">تحذيرات</div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
