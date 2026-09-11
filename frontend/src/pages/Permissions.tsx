import { useEffect, useMemo, useState } from 'react';
import { permissionsAPI } from '../api/client';
import PageHeader from '../components/common/PageHeader';
import Card from '../components/common/Card';
import { ShieldCheck, RefreshCw, Users, Lock, RotateCcw, Loader2 } from 'lucide-react';
import toast from 'react-hot-toast';

interface PermissionDef {
  code: string;
  label: string;
  category: string;
}

interface CellState {
  default: boolean;
  effective: boolean;
  overridden: boolean;
}

interface MatrixResponse {
  permissions: PermissionDef[];
  roles: { value: string; label: string }[];
  matrix: Record<string, Record<string, CellState>>;
}

/**
 * إدارة الصلاحيات (متطلب د. مجد): مصفوفة أدوار × صلاحيات ديناميكية.
 * كل تغيير يسجل تجاوزاً في الخادم مع تدقيق الحدث، ويسري فوراً.
 */
export const PermissionsManagement = () => {
  const [data, setData] = useState<MatrixResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeRole, setActiveRole] = useState<string>('DOCTOR');
  const [pending, setPending] = useState<string | null>(null);

  const load = async () => {
    setLoading(true);
    try {
      const res = await permissionsAPI.matrix();
      setData(res.data);
      if (res.data?.roles?.length && !res.data.roles.some((r: { value: string }) => r.value === activeRole)) {
        setActiveRole(res.data.roles[0].value);
      }
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'فشل تحميل مصفوفة الصلاحيات');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const grouped = useMemo(() => {
    if (!data) return [] as [string, PermissionDef[]][];
    const byCategory: Record<string, PermissionDef[]> = {};
    for (const p of data.permissions) {
      (byCategory[p.category] ||= []).push(p);
    }
    return Object.entries(byCategory);
  }, [data]);

  const activeRoleLabel = data?.roles.find((r) => r.value === activeRole)?.label ?? activeRole;
  const isSuperAdmin = activeRole === 'SUPER_ADMIN';

  const setPermission = async (permission: string, allowed: boolean) => {
    setPending(permission);
    try {
      await permissionsAPI.set(activeRole, permission, allowed);
      toast.success(allowed ? 'تم منح الصلاحية' : 'تم سحب الصلاحية');
      await load();
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'فشل تحديث الصلاحية');
    } finally {
      setPending(null);
    }
  };

  const resetPermission = async (permission: string) => {
    setPending(permission);
    try {
      await permissionsAPI.reset(activeRole, permission);
      toast.success('أُعيدت الصلاحية للوضع الافتراضي');
      await load();
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'فشل إعادة الصلاحية');
    } finally {
      setPending(null);
    }
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 animate-in fade-in duration-300">
      <PageHeader
        title="إدارة الصلاحيات"
        description="مصفوفة صلاحيات الأدوار: المنح والسحب يسريان فوراً ويُدقَّق كل تغيير في سجل التدقيق"
        icon={<ShieldCheck className="w-8 h-8 text-primary-500" />}
      >
        <button
          onClick={load}
          disabled={loading}
          className="flex items-center gap-2 px-4 py-2 text-sm font-medium bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl hover:bg-gray-50 dark:hover:bg-gray-700/50 text-gray-700 dark:text-gray-200 transition-colors shadow-sm"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin text-primary-500' : ''}`} />
          تحديث
        </button>
      </PageHeader>

      {/* Role selector */}
      <Card className="p-4">
        <div className="flex items-center gap-2 mb-3 text-sm font-semibold text-gray-700 dark:text-gray-200">
          <Users className="w-4 h-4 text-primary-500" />
          اختر الدور
        </div>
        <div className="flex flex-wrap gap-2">
          {(data?.roles ?? []).map((r) => (
            <button
              key={r.value}
              onClick={() => setActiveRole(r.value)}
              className={`px-3 py-1.5 text-xs font-semibold rounded-full border transition-colors ${
                activeRole === r.value
                  ? 'bg-primary-600 text-white border-primary-600'
                  : 'bg-white dark:bg-gray-800 border-gray-200 dark:border-gray-700 text-gray-600 dark:text-gray-300 hover:border-primary-300'
              }`}
            >
              {r.label}
              {r.value === 'SUPER_ADMIN' && ' 🔒'}
            </button>
          ))}
        </div>
        {isSuperAdmin && (
          <p className="mt-3 text-xs text-amber-600 dark:text-amber-300 flex items-center gap-1.5">
            <Lock className="w-3.5 h-3.5" />
            مدير النظام الأعلى يملك كل الصلاحيات دائماً — لا يمكن تقييده حمايةً من إغلاق الإدارة لنفسها.
          </p>
        )}
      </Card>

      {/* Permission matrix for the selected role */}
      <Card className="overflow-hidden p-0">
        <div className="px-6 py-4 border-b border-gray-100 dark:border-gray-700/60 flex items-center justify-between flex-wrap gap-2">
          <h3 className="font-semibold text-gray-900 dark:text-white">
            صلاحيات دور: <span className="text-primary-600 dark:text-primary-400">{activeRoleLabel}</span>
          </h3>
          <span className="text-xs text-gray-500 dark:text-gray-400">
            «الافتراضي» هو الوضع المعرّف في النظام — التبديل ينشئ تجاوزاً ديناميكياً
          </span>
        </div>

        {loading ? (
          <div className="py-16 text-center text-gray-500">
            <Loader2 className="w-6 h-6 animate-spin mx-auto mb-2 text-primary-500" />
            جاري تحميل المصفوفة...
          </div>
        ) : (
          <div className="divide-y divide-gray-100 dark:divide-gray-700/40">
            {grouped.map(([category, perms]) => (
              <div key={category} className="px-6 py-4">
                <h4 className="text-xs font-bold text-gray-400 dark:text-gray-500 uppercase tracking-wider mb-3">
                  {category}
                </h4>
                <div className="space-y-2">
                  {perms.map((p) => {
                    const cell: CellState | undefined = data?.matrix?.[activeRole]?.[p.code];
                    if (!cell) return null;
                    return (
                      <div
                        key={p.code}
                        className="flex items-center justify-between gap-3 py-2 px-3 rounded-xl bg-gray-50/60 dark:bg-gray-900/30"
                      >
                        <div className="min-w-0">
                          <div className="text-sm font-medium text-gray-800 dark:text-gray-100 flex items-center gap-2">
                            {p.label}
                            {cell.overridden && (
                              <span className="text-[10px] font-semibold bg-indigo-50 dark:bg-indigo-900/40 text-indigo-600 dark:text-indigo-300 px-2 py-0.5 rounded-full">
                                تجاوز ديناميكي
                              </span>
                            )}
                          </div>
                          <div className="text-[11px] text-gray-400 font-mono" dir="ltr">
                            {p.code} — الافتراضي: {cell.default ? 'مسموح' : 'ممنوع'}
                          </div>
                        </div>
                        <div className="flex items-center gap-2 shrink-0">
                          {cell.overridden && !isSuperAdmin && (
                            <button
                              onClick={() => resetPermission(p.code)}
                              disabled={pending === p.code}
                              title="العودة إلى الوضع الافتراضي"
                              className="p-2 rounded-lg text-gray-500 hover:text-primary-600 hover:bg-primary-50 dark:hover:bg-primary-900/30 transition-colors disabled:opacity-50"
                            >
                              <RotateCcw className="w-4 h-4" />
                            </button>
                          )}
                          <button
                            onClick={() => setPermission(p.code, !cell.effective)}
                            disabled={isSuperAdmin || pending === p.code}
                            role="switch"
                            aria-checked={cell.effective}
                            className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors disabled:opacity-60 ${
                              cell.effective ? 'bg-emerald-600' : 'bg-gray-300 dark:bg-gray-600'
                            }`}
                          >
                            <span
                              className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                                cell.effective ? 'translate-x-1' : '-translate-x-6'
                              }`}
                            />
                          </button>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            ))}
          </div>
        )}
      </Card>
    </div>
  );
};

export default PermissionsManagement;
