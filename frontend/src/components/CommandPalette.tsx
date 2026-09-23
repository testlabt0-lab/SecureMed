import React, { useState, useEffect, useRef, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { Search, Lock, Sun, Moon, Stethoscope, QrCode, Pill, HeartPulse, FolderKanban, Users, Calendar, Activity, ShieldCheck, Settings, Video, FlaskConical, Bed, Receipt, Sparkles, Command, ChevronLeft, X, Loader2 } from 'lucide-react';
import toast from 'react-hot-toast';
import { roleLabel } from '../constants/roles';
import { useThemeStore } from '../store/themeStore';
import { useSecurityPreferencesStore } from '../store/securityPreferencesStore';
import { searchApi } from '../api/extendedApis';

interface CommandPaletteProps {
  open: boolean;
  onClose: () => void;
  onOpenQrScanner?: () => void;
  onOpenDrugChecker?: () => void;
}

interface PaletteItem {
  id: string;
  category: 'ACTIONS' | 'NAVIGATION' | 'PATIENTS' | 'CHANNELS' | 'USERS';
  title: string;
  subtitle?: string;
  icon: any;
  iconColor?: string;
  shortcut?: string;
  action: () => void;
}

export default function CommandPalette({
  open,
  onClose,
  onOpenQrScanner,
  onOpenDrugChecker,
}: CommandPaletteProps) {
  const navigate = useNavigate();
  const { theme, toggleTheme, setTheme } = useThemeStore();
  const { lock } = useSecurityPreferencesStore();

  const [query, setQuery] = useState('');
  const [debounced, setDebounced] = useState('');
  const [selectedIndex, setSelectedIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLDivElement>(null);

  // Debounce search input
  useEffect(() => {
    const timer = setTimeout(() => setDebounced(query.trim()), 200);
    return () => clearTimeout(timer);
  }, [query]);

  // Focus on open
  useEffect(() => {
    if (open) {
      setQuery('');
      setDebounced('');
      setSelectedIndex(0);
      setTimeout(() => inputRef.current?.focus(), 60);
    }
  }, [open]);

  // Query live search if query length >= 2
  const { data: searchResults, isFetching } = useQuery({
    queryKey: ['command-palette-search', debounced],
    queryFn: () => searchApi.query(debounced),
    enabled: open && debounced.length >= 2,
  });

  // Base Quick Actions
  const quickActions: PaletteItem[] = useMemo(() => [
    {
      id: 'act-lock',
      category: 'ACTIONS',
      title: 'قفل شاشة الخصوصية فورياً',
      subtitle: 'تعتيم الشاشة وتأمين المحطة الطبية (Privacy Shield)',
      icon: Lock,
      iconColor: 'text-amber-500 bg-amber-500/10',
      action: () => {
        onClose();
        lock('manual');
        toast('تم قفل الشاشة بنجاح');
      },
    },
    {
      id: 'act-theme',
      category: 'ACTIONS',
      title: 'تبديل المظهر السريري / الليلي / النهاري',
      subtitle: `الوضع الحالي: ${theme === 'clinical' ? 'سريري عالي التباين' : theme === 'dark' ? 'ليلي' : 'نهاري'}`,
      icon: theme === 'clinical' ? Stethoscope : theme === 'dark' ? Moon : Sun,
      iconColor: 'text-sky-500 bg-sky-500/10',
      action: () => {
        onClose();
        if (theme === 'light') setTheme('dark');
        else if (theme === 'dark') setTheme('clinical');
        else setTheme('light');
      },
    },
    {
      id: 'act-qr',
      category: 'ACTIONS',
      title: 'مسح سوار المريض الذكي (QR Barcode)',
      subtitle: 'فتح ملف المريض الإسعافي عبر مسح الرمز فوراً',
      icon: QrCode,
      iconColor: 'text-teal-500 bg-teal-500/10',
      action: () => {
        onClose();
        if (onOpenQrScanner) onOpenQrScanner();
        else navigate('/patients');
      },
    },
    {
      id: 'act-drug-checker',
      category: 'ACTIONS',
      title: 'فاحص التفاعلات الدوائية والحساسية',
      subtitle: 'التحقق السريع من تعارض الأدوية عبر الذكاء الاصطناعي',
      icon: Pill,
      iconColor: 'text-rose-500 bg-rose-500/10',
      action: () => {
        onClose();
        if (onOpenDrugChecker) onOpenDrugChecker();
        else navigate('/pharmacy');
      },
    },
  ], [onClose, lock, theme, setTheme, onOpenQrScanner, onOpenDrugChecker, navigate]);

  // Navigation Links
  const navItems: PaletteItem[] = useMemo(() => [
    { id: 'nav-dash', category: 'NAVIGATION', title: 'لوحة القيادة الرئيسية', subtitle: 'نظرة عامة على الإحصائيات والحالات', icon: Activity, action: () => { onClose(); navigate('/dashboard'); } },
    { id: 'nav-patients', category: 'NAVIGATION', title: 'سجلات المرضى (EHR)', subtitle: 'إدارة ملفات المرضى وتاريخهم الصحي', icon: HeartPulse, action: () => { onClose(); navigate('/patients'); } },
    { id: 'nav-channels', category: 'NAVIGATION', title: 'القنوات والحالات السريرية', subtitle: 'متابعة فرق العمل الطبية المشتركة', icon: FolderKanban, action: () => { onClose(); navigate('/channels'); } },
    { id: 'nav-pharmacy', category: 'NAVIGATION', title: 'صيدلية المستشفى والوصفات', subtitle: 'صرف الأدوية وتتبع المخزون والتعارضات', icon: Pill, action: () => { onClose(); navigate('/pharmacy'); } },
    { id: 'nav-lab', category: 'NAVIGATION', title: 'المختبر والتحاليل الطبية', subtitle: 'نتائج الفحوصات والطلبات المعلقة', icon: FlaskConical, action: () => { onClose(); navigate('/lab'); } },
    { id: 'nav-wards', category: 'NAVIGATION', title: 'إدارة الأجنحة والأسرة (Wards)', subtitle: 'توزيع المرضى والمراقبة السريرية', icon: Bed, action: () => { onClose(); navigate('/wards'); } },
    { id: 'nav-telemed', category: 'NAVIGATION', title: 'الاستشارات المرئية (Telemedicine)', subtitle: 'مكالمات الفيديو والعيادات الافتراضية', icon: Video, action: () => { onClose(); navigate('/telemedicine'); } },
    { id: 'nav-appts', category: 'NAVIGATION', title: 'جدول المواعيد والعيادات', subtitle: 'تنظيم مواعيد الاستقبال والمراجعات', icon: Calendar, action: () => { onClose(); navigate('/appointments'); } },
    { id: 'nav-billing', category: 'NAVIGATION', title: 'الفواتير والتحصيل المالي', subtitle: 'إدارة فواتير المرضى والمطالبات التأمينية', icon: Receipt, action: () => { onClose(); navigate('/billing'); } },
    { id: 'nav-security', category: 'NAVIGATION', title: 'لوحة الأمان والامتثال (Security)', subtitle: 'إدارة الصلاحيات، ماسح الثغرات، والأجهزة', icon: ShieldCheck, action: () => { onClose(); navigate('/security'); } },
    { id: 'nav-settings', category: 'NAVIGATION', title: 'إعدادات النظام والخصوصية', subtitle: 'تخصيص الحساب وكلمات المرور والمؤقتات', icon: Settings, action: () => { onClose(); navigate('/settings'); } },
  ], [onClose, navigate]);

  // Combine and filter items based on query
  const displayItems = useMemo<PaletteItem[]>(() => {
    const qLower = debounced.toLowerCase();

    // Search results from API
    const apiPatients: PaletteItem[] = (searchResults?.data?.patients || []).map((p: any) => ({
      id: `patient-${p.id}`,
      category: 'PATIENTS',
      title: p.full_name,
      subtitle: `هوية: ${p.national_id || '—'} • فصيلة الدم: ${p.blood_type || '—'}`,
      icon: HeartPulse,
      iconColor: 'text-teal-500 bg-teal-500/10',
      action: () => { onClose(); navigate(`/patients/${p.id}`); },
    }));

    const apiChannels: PaletteItem[] = (searchResults?.data?.channels || []).map((c: any) => ({
      id: `channel-${c.id}`,
      category: 'CHANNELS',
      title: c.name,
      subtitle: `النوع: ${c.channel_type || 'قناة سريرية'} • الحالة: ${c.status || 'نشطة'}`,
      icon: FolderKanban,
      iconColor: 'text-primary-500 bg-primary-500/10',
      action: () => { onClose(); navigate(`/channels/${c.id}`); },
    }));

    const apiUsers: PaletteItem[] = (searchResults?.data?.users || []).map((u: any) => ({
      id: `user-${u.id}`,
      category: 'USERS',
      title: u.full_name || u.email,
      subtitle: `${u.email} — ${roleLabel(u.role)}`,
      icon: Users,
      iconColor: 'text-indigo-500 bg-indigo-500/10',
      action: () => { onClose(); navigate('/users'); },
    }));

    if (!qLower) {
      return [...quickActions, ...navItems];
    }

    const filteredActions = quickActions.filter(a =>
      a.title.toLowerCase().includes(qLower) || a.subtitle?.toLowerCase().includes(qLower)
    );

    const filteredNav = navItems.filter(n =>
      n.title.toLowerCase().includes(qLower) || n.subtitle?.toLowerCase().includes(qLower)
    );

    return [...apiPatients, ...apiChannels, ...apiUsers, ...filteredActions, ...filteredNav];
  }, [debounced, searchResults, quickActions, navItems, onClose, navigate]);

  // Keyboard navigation
  useEffect(() => {
    if (!open) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        setSelectedIndex((prev) => (prev + 1) % Math.max(1, displayItems.length));
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        setSelectedIndex((prev) => (prev - 1 + displayItems.length) % Math.max(1, displayItems.length));
      } else if (e.key === 'Enter') {
        e.preventDefault();
        if (displayItems[selectedIndex]) {
          displayItems[selectedIndex].action();
        }
      } else if (e.key === 'Escape') {
        e.preventDefault();
        onClose();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [open, displayItems, selectedIndex, onClose]);

  // Scroll active item into view
  useEffect(() => {
    if (listRef.current) {
      const activeEl = listRef.current.querySelector(`[data-index="${selectedIndex}"]`);
      if (activeEl) {
        activeEl.scrollIntoView({ block: 'nearest' });
      }
    }
  }, [selectedIndex]);

  if (!open) return null;

  const categoryTitles: Record<string, string> = {
    ACTIONS: 'إجراءات سريعة وذكية',
    NAVIGATION: 'التنقل المباشر بين الأقسام',
    PATIENTS: 'المرضى المطابقون',
    CHANNELS: 'القنوات والحالات الطبية',
    USERS: 'الأطباء والمستخدمون',
  };

  return (
    <div
      className="fixed inset-0 z-[110] flex items-start justify-center bg-black/60 backdrop-blur-md p-4 pt-[10vh] animate-in fade-in duration-150"
      onClick={onClose}
      dir="rtl"
    >
      <div
        className="w-full max-w-2xl overflow-hidden rounded-3xl border border-gray-200/80 dark:border-white/10 bg-white/95 dark:bg-gray-900/95 shadow-2xl backdrop-blur-2xl transition-all"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Search Header */}
        <div className="flex items-center gap-3 px-5 py-4 border-b border-gray-200 dark:border-gray-800">
          <Search className="w-5 h-5 text-gray-400 shrink-0" />
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              setSelectedIndex(0);
            }}
            placeholder="ابحث عن مريض، قناة، دواء، أو نفّذ أمراً سريعاً..."
            className="w-full bg-transparent text-base text-gray-900 dark:text-white placeholder-gray-400 focus:outline-none"
          />
          {isFetching && <Loader2 className="w-4 h-4 animate-spin text-primary-500 shrink-0" />}
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Results List */}
        <div ref={listRef} className="max-h-[60vh] overflow-y-auto p-3 space-y-1">
          {displayItems.length === 0 ? (
            <div className="py-12 text-center">
              <Search className="w-8 h-8 text-gray-300 dark:text-gray-600 mx-auto mb-2" />
              <p className="text-sm font-medium text-gray-500 dark:text-gray-400">
                لا توجد نتائج مطابقة لـ «{query}»
              </p>
              <p className="text-xs text-gray-400 mt-1">
                جرب البحث بالاسم، رقم الهوية، أو اسم القسم
              </p>
            </div>
          ) : (
            displayItems.map((item, idx) => {
              const isSelected = idx === selectedIndex;
              const Icon = item.icon;
              const prevItem = displayItems[idx - 1];
              const showCategoryHeader = !prevItem || prevItem.category !== item.category;

              return (
                <React.Fragment key={item.id}>
                  {showCategoryHeader && (
                    <div className="px-3 pt-3 pb-1 text-[11px] font-bold text-gray-400 dark:text-gray-500 uppercase tracking-wider">
                      {categoryTitles[item.category] || item.category}
                    </div>
                  )}

                  <button
                    data-index={idx}
                    onClick={item.action}
                    onMouseEnter={() => setSelectedIndex(idx)}
                    className={`w-full flex items-center justify-between p-3 rounded-2xl transition-all text-right group cursor-pointer ${
                      isSelected
                        ? 'bg-primary-50 dark:bg-primary-950/40 border border-primary-200 dark:border-primary-800/60 shadow-sm'
                        : 'hover:bg-gray-50 dark:hover:bg-gray-800/50 border border-transparent'
                    }`}
                  >
                    <div className="flex items-center gap-3.5 min-w-0">
                      <div
                        className={`w-10 h-10 rounded-xl flex items-center justify-center shrink-0 shadow-sm ${
                          item.iconColor || 'bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-300'
                        }`}
                      >
                        <Icon className="w-5 h-5" />
                      </div>
                      <div className="min-w-0 flex-1">
                        <p className={`text-sm font-semibold truncate ${
                          isSelected ? 'text-primary-900 dark:text-primary-100' : 'text-gray-900 dark:text-white'
                        }`}>
                          {item.title}
                        </p>
                        {item.subtitle && (
                          <p className="text-xs text-gray-500 dark:text-gray-400 truncate mt-0.5">
                            {item.subtitle}
                          </p>
                        )}
                      </div>
                    </div>

                    <div className="flex items-center gap-2 pl-2">
                      <ChevronLeft className={`w-4 h-4 transition-transform ${
                        isSelected ? 'text-primary-600 dark:text-primary-400 -translate-x-1' : 'text-gray-300 dark:text-gray-600'
                      }`} />
                    </div>
                  </button>
                </React.Fragment>
              );
            })
          )}
        </div>

        {/* Footer info & shortcuts */}
        <div className="px-5 py-3 border-t border-gray-100 dark:border-gray-800/80 bg-gray-50/50 dark:bg-gray-950/40 flex items-center justify-between text-xs text-gray-500 dark:text-gray-400">
          <div className="flex items-center gap-3">
            <span className="flex items-center gap-1">
              <kbd className="px-1.5 py-0.5 bg-gray-200 dark:bg-gray-800 rounded font-mono text-[10px]">↑</kbd>
              <kbd className="px-1.5 py-0.5 bg-gray-200 dark:bg-gray-800 rounded font-mono text-[10px]">↓</kbd>
              للتنقل
            </span>
            <span className="flex items-center gap-1">
              <kbd className="px-1.5 py-0.5 bg-gray-200 dark:bg-gray-800 rounded font-mono text-[10px]">Enter</kbd>
              للاختيار
            </span>
            <span className="flex items-center gap-1">
              <kbd className="px-1.5 py-0.5 bg-gray-200 dark:bg-gray-800 rounded font-mono text-[10px]">Esc</kbd>
              للإغلاق
            </span>
          </div>

          <div className="flex items-center gap-1 font-medium text-[11px] text-primary-600 dark:text-primary-400">
            <Sparkles className="w-3.5 h-3.5" />
            <span>SecureMed Smart Command Bar</span>
          </div>
        </div>
      </div>
    </div>
  );
}
