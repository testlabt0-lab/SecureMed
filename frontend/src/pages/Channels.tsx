import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { Plus, Search, FolderKanban, ChevronLeft, ChevronRight, ArrowUpDown } from 'lucide-react';
import { channelsAPI, patientsAPI } from '../api/client';
import toast from 'react-hot-toast';

export default function Channels() {
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [priorityFilter, setPriorityFilter] = useState('');
  const [page, setPage] = useState(1);
  const [sortBy, setSortBy] = useState('created_at');
  const [sortOrder, setSortOrder] = useState('desc');
  const [showCreate, setShowCreate] = useState(false);
  const queryClient = useQueryClient();

  const { data: channelsData, isLoading } = useQuery({
    queryKey: ['channels', { search, statusFilter, priorityFilter, page, sortBy, sortOrder }],
    queryFn: () => channelsAPI.list({
      search,
      status: statusFilter,
      priority: priorityFilter,
      page,
      ordering: sortOrder === 'desc' ? `-${sortBy}` : sortBy,
    }),
  });

  const { data: patientsData } = useQuery({
    queryKey: ['patients-list'],
    queryFn: () => patientsAPI.list(),
  });

  const createMutation = useMutation({
    mutationFn: (data: any) => channelsAPI.create(data),
    onSuccess: () => {
      toast.success('تم إنشاء القناة بنجاح');
      queryClient.invalidateQueries({ queryKey: ['channels'] });
      setShowCreate(false);
    },
    onError: (err: any) => {
      toast.error(err.response?.data?.detail || 'فشل إنشاء القناة');
    },
  });

  const channels = channelsData?.data?.results || channelsData?.data || [];
  const totalCount = channelsData?.data?.count || 0;
  const totalPages = channelsData?.data?.total_pages || 1;
  const currentPage = channelsData?.data?.page || 1;
  const patients = patientsData?.data?.results || patientsData?.data || [];

  const handleSort = (field: string) => {
    if (sortBy === field) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      setSortBy(field);
      setSortOrder('asc');
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">القنوات والحالات</h1>
          <p className="text-gray-600 dark:text-gray-400 text-sm mt-1">
            إدارة حالات المرضى والقنوات الطبية
          </p>
        </div>
        <button
          onClick={() => setShowCreate(true)}
          className="btn-primary flex items-center gap-2"
        >
          <Plus className="w-4 h-4" />
          قناة جديدة
        </button>
      </div>

      {/* Stats summary */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <div className="card py-3 px-4">
          <div className="text-2xl font-bold text-gray-900 dark:text-white">{totalCount}</div>
          <div className="text-xs text-gray-500 dark:text-gray-400">إجمالي القنوات</div>
        </div>
        <div className="card py-3 px-4">
          <div className="text-2xl font-bold text-green-600 dark:text-green-400">
            {channels.filter((c: any) => c.status === 'ACTIVE').length}
          </div>
          <div className="text-xs text-gray-500 dark:text-gray-400">نشطة</div>
        </div>
        <div className="card py-3 px-4">
          <div className="text-2xl font-bold text-red-600 dark:text-red-400">
            {channels.filter((c: any) => c.priority === 'URGENT').length}
          </div>
          <div className="text-xs text-gray-500 dark:text-gray-400">عاجلة</div>
        </div>
        <div className="card py-3 px-4">
          <div className="text-2xl font-bold text-orange-600 dark:text-orange-400">
            {channels.filter((c: any) => c.priority === 'HIGH').length}
          </div>
          <div className="text-xs text-gray-500 dark:text-gray-400">عالية الأولوية</div>
        </div>
      </div>

      <div className="card">
        {/* Filters */}
        <div className="flex flex-col md:flex-row gap-3 mb-4">
          <div className="relative flex-1">
            <Search className="absolute right-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
            <input
              type="text"
              value={search}
              onChange={(e) => { setSearch(e.target.value); setPage(1); }}
              placeholder="بحث في القنوات..."
              className="input-field pr-10"
            />
          </div>
          <select
            value={statusFilter}
            onChange={(e) => { setStatusFilter(e.target.value); setPage(1); }}
            className="input-field md:w-40"
          >
            <option value="">كل الحالات</option>
            <option value="ACTIVE">نشط</option>
            <option value="ARCHIVED">مؤرشف</option>
            <option value="CLOSED">مغلق</option>
          </select>
          <select
            value={priorityFilter}
            onChange={(e) => { setPriorityFilter(e.target.value); setPage(1); }}
            className="input-field md:w-40"
          >
            <option value="">كل الأولويات</option>
            <option value="LOW">منخفضة</option>
            <option value="MEDIUM">متوسطة</option>
            <option value="HIGH">عالية</option>
            <option value="URGENT">عاجلة</option>
          </select>
        </div>

        {isLoading ? (
          <div className="text-center py-8">
            <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
            <p className="text-gray-500 dark:text-gray-400 mt-2">جاري التحميل...</p>
          </div>
        ) : channels.length === 0 ? (
          <div className="text-center py-12">
            <FolderKanban className="w-12 h-12 text-gray-300 dark:text-gray-600 mx-auto mb-3" />
            <p className="text-gray-500 dark:text-gray-400">لا توجد قنوات بعد</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-gray-200 dark:border-gray-700 text-right text-sm text-gray-500 dark:text-gray-400">
                  <th className="pb-3 pr-4 font-medium cursor-pointer" onClick={() => handleSort('name')}>
                    <div className="flex items-center gap-1">اسم القناة <ArrowUpDown className="w-3 h-3" /></div>
                  </th>
                  <th className="pb-3 font-medium cursor-pointer" onClick={() => handleSort('channel_type')}>
                    <div className="flex items-center gap-1">النوع <ArrowUpDown className="w-3 h-3" /></div>
                  </th>
                  <th className="pb-3 font-medium">الحالة</th>
                  <th className="pb-3 font-medium cursor-pointer" onClick={() => handleSort('priority')}>
                    <div className="flex items-center gap-1">الأولوية <ArrowUpDown className="w-3 h-3" /></div>
                  </th>
                  <th className="pb-3 font-medium">الأعضاء</th>
                  <th className="pb-3 font-medium">دورك</th>
                  <th className="pb-3 pl-4 font-medium cursor-pointer" onClick={() => handleSort('created_at')}>
                    <div className="flex items-center gap-1">التاريخ <ArrowUpDown className="w-3 h-3" /></div>
                  </th>
                </tr>
              </thead>
              <tbody>
                {channels.map((channel: any) => (
                  <tr
                    key={channel.id}
                    className="border-b border-gray-100 dark:border-gray-700/50 hover:bg-gray-50 dark:hover:bg-gray-700/30 transition-colors"
                  >
                    <td className="py-3 pr-4">
                      <Link
                        to={`/channels/${channel.id}`}
                        className="font-medium text-gray-900 dark:text-white hover:text-primary-600 dark:hover:text-primary-400"
                      >
                        {channel.name}
                      </Link>
                      <p className="text-xs text-gray-500 dark:text-gray-400">{channel.description}</p>
                    </td>
                    <td className="text-sm text-gray-600 dark:text-gray-300">{channel.channel_type_display}</td>
                    <td>
                      <span className={`badge ${
                        channel.status === 'ACTIVE' ? 'badge-success' :
                        channel.status === 'ARCHIVED' ? 'badge-warning' : 'badge-danger'
                      }`}>
                        {channel.status_display}
                      </span>
                    </td>
                    <td>
                      <span className={`badge ${
                        channel.priority === 'URGENT' ? 'badge-danger' :
                        channel.priority === 'HIGH' ? 'badge-warning' : 'badge-info'
                      }`}>
                        {channel.priority}
                      </span>
                    </td>
                    <td className="text-sm text-gray-600 dark:text-gray-300">{channel.members_count || 0}</td>
                    <td className="text-sm text-gray-600 dark:text-gray-300">{channel.current_user_role || '—'}</td>
                    <td className="pl-4 text-sm text-gray-500 dark:text-gray-400">
                      {new Date(channel.created_at).toLocaleDateString('ar-SA')}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="flex items-center justify-between mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
            <p className="text-sm text-gray-500 dark:text-gray-400">
              إجمالي: {totalCount} • صفحة {currentPage} من {totalPages}
            </p>
            <div className="flex gap-2">
              <button
                onClick={() => setPage(p => Math.max(1, p - 1))}
                disabled={page <= 1}
                className="btn-secondary px-3 py-1 disabled:opacity-50"
              >
                <ChevronRight className="w-4 h-4" />
              </button>
              <button
                onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                disabled={page >= totalPages}
                className="btn-secondary px-3 py-1 disabled:opacity-50"
              >
                <ChevronLeft className="w-4 h-4" />
              </button>
            </div>
          </div>
        )}
      </div>

      {showCreate && (
        <CreateChannelModal
          patients={patients}
          onSubmit={(data: any) => createMutation.mutate(data)}
          onClose={() => setShowCreate(false)}
          loading={createMutation.isPending}
        />
      )}
    </div>
  );
}

function CreateChannelModal({ patients, onSubmit, onClose, loading }: any) {
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    channel_type: 'OUTPATIENT',
    priority: 'MEDIUM',
    patient: '',
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit(formData);
  };

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-xl w-full max-w-md p-6">
        <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-4">إنشاء قناة جديدة</h2>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              اسم القناة
            </label>
            <input
              type="text"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              required
              className="input-field"
              placeholder="مثال: حالة طارئة - أحمد محمد"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              المريض
            </label>
            <select
              value={formData.patient}
              onChange={(e) => setFormData({ ...formData, patient: e.target.value })}
              required
              className="input-field"
            >
              <option value="">اختر المريض</option>
              {patients.map((p: any) => (
                <option key={p.id} value={p.id}>
                  {p.full_name} - {p.date_of_birth}
                </option>
              ))}
            </select>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                النوع
              </label>
              <select
                value={formData.channel_type}
                onChange={(e) => setFormData({ ...formData, channel_type: e.target.value })}
                className="input-field"
              >
                <option value="EMERGENCY">طارئة</option>
                <option value="INPATIENT">مقيم</option>
                <option value="OUTPATIENT">خارجي</option>
                <option value="CONSULTATION">استشارة</option>
                <option value="FOLLOW_UP">متابعة</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                الأولوية
              </label>
              <select
                value={formData.priority}
                onChange={(e) => setFormData({ ...formData, priority: e.target.value })}
                className="input-field"
              >
                <option value="LOW">منخفضة</option>
                <option value="MEDIUM">متوسطة</option>
                <option value="HIGH">عالية</option>
                <option value="URGENT">عاجلة</option>
              </select>
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              الوصف
            </label>
            <textarea
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              rows={3}
              className="input-field"
              placeholder="معلومات أولية عن الحالة..."
            />
          </div>
          <div className="flex gap-2 pt-2">
            <button type="submit" disabled={loading} className="btn-primary flex-1">
              {loading ? 'جاري الإنشاء...' : 'إنشاء'}
            </button>
            <button type="button" onClick={onClose} className="btn-secondary flex-1">
              إلغاء
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
