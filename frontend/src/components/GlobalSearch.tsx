import { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Search, User, FolderKanban, HeartPulse, Loader2, X } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { searchApi } from '../api/extendedApis';

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

const channelTypes: Record<string, string> = {
  EMERGENCY: 'حالة طارئة',
  INPATIENT: 'مريض مقيم',
  OUTPATIENT: 'مريض خارجي',
  CONSULTATION: 'استشارة',
  FOLLOW_UP: 'متابعة',
};

export default function GlobalSearch({ open, onClose }: { open: boolean; onClose: () => void }) {
  const navigate = useNavigate();
  const [q, setQ] = useState('');
  const [debounced, setDebounced] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const t = setTimeout(() => setDebounced(q.trim()), 250);
    return () => clearTimeout(t);
  }, [q]);

  useEffect(() => {
    if (open) {
      setQ('');
      setDebounced('');
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [open]);

  // Ctrl+K global shortcut
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        onClose();
      }
      if (e.key === 'Escape') onClose();
    };
    if (open) window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [open, onClose]);

  const { data, isFetching } = useQuery({
    queryKey: ['global-search', debounced],
    queryFn: () => searchApi.query(debounced),
    enabled: open && debounced.length >= 2,
  });

  if (!open) return null;

  const results = data?.data;
  const go = (path: string) => {
    onClose();
    navigate(path);
  };

  const Section = ({ title, icon: Icon, children, count }: any) =>
    count > 0 ? (
      <div className="mb-3">
        <p className="flex items-center gap-2 text-xs font-bold text-gray-400 px-2 mb-1">
          <Icon className="w-3.5 h-3.5" />
          {title}
        </p>
        <div className="space-y-1">{children}</div>
      </div>
    ) : null;

  return (
    <div
      className="fixed inset-0 bg-black/50 z-[60] flex items-start justify-center pt-[10vh] p-4"
      onClick={onClose}
    >
      <div
        className="bg-white dark:bg-gray-800 rounded-2xl shadow-2xl w-full max-w-xl overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Search input */}
        <div className="flex items-center gap-3 px-4 border-b border-gray-200 dark:border-gray-700">
          <Search className="w-5 h-5 text-gray-400" />
          <input
            ref={inputRef}
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="ابحث عن مرضى، قنوات، مستخدمين..."
            className="flex-1 py-4 bg-transparent outline-none text-gray-900 dark:text-white placeholder:text-gray-400"
          />
          {isFetching && <Loader2 className="w-4 h-4 animate-spin text-primary-500" />}
          <button onClick={onClose} className="p-1 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg">
            <X className="w-4 h-4 text-gray-400" />
          </button>
        </div>

        {/* Results */}
        <div className="max-h-[55vh] overflow-y-auto p-3">
          {debounced.length < 2 ? (
            <p className="text-center text-sm text-gray-400 py-8">
              اكتب حرفين على الأقل للبحث الشامل
            </p>
          ) : results && results.total === 0 ? (
            <p className="text-center text-sm text-gray-400 py-8">
              لا توجد نتائج مطابقة لـ «{debounced}»
            </p>
          ) : (
            <>
              <Section title="المرضى" icon={HeartPulse} count={results?.patients?.length || 0}>
                {results?.patients?.map((p: any) => (
                  <button
                    key={p.id}
                    onClick={() => go(`/patients/${p.id}`)}
                    className="w-full flex items-center gap-3 p-2.5 rounded-lg hover:bg-primary-50 dark:hover:bg-gray-700 text-right"
                  >
                    <div className="w-8 h-8 rounded-full bg-medical-100 text-medical-600 flex items-center justify-center text-sm font-bold">
                      {p.full_name?.charAt(0)}
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-gray-900 dark:text-white truncate">{p.full_name}</p>
                      <p className="text-xs text-gray-400">هوية: {p.national_id || '—'}</p>
                    </div>
                  </button>
                ))}
              </Section>

              <Section title="القنوات والحالات" icon={FolderKanban} count={results?.channels?.length || 0}>
                {results?.channels?.map((c: any) => (
                  <button
                    key={c.id}
                    onClick={() => go(`/channels/${c.id}`)}
                    className="w-full flex items-center gap-3 p-2.5 rounded-lg hover:bg-primary-50 dark:hover:bg-gray-700 text-right"
                  >
                    <div className="w-8 h-8 rounded-lg bg-primary-100 text-primary-600 flex items-center justify-center">
                      <FolderKanban className="w-4 h-4" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-gray-900 dark:text-white truncate">{c.name}</p>
                      <p className="text-xs text-gray-400">{channelTypes[c.channel_type] || c.channel_type}</p>
                    </div>
                  </button>
                ))}
              </Section>

              <Section title="المستخدمون" icon={User} count={results?.users?.length || 0}>
                {results?.users?.map((u: any) => (
                  <button
                    key={u.id}
                    onClick={() => go(`/users`)}
                    className="w-full flex items-center gap-3 p-2.5 rounded-lg hover:bg-primary-50 dark:hover:bg-gray-700 text-right"
                  >
                    <div className="w-8 h-8 rounded-full bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 flex items-center justify-center text-sm font-bold">
                      {u.full_name?.charAt(0)}
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-gray-900 dark:text-white truncate">{u.full_name}</p>
                      <p className="text-xs text-gray-400 truncate">{u.email} — {roleLabels[u.role] || u.role}</p>
                    </div>
                  </button>
                ))}
              </Section>
            </>
          )}
        </div>

        {/* Footer hint */}
        <div className="px-4 py-2.5 border-t border-gray-200 dark:border-gray-700 flex items-center justify-between text-xs text-gray-400">
          <span>Enter للتنقل • Esc للإغلاق</span>
          <span className="flex items-center gap-1">
            <kbd className="px-1.5 py-0.5 bg-gray-100 dark:bg-gray-700 rounded text-[10px]">Ctrl</kbd>
            +
            <kbd className="px-1.5 py-0.5 bg-gray-100 dark:bg-gray-700 rounded text-[10px]">K</kbd>
          </span>
        </div>
      </div>
    </div>
  );
}
