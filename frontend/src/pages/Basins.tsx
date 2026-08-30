import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Building2, Plus, MapPin, Phone, BedDouble, RefreshCw,
  Hospital, Activity, Pencil, Trash2, Power,
} from 'lucide-react';
import { basinsAPI } from '../api/client';
import { useAuthStore } from '../store/authStore';
import toast from 'react-hot-toast';

const typeLabels: Record<string, string> = {
  GENERAL_HOSPITAL: 'مستشفى عام',
  SPECIALIZED_HOSPITAL: 'مستشفى تخصصي',
  RURAL_HOSPITAL: 'مستشفى ريفي',
  HEALTH_CENTER: 'مركز صحي',
  HEALTH_UNIT: 'وحدة صحية',
  DIALYSIS_CENTER: 'مركز غسيل كلوي',
  SPECIALIZED_CLINIC: 'مركز/عيادة تخصصية',
};

const typeColors: Record<string, string> = {
  GENERAL_HOSPITAL: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',
  SPECIALIZED_HOSPITAL: 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400',
  RURAL_HOSPITAL: 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400',
  HEALTH_CENTER: 'bg-primary-100 text-primary-700 dark:bg-primary-900/30 dark:text-primary-400',
  HEALTH_UNIT: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400',
  DIALYSIS_CENTER: 'bg-sky-100 text-sky-700 dark:bg-sky-900/30 dark:text-sky-400',
  SPECIALIZED_CLINIC: 'bg-pink-100 text-pink-700 dark:bg-pink-900/30 dark:text-pink-400',
};

export default function Basins() {
  const { user } = useAuthStore();
  const isAdmin = user?.role === 'SUPER_ADMIN' || user?.role === 'HOSPITAL_ADMIN';
  const isSuper = user?.role === 'SUPER_ADMIN';
  const queryClient = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState<any>(null);

  const { data, isLoading } = useQuery({
    queryKey: ['basins'],
    queryFn: () => basinsAPI.list(),
  });

  const { data: overviewData } = useQuery({
    queryKey: ['basins-overview'],
    queryFn: () => basinsAPI.overview(),
    enabled: isAdmin,
  });

  const toggleModule = useMutation({
    mutationFn: ({ id, module, enabled }: any) =>
      basinsAPI.toggleModule(id, module, enabled),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['basins'] });
      toast.success('تم تحديث الوحدات');
    },
    onError: () => toast.error('فشل التحديث'),
  });

  const applyDefaults = useMutation({
    mutationFn: (id: string) => basinsAPI.applyTypeDefaults(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['basins'] });
      toast.success('تم تفعيل الوحدات الافتراضية حسب نوع الحوض');
    },
  });

  const deleteBasin = useMutation({
    mutationFn: (id: string) => basinsAPI.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['basins'] });
      toast.success('تم حذف الحوض');
    },
    onError: (err: any) =>
      toast.error(err.response?.data?.detail || 'فشل الحذف'),
  });

  const basins = data?.data?.results || data?.data || [];
  const overview = overviewData?.data;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <Building2 className="w-7 h-7 text-primary-600" />
            الأحواز الصحية
          </h1>
          <p className="text-gray-600 dark:text-gray-400 text-sm mt-1">
            الارتباط بالأحواز وتفعيل الوحدات بحسب نوع الحوض
          </p>
        </div>
        {isSuper && (
          <button
            onClick={() => { setEditing(null); setShowForm(true); }}
            className="btn-primary flex items-center gap-2"
          >
            <Plus className="w-4 h-4" />
            حوض جديد
          </button>
        )}
      </div>

      {/* Overview cards */}
      {overview && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="card flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-primary-100 dark:bg-primary-900/30 flex items-center justify-center">
              <Building2 className="w-5 h-5 text-primary-600" />
            </div>
            <div>
              <p className="text-2xl font-bold">{overview.total}</p>
              <p className="text-xs text-gray-500">إجمالي الأحواز</p>
            </div>
          </div>
          <div className="card flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-emerald-100 dark:bg-emerald-900/30 flex items-center justify-center">
              <Activity className="w-5 h-5 text-emerald-600" />
            </div>
            <div>
              <p className="text-2xl font-bold">{overview.active}</p>
              <p className="text-xs text-gray-500">أحواز نشطة</p>
            </div>
          </div>
          {Object.entries(overview.by_type || {}).slice(0, 2).map(([t, count]: any) => (
            <div key={t} className="card flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-gray-100 dark:bg-gray-700 flex items-center justify-center">
                <Hospital className="w-5 h-5 text-gray-600 dark:text-gray-300" />
              </div>
              <div>
                <p className="text-2xl font-bold">{count}</p>
                <p className="text-xs text-gray-500">{typeLabels[t] || t}</p>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Basin cards */}
      {isLoading ? (
        <div className="text-center py-12 text-gray-500">جاري التحميل...</div>
      ) : basins.length === 0 ? (
        <div className="card text-center py-12">
          <Building2 className="w-12 h-12 text-gray-300 mx-auto mb-3" />
          <p className="text-gray-500">لا توجد أحواز مسجلة بعد</p>
        </div>
      ) : (
        <div className="grid md:grid-cols-2 gap-4">
          {basins.map((b: any) => (
            <div key={b.id} className="card space-y-4">
              <div className="flex items-start justify-between gap-2">
                <div className="flex-1">
                  <div className="flex items-center gap-2 flex-wrap">
                    <h3 className="font-bold text-lg">{b.name}</h3>
                    <span className={`badge ${typeColors[b.basin_type] || 'badge-info'}`}>
                      {b.basin_type_display}
                    </span>
                    {!b.is_active && <span className="badge badge-danger">موقوف</span>}
                  </div>
                  <p className="text-xs text-gray-500 mt-1 font-mono">{b.code}</p>
                </div>
                {isSuper && (
                  <div className="flex gap-1">
                    <button
                      onClick={() => { setEditing(b); setShowForm(true); }}
                      className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg"
                      title="تعديل"
                    >
                      <Pencil className="w-4 h-4 text-gray-500" />
                    </button>
                    <button
                      onClick={() => {
                        if (confirm(`حذف حوض «${b.name}»؟`)) deleteBasin.mutate(b.id);
                      }}
                      className="p-2 hover:bg-red-50 dark:hover:bg-red-900/30 rounded-lg"
                      title="حذف"
                    >
                      <Trash2 className="w-4 h-4 text-red-500" />
                    </button>
                  </div>
                )}
              </div>

              <div className="flex flex-wrap gap-3 text-xs text-gray-500 dark:text-gray-400">
                {b.governorate && (
                  <span className="flex items-center gap-1">
                    <MapPin className="w-3.5 h-3.5" />{b.governorate}
                    {b.directorate ? ` — ${b.directorate}` : ''}
                  </span>
                )}
                {b.phone && <span className="flex items-center gap-1"><Phone className="w-3.5 h-3.5" />{b.phone}</span>}
                {b.bed_capacity ? (
                  <span className="flex items-center gap-1"><BedDouble className="w-3.5 h-3.5" />{b.bed_capacity} أسرّة</span>
                ) : null}
              </div>

              {/* Stats row */}
              <div className="grid grid-cols-3 gap-2 text-center">
                <div className="bg-gray-50 dark:bg-gray-700/50 rounded-lg py-2">
                  <p className="font-bold text-primary-600">{b.stats?.users ?? 0}</p>
                  <p className="text-[10px] text-gray-500">مستخدمون</p>
                </div>
                <div className="bg-gray-50 dark:bg-gray-700/50 rounded-lg py-2">
                  <p className="font-bold text-medical-600">{b.stats?.patients ?? 0}</p>
                  <p className="text-[10px] text-gray-500">مرضى</p>
                </div>
                <div className="bg-gray-50 dark:bg-gray-700/50 rounded-lg py-2">
                  <p className="font-bold text-amber-600">{b.stats?.active_channels ?? 0}</p>
                  <p className="text-[10px] text-gray-500">حالات نشطة</p>
                </div>
              </div>

              {/* Module toggles */}
              <div>
                <div className="flex items-center justify-between mb-2">
                  <p className="text-xs font-medium text-gray-600 dark:text-gray-300">
                    الوحدات المفعّلة (بحسب نوع الحوض)
                  </p>
                  {isSuper && (
                    <button
                      onClick={() => applyDefaults.mutate(b.id)}
                      className="flex items-center gap-1 text-xs text-primary-600 hover:text-primary-700"
                      title="إعادة تفعيل الافتراضي حسب النوع"
                    >
                      <RefreshCw className="w-3 h-3" />
                      الافتراضي
                    </button>
                  )}
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {(b.modules_detail || []).map((m: any) => {
                    const canToggle = isSuper && b.is_active;
                    return (
                      <button
                        key={m.key}
                        disabled={!canToggle}
                        onClick={() =>
                          toggleModule.mutate({ id: b.id, module: m.key, enabled: !m.enabled })
                        }
                        className={`px-2.5 py-1 rounded-full text-xs font-medium border transition-colors ${
                          m.enabled
                            ? 'bg-emerald-50 text-emerald-700 border-emerald-200 dark:bg-emerald-900/30 dark:text-emerald-400 dark:border-emerald-800'
                            : 'bg-gray-50 text-gray-400 border-gray-200 dark:bg-gray-700/50 dark:text-gray-500 dark:border-gray-600'
                        } ${canToggle ? 'hover:border-primary-400 cursor-pointer' : 'cursor-default'}`}
                        title={canToggle ? (m.enabled ? 'انقر للتعطيل' : 'انقر للتفعيل') : undefined}
                      >
                        <Power className={`inline w-3 h-3 ml-1 ${m.enabled ? '' : 'opacity-40'}`} />
                        {m.label}
                      </button>
                    );
                  })}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {showForm && (
        <BasinFormModal
          basin={editing}
          onClose={() => setShowForm(false)}
          onSaved={() => {
            setShowForm(false);
            queryClient.invalidateQueries({ queryKey: ['basins'] });
          }}
        />
      )}
    </div>
  );
}

function BasinFormModal({ basin, onClose, onSaved }: any) {
  const isEdit = !!basin;
  const [form, setForm] = useState({
    name: basin?.name || '',
    code: basin?.code || '',
    basin_type: basin?.basin_type || 'HEALTH_CENTER',
    governorate: basin?.governorate || '',
    directorate: basin?.directorate || '',
    address: basin?.address || '',
    phone: basin?.phone || '',
    email: basin?.email || '',
    bed_capacity: basin?.bed_capacity || '',
    notes: basin?.notes || '',
  });
  const [saving, setSaving] = useState(false);

  const submit = async (e: any) => {
    e.preventDefault();
    setSaving(true);
    try {
      const payload = { ...form, bed_capacity: form.bed_capacity || null };
      if (isEdit) await basinsAPI.update(basin.id, payload);
      else await basinsAPI.create(payload);
      toast.success(isEdit ? 'تم تحديث الحوض' : 'تم إنشاء الحوض وتفعيل الوحدات الافتراضية');
      onSaved();
    } catch (err: any) {
      const detail =
        err.response?.data?.name?.[0] ||
        err.response?.data?.code?.[0] ||
        err.response?.data?.detail ||
        'فشل الحفظ';
      toast.error(String(detail));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4 overflow-y-auto">
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-xl w-full max-w-lg p-6 my-8 max-h-[90vh] overflow-y-auto">
        <h2 className="text-xl font-bold mb-1">{isEdit ? 'تعديل الحوض' : 'حوض صحي جديد'}</h2>
        <p className="text-xs text-gray-500 mb-4">
          عند إنشاء الحوض تُفعّل الوحدات تلقائياً بحسب النوع المختار
        </p>
        <form onSubmit={submit} className="space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <div className="col-span-2">
              <label className="block text-sm font-medium mb-1">اسم الحوض *</label>
              <input
                className="input-field" required value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
                placeholder="مثال: مستشفى الثورة العام"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">الرمز *</label>
              <input
                className="input-field" required value={form.code}
                onChange={(e) => setForm({ ...form, code: e.target.value.toUpperCase() })}
                placeholder="THH-SAN-01"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">نوع الحوض *</label>
              <select
                className="input-field" value={form.basin_type}
                onChange={(e) => setForm({ ...form, basin_type: e.target.value })}
              >
                {Object.entries(typeLabels).map(([k, v]) => (
                  <option key={k} value={k}>{v}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">المحافظة</label>
              <input
                className="input-field" value={form.governorate}
                onChange={(e) => setForm({ ...form, governorate: e.target.value })}
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">المديرية</label>
              <input
                className="input-field" value={form.directorate}
                onChange={(e) => setForm({ ...form, directorate: e.target.value })}
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">الهاتف</label>
              <input
                className="input-field" value={form.phone}
                onChange={(e) => setForm({ ...form, phone: e.target.value })}
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">الطاقة الاستيعابية</label>
              <input
                type="number" min="0" className="input-field" value={form.bed_capacity}
                onChange={(e) => setForm({ ...form, bed_capacity: e.target.value })}
              />
            </div>
            <div className="col-span-2">
              <label className="block text-sm font-medium mb-1">العنوان</label>
              <input
                className="input-field" value={form.address}
                onChange={(e) => setForm({ ...form, address: e.target.value })}
              />
            </div>
          </div>
          <div className="flex gap-2 pt-2">
            <button type="submit" disabled={saving} className="btn-primary flex-1">
              {saving ? 'جاري الحفظ...' : isEdit ? 'حفظ التعديلات' : 'إنشاء الحوض'}
            </button>
            <button type="button" onClick={onClose} className="btn-secondary flex-1">إلغاء</button>
          </div>
        </form>
      </div>
    </div>
  );
}
