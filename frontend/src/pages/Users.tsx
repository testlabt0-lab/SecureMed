import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { UserPlus, Search, Users as UsersIcon, Shield, Pencil, Power } from 'lucide-react';
import { motion } from 'framer-motion';
import { usersAPI, basinsAPI } from '../api/client';
import { useAuthStore } from '../store/authStore';
import toast from 'react-hot-toast';

const roleLabels: Record<string, string> = {
  SUPER_ADMIN: 'مدير النظام',
  HOSPITAL_ADMIN: 'مدير المستشفى',
  CENTER_ADMIN: 'مدير مركز',
  DOCTOR: 'طبيب',
  NURSE: 'ممرض',
  LAB_TECH: 'فني مختبر',
  PHARMACIST: 'صيدلي',
  AUDITOR: 'مراجع أمني',
  PATIENT: 'مريض',
  ACCOUNTANT: 'محاسب',
  RECEPTIONIST: 'موظف استقبال',
};

export default function Users() {
  const { user: currentUser } = useAuthStore();
  const [search, setSearch] = useState('');
  const [roleFilter, setRoleFilter] = useState('');
  const [showCreate, setShowCreate] = useState(false);
  const [editing, setEditing] = useState<any>(null);
  const queryClient = useQueryClient();

  const { data: basinsData } = useQuery({
    queryKey: ['basins'],
    queryFn: () => basinsAPI.list(),
  });
  const basins = Array.isArray(basinsData?.data?.results) ? basinsData.data.results : (Array.isArray(basinsData?.data) ? basinsData.data : []);

  const { data: usersData, isLoading } = useQuery({
    queryKey: ['users', { search, role: roleFilter }],
    queryFn: () => usersAPI.list({ search, role: roleFilter }),
  });

  const createMutation = useMutation({
    mutationFn: (data: any) => usersAPI.create(data),
    onSuccess: () => {
      toast.success('تم إنشاء المستخدم بنجاح');
      queryClient.invalidateQueries({ queryKey: ['users'] });
      setShowCreate(false);
    },
    onError: (err: any) => toast.error(err.response?.data?.detail || 'فشل'),
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: any) => usersAPI.update(id, data),
    onSuccess: () => {
      toast.success('تم حفظ التعديلات');
      queryClient.invalidateQueries({ queryKey: ['users'] });
      setEditing(null);
    },
    onError: (err: any) => toast.error(err.response?.data?.detail || 'فشل الحفظ'),
  });

  const deactivateMutation = useMutation({
    mutationFn: (id: string) => usersAPI.deactivate(id),
    onSuccess: () => {
      toast.success('تم إلغاء تفعيل المستخدم');
      queryClient.invalidateQueries({ queryKey: ['users'] });
    },
  });

  const activateMutation = useMutation({
    mutationFn: (id: string) => usersAPI.activate(id),
    onSuccess: () => {
      toast.success('تم تفعيل المستخدم');
      queryClient.invalidateQueries({ queryKey: ['users'] });
    },
  });

  const users = Array.isArray(usersData?.data?.results) ? usersData.data.results : (Array.isArray(usersData?.data) ? usersData.data : []);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">إدارة المستخدمين</h1>
          <p className="text-gray-600 dark:text-gray-400 text-sm mt-1">إدارة الحسابات والأدوار والصلاحيات (RBAC)</p>
        </div>
        <button onClick={() => setShowCreate(true)} className="btn-primary flex items-center gap-2">
          <UserPlus className="w-4 h-4" />
          مستخدم جديد
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
              placeholder="بحث عن مستخدم..."
              className="input-field pr-10"
            />
          </div>
          <select
            value={roleFilter}
            onChange={(e) => setRoleFilter(e.target.value)}
            className="input-field md:w-48"
          >
            <option value="">كل الأدوار</option>
            {Object.entries(roleLabels).map(([key, label]) => (
              <option key={key} value={key}>{label}</option>
            ))}
          </select>
        </div>

        {isLoading ? (
          <div className="text-center py-8 text-gray-500">جاري التحميل...</div>
        ) : users.length === 0 ? (
          <div className="text-center py-12">
            <UsersIcon className="w-12 h-12 text-gray-300 mx-auto mb-3" />
            <p className="text-gray-500">لا يوجد مستخدمون</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-gray-200 dark:border-gray-700 text-right text-sm text-gray-500">
                  <th className="pb-3 pr-4 font-medium">الاسم</th>
                  <th className="pb-3 font-medium">البريد</th>
                  <th className="pb-3 font-medium">الدور</th>
                  <th className="pb-3 font-medium">الحوض</th>
                  <th className="pb-3 font-medium">الحالة</th>
                  <th className="pb-3 pl-4 font-medium">الإجراءات</th>
                </tr>
              </thead>
              <tbody>
                {users.map((u: any, index: number) => (
                  <motion.tr 
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: index * 0.05, duration: 0.2 }}
                    key={u.id} 
                    className="border-b border-gray-100 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700/50"
                  >
                    <td className="py-3 pr-4">
                      <div className="flex items-center gap-3">
                        <div className="w-9 h-9 bg-indigo-100 dark:bg-indigo-900/30 rounded-full flex items-center justify-center">
                          <span className="text-indigo-700 dark:text-indigo-400 text-sm font-medium">
                            {u.full_name?.charAt(0) || '?'}
                          </span>
                        </div>
                        <div>
                          <p className="font-medium text-gray-900 dark:text-white">{u.full_name}</p>
                          <p className="text-xs text-gray-500">{u.department || ''}</p>
                        </div>
                      </div>
                    </td>
                    <td className="text-sm">{u.email}</td>
                    <td>
                      <span className="inline-flex items-center rounded-full bg-blue-50 px-2.5 py-0.5 text-xs font-medium text-blue-700 ring-1 ring-inset ring-blue-700/10 dark:bg-blue-900/30 dark:text-blue-300 dark:ring-blue-900/50">
                        {roleLabels[u.role]}
                      </span>
                    </td>
                    <td className="text-xs text-gray-500">
                      {u.basin_name || '—'}
                    </td>
                    <td>
                      {u.is_active ? (
                        <span className="inline-flex items-center rounded-full bg-emerald-50 px-2.5 py-0.5 text-xs font-medium text-emerald-700 ring-1 ring-inset ring-emerald-600/20 dark:bg-emerald-900/30 dark:text-emerald-400 dark:ring-emerald-900/50">نشط</span>
                      ) : (
                        <span className="inline-flex items-center rounded-full bg-red-50 px-2.5 py-0.5 text-xs font-medium text-red-700 ring-1 ring-inset ring-red-600/10 dark:bg-red-900/30 dark:text-red-400 dark:ring-red-900/50">موقوف</span>
                      )}
                    </td>
                    <td className="pl-4">
                      <div className="flex gap-1 justify-end">
                        <button
                          onClick={() => setEditing(u)}
                          className="p-2 hover:bg-indigo-50 dark:hover:bg-indigo-900/30 rounded-lg transition-colors"
                          title="تعديل"
                        >
                          <Pencil className="w-4 h-4 text-indigo-600 dark:text-indigo-400" />
                        </button>
                        {u.is_active ? (
                          u.id !== currentUser?.id && (
                            <button
                              onClick={() => {
                                if (confirm('هل تريد إلغاء تفعيل هذا المستخدم؟')) deactivateMutation.mutate(u.id);
                              }}
                              className="p-2 hover:bg-red-50 dark:hover:bg-red-900/30 rounded-lg transition-colors"
                              title="إيقاف"
                            >
                              <Power className="w-4 h-4 text-red-500" />
                            </button>
                          )
                        ) : (
                          <button
                            onClick={() => activateMutation.mutate(u.id)}
                            className="p-2 hover:bg-emerald-50 dark:hover:bg-emerald-900/30 rounded-lg transition-colors"
                            title="تفعيل"
                          >
                            <Power className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
                          </button>
                        )}
                      </div>
                    </td>
                  </motion.tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {showCreate && (
        <CreateUserModal
          basins={basins}
          onSubmit={(data: any) => createMutation.mutate(data)}
          onClose={() => setShowCreate(false)}
          loading={createMutation.isPending}
        />
      )}

      {editing && (
        <EditUserModal
          user={editing}
          basins={basins}
          onSubmit={(data: any) => updateMutation.mutate({ id: editing.id, data })}
          onClose={() => setEditing(null)}
          loading={updateMutation.isPending}
        />
      )}
    </div>
  );
}

function BasinSelect({ basins, value, onChange }: any) {
  return (
    <select className="input-field" value={value || ''} onChange={onChange}>
      <option value="">— بدون حوض (عام) —</option>
      {(Array.isArray(basins) ? basins : []).map((b: any) => (
        <option key={b.id} value={b.id}>
          {b.name} ({b.basin_type_display || b.basin_type})
        </option>
      ))}
    </select>
  );
}

function CreateUserModal({ onSubmit, onClose, loading, basins }: any) {
  const [formData, setFormData] = useState({
    email: '',
    full_name: '',
    phone: '',
    role: 'DOCTOR',
    license_number: '',
    department: '',
    specialization: '',
    basin: '',
    password: '',
    password_confirm: '',
  });

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4 overflow-y-auto">
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-xl w-full max-w-lg p-6 my-8 max-h-[90vh] overflow-y-auto">
        <h2 className="text-xl font-bold mb-4">إضافة مستخدم جديد</h2>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            onSubmit({ ...formData, basin: formData.basin || null });
          }}
          className="space-y-4"
        >
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">الاسم الكامل</label>
              <input
                type="text"
                value={formData.full_name}
                onChange={(e) => setFormData({ ...formData, full_name: e.target.value })}
                required
                className="input-field"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">البريد الإلكتروني</label>
              <input
                type="email"
                value={formData.email}
                onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                required
                className="input-field"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">الدور</label>
              <select
                value={formData.role}
                onChange={(e) => setFormData({ ...formData, role: e.target.value })}
                className="input-field"
              >
                {Object.entries(roleLabels).map(([key, label]) => (
                  <option key={key} value={key}>{label}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">الحوض الصحي</label>
              <BasinSelect
                basins={basins}
                value={formData.basin}
                onChange={(e: any) => setFormData({ ...formData, basin: e.target.value })}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">الهاتف</label>
              <input
                type="text"
                value={formData.phone}
                onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                className="input-field"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">رقم الترخيص</label>
              <input
                type="text"
                value={formData.license_number}
                onChange={(e) => setFormData({ ...formData, license_number: e.target.value })}
                className="input-field"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">القسم</label>
              <input
                type="text"
                value={formData.department}
                onChange={(e) => setFormData({ ...formData, department: e.target.value })}
                className="input-field"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">التخصص</label>
              <input
                type="text"
                value={formData.specialization}
                onChange={(e) => setFormData({ ...formData, specialization: e.target.value })}
                className="input-field"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">كلمة المرور</label>
              <input
                type="password"
                value={formData.password}
                onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                required
                minLength={12}
                className="input-field"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">تأكيد كلمة المرور</label>
              <input
                type="password"
                value={formData.password_confirm}
                onChange={(e) => setFormData({ ...formData, password_confirm: e.target.value })}
                required
                minLength={12}
                className="input-field"
              />
            </div>
          </div>
          <div className="flex gap-2 pt-2">
            <button type="submit" disabled={loading} className="btn-primary flex-1">
              {loading ? 'جاري الإنشاء...' : 'إنشاء المستخدم'}
            </button>
            <button type="button" onClick={onClose} className="btn-secondary flex-1">إلغاء</button>
          </div>
        </form>
      </div>
    </div>
  );
}

function EditUserModal({ user, basins, onSubmit, onClose, loading }: any) {
  const [formData, setFormData] = useState({
    full_name: user.full_name || '',
    phone: user.phone || '',
    role: user.role || 'DOCTOR',
    department: user.department || '',
    specialization: user.specialization || '',
    license_number: user.license_number || '',
    basin: user.basin || '',
  });

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4 overflow-y-auto">
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-xl w-full max-w-lg p-6 my-8 max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between mb-1">
          <h2 className="text-xl font-bold">تعديل المستخدم</h2>
          <span className="text-xs text-gray-400 font-mono">{user.email}</span>
        </div>
        <p className="text-xs text-gray-500 mb-4">
          تغيير الدور يعيد تعيين صلاحيات المستخدم فوراً في كل القنوات النظامية
        </p>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            onSubmit({ ...formData, basin: formData.basin || null });
          }}
          className="space-y-4"
        >
          <div className="grid grid-cols-2 gap-3">
            <div className="col-span-2">
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">الاسم الكامل</label>
              <input
                type="text"
                value={formData.full_name}
                onChange={(e) => setFormData({ ...formData, full_name: e.target.value })}
                required
                className="input-field"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">الدور</label>
              <select
                value={formData.role}
                onChange={(e) => setFormData({ ...formData, role: e.target.value })}
                className="input-field"
              >
                {Object.entries(roleLabels).map(([key, label]) => (
                  <option key={key} value={key}>{label}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">الحوض الصحي</label>
              <BasinSelect
                basins={basins}
                value={formData.basin}
                onChange={(e: any) => setFormData({ ...formData, basin: e.target.value })}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">الهاتف</label>
              <input
                type="text"
                value={formData.phone}
                onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                className="input-field"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">رقم الترخيص</label>
              <input
                type="text"
                value={formData.license_number}
                onChange={(e) => setFormData({ ...formData, license_number: e.target.value })}
                className="input-field"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">القسم</label>
              <input
                type="text"
                value={formData.department}
                onChange={(e) => setFormData({ ...formData, department: e.target.value })}
                className="input-field"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">التخصص</label>
              <input
                type="text"
                value={formData.specialization}
                onChange={(e) => setFormData({ ...formData, specialization: e.target.value })}
                className="input-field"
              />
            </div>
          </div>
          <div className="flex gap-2 pt-2">
            <button type="submit" disabled={loading} className="btn-primary flex-1">
              {loading ? 'جاري الحفظ...' : 'حفظ التعديلات'}
            </button>
            <button type="button" onClick={onClose} className="btn-secondary flex-1">إلغاء</button>
          </div>
        </form>
      </div>
    </div>
  );
}
