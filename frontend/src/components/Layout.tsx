import { NavLink, useNavigate, useLocation, useOutlet } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { useAuthStore } from '../store/authStore';
import { useThemeStore } from '../store/themeStore';
import { useQuery } from '@tanstack/react-query';
import {
  LayoutDashboard, FolderKanban, Users, Shield, ScrollText,
  User as UserIcon, LogOut, Stethoscope, Menu, X,
  Sun, Moon, Bell, BarChart3, Bot, Building2, DatabaseBackup,
} from 'lucide-react';
import { useState, useEffect, useRef } from 'react';
import toast from 'react-hot-toast';
import { notificationsApi } from '../api/extendedApis';
import GlobalSearch from './GlobalSearch';
import AIAssistant from './AIAssistant';

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

export default function Layout() {
  const { user, logout, tokens } = useAuthStore();
  const { theme, toggleTheme } = useThemeStore();
  const navigate = useNavigate();
  const location = useLocation();
  const outlet = useOutlet();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [searchOpen, setSearchOpen] = useState(false);
  const [aiOpen, setAiOpen] = useState(false);
  const lastUnread = useRef<number | null>(null);

  // Ctrl+K opens global search
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        setSearchOpen(true);
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, []);

  // Fetch unread notifications count
  const { data: unreadData } = useQuery({
    queryKey: ['unread-count'],
    queryFn: () => notificationsApi.unreadCount(),
    refetchInterval: 20000, // Refresh every 20 seconds
    enabled: !!user,
  });

  const unreadCount = unreadData?.data?.unread_count || 0;

  // Browser push notifications when new ones arrive
  useEffect(() => {
    if (lastUnread.current !== null && unreadCount > lastUnread.current) {
      const showBrowserNotification = async () => {
        if (!('Notification' in window)) return;
        let permission = Notification.permission;
        if (permission === 'default') {
          permission = await Notification.requestPermission();
        }
        if (permission === 'granted') {
          try {
            const { data: listData } = await notificationsApi.list({ page_size: 1 });
            const latest = listData?.results?.[0];
            const n = new Notification('SecureMed — إشعار جديد', {
              body: latest?.title || `لديك ${unreadCount} إشعارات غير مقروءة`,
              icon: '/favicon.svg',
              tag: 'securemed-notification',
            });
            n.onclick = () => {
              window.focus();
              navigate('/notifications');
              n.close();
            };
          } catch {
            toast(`لديك ${unreadCount} إشعارات غير مقروءة`);
          }
        } else {
          toast(`🔔 لديك ${unreadCount} إشعارات غير مقروءة`);
        }
      };
      showBrowserNotification();
    }
    lastUnread.current = unreadCount;
  }, [unreadCount, navigate]);

  // Apply dark mode class to document
  useEffect(() => {
    if (theme === 'dark') {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  }, [theme]);

  const handleLogout = async () => {
    try {
      if (tokens?.refresh) {
        const { authAPI } = await import('../api/client');
        await authAPI.logout(tokens.refresh);
      }
    } catch (e) {
      // Ignore logout errors
    } finally {
      logout();
      toast.success('تم تسجيل الخروج بنجاح');
      navigate('/login');
    }
  };

  const navItems = [
    { path: '/dashboard', label: 'لوحة التحكم', icon: LayoutDashboard },
    { path: '/channels', label: 'القنوات والحالات', icon: FolderKanban },
    { path: '/patients', label: 'المرضى', icon: Users },
    { path: '/analytics', label: 'التحليلات', icon: BarChart3, roles: ['SUPER_ADMIN', 'HOSPITAL_ADMIN', 'AUDITOR'] },
    { path: '/security', label: 'لوحة الأمان', icon: Shield, roles: ['SUPER_ADMIN', 'HOSPITAL_ADMIN', 'AUDITOR'] },
    { path: '/audit', label: 'سجلات التدقيق', icon: ScrollText, roles: ['SUPER_ADMIN', 'HOSPITAL_ADMIN', 'AUDITOR'] },
    { path: '/users', label: 'المستخدمون', icon: Users, roles: ['SUPER_ADMIN', 'HOSPITAL_ADMIN'] },
    { path: '/basins', label: 'الأحواز الصحية', icon: Building2 },
    { path: '/backups', label: 'النسخ الاحتياطي', icon: DatabaseBackup, roles: ['SUPER_ADMIN'] },
    { path: '/notifications', label: 'الإشعارات', icon: Bell, badge: unreadCount },
    { path: '/profile', label: 'الملف الشخصي', icon: UserIcon },
  ].filter(item => !item.roles || (user && item.roles.includes(user.role)));

  const sidebarContent = (
    <>
      {/* Logo */}
      <motion.div
        className="flex items-center justify-between h-16 px-5 border-b border-gray-100 dark:border-gray-700/60"
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
      >
        <div className="flex items-center gap-2.5">
          <motion.div
            className="relative w-10 h-10 bg-gradient-to-br from-primary-500 via-primary-600 to-medical-600 rounded-2xl flex items-center justify-center shadow-lg shadow-primary-600/30"
            whileHover={{ rotate: -8, scale: 1.08 }}
            transition={{ type: 'spring', stiffness: 300 }}
          >
            <Stethoscope className="w-6 h-6 text-white" />
            <span className="absolute -top-0.5 -left-0.5 w-2.5 h-2.5 rounded-full bg-medical-400 border-2 border-white dark:border-gray-800" />
          </motion.div>
          <div>
            <h1 className="font-black font-heading text-gray-900 dark:text-white leading-tight">
              Secure<span className="text-gradient">Med</span>
            </h1>
            <p className="text-[11px] text-gray-400 dark:text-gray-500">منصة صحية آمنة</p>
          </div>
        </div>
        <button
          className="lg:hidden p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
          onClick={() => setSidebarOpen(false)}
        >
          <X className="w-5 h-5 text-gray-600 dark:text-gray-400" />
        </button>
      </motion.div>

      {/* Nav — scrollable, with animated active pill */}
      <nav className="flex-1 overflow-y-auto p-3.5 space-y-1">
        {navItems.map((item, i) => (
          <motion.div
            key={item.path}
            initial={{ opacity: 0, x: 24 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.04 * i, duration: 0.35 }}
          >
            <NavLink
              to={item.path}
              onClick={() => setSidebarOpen(false)}
              className={({ isActive }) =>
                `group relative flex items-center gap-3 px-4 py-2.5 rounded-xl text-sm font-medium transition-all duration-200 ${
                  isActive
                    ? 'text-primary-700 dark:text-primary-300'
                    : 'text-gray-600 dark:text-gray-400 hover:text-primary-600 dark:hover:text-primary-300'
                }`
              }
            >
              {({ isActive }) => (
                <>
                  {isActive && (
                    <motion.span
                      layoutId="nav-active-pill"
                      className="absolute inset-0 rounded-xl bg-gradient-to-l from-primary-500/15 to-medical-500/10 border border-primary-500/25 dark:border-primary-400/20"
                      transition={{ type: 'spring', stiffness: 380, damping: 32 }}
                    />
                  )}
                  {isActive && (
                    <motion.span
                      layoutId="nav-active-bar"
                      className="absolute -right-1.5 top-1/2 -mt-3 h-6 w-1.5 rounded-full bg-gradient-to-b from-primary-500 to-medical-500"
                      transition={{ type: 'spring', stiffness: 380, damping: 32 }}
                    />
                  )}
                  <item.icon
                    className={`w-5 h-5 relative z-10 transition-transform duration-200 group-hover:scale-110 ${
                      isActive ? 'text-primary-600 dark:text-primary-300' : ''
                    }`}
                  />
                  <span className="flex-1 relative z-10">{item.label}</span>
                  {item.badge && item.badge > 0 ? (
                    <motion.span
                      initial={{ scale: 0 }}
                      animate={{ scale: 1 }}
                      className="relative z-10 bg-gradient-to-l from-red-500 to-rose-500 text-white text-xs font-bold px-2 py-0.5 rounded-full shadow-md shadow-red-500/30"
                    >
                      {item.badge}
                    </motion.span>
                  ) : null}
                </>
              )}
            </NavLink>
          </motion.div>
        ))}
      </nav>

      {/* Bottom section */}
      <div className="border-t border-gray-100 dark:border-gray-700/60 p-4 space-y-2">
        {/* Dark mode toggle */}
        <motion.button
          onClick={toggleTheme}
          className="w-full flex items-center justify-center gap-2 px-4 py-2 text-sm text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-xl transition-colors"
          whileTap={{ scale: 0.97 }}
        >
          <AnimatePresence mode="wait" initial={false}>
            {theme === 'light' ? (
              <motion.span
                key="moon"
                className="flex items-center gap-2"
                initial={{ rotate: -90, opacity: 0 }}
                animate={{ rotate: 0, opacity: 1 }}
                exit={{ rotate: 90, opacity: 0 }}
                transition={{ duration: 0.25 }}
              >
                <Moon className="w-4 h-4" />
                الوضع الليلي
              </motion.span>
            ) : (
              <motion.span
                key="sun"
                className="flex items-center gap-2"
                initial={{ rotate: 90, opacity: 0 }}
                animate={{ rotate: 0, opacity: 1 }}
                exit={{ rotate: -90, opacity: 0 }}
                transition={{ duration: 0.25 }}
              >
                <Sun className="w-4 h-4" />
                الوضع النهاري
              </motion.span>
            )}
          </AnimatePresence>
        </motion.button>

        {/* User info */}
        <div className="flex items-center gap-3 p-2.5 rounded-2xl bg-gray-50 dark:bg-gray-700/40">
          <div className="relative">
            <div className="w-10 h-10 bg-gradient-to-br from-primary-500/20 to-medical-500/20 border border-primary-500/30 rounded-full flex items-center justify-center">
              <span className="text-primary-700 dark:text-primary-300 font-bold">
                {user?.full_name?.charAt(0) || 'م'}
              </span>
            </div>
            <span className="absolute bottom-0 left-0 w-2.5 h-2.5 rounded-full bg-green-400 border-2 border-white dark:border-gray-800" />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-semibold text-gray-900 dark:text-white truncate">
              {user?.full_name}
            </p>
            <p className="text-xs text-gray-500 dark:text-gray-400">
              {user ? roleLabels[user.role] : ''}
            </p>
          </div>
          <motion.button
            onClick={handleLogout}
            className="p-2 text-red-500 hover:bg-red-50 dark:hover:bg-red-900/30 rounded-xl transition-colors"
            title="تسجيل الخروج"
            whileHover={{ scale: 1.1, rotate: -8 }}
            whileTap={{ scale: 0.9 }}
          >
            <LogOut className="w-5 h-5" />
          </motion.button>
        </div>
      </div>
    </>
  );

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-950 flex">
      {/* Desktop sidebar */}
      <aside className="hidden lg:flex sticky top-0 right-0 h-screen w-72 flex-col bg-white/90 dark:bg-gray-900/80 backdrop-blur-xl border-l border-gray-100 dark:border-gray-700/60 z-40">
        {sidebarContent}
      </aside>

      {/* Mobile sidebar */}
      <AnimatePresence>
        {sidebarOpen && (
          <>
            <motion.div
              className="fixed inset-0 bg-navy-900/60 backdrop-blur-sm z-30 lg:hidden"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setSidebarOpen(false)}
            />
            <motion.aside
              className="fixed lg:hidden top-0 right-0 z-40 h-screen w-72 flex flex-col bg-white dark:bg-gray-900 border-l border-gray-200 dark:border-gray-700"
              initial={{ x: '100%' }}
              animate={{ x: 0 }}
              exit={{ x: '100%' }}
              transition={{ type: 'spring', stiffness: 320, damping: 34 }}
            >
              {sidebarContent}
            </motion.aside>
          </>
        )}
      </AnimatePresence>

      {/* Main content */}
      <div className="flex-1 flex flex-col min-h-screen min-w-0">
        {/* Mobile header */}
        <header className="lg:hidden sticky top-0 z-20 bg-white/90 dark:bg-gray-900/90 backdrop-blur-xl border-b border-gray-100 dark:border-gray-700/60 px-4 h-16 flex items-center justify-between">
          <motion.button
            onClick={() => setSidebarOpen(true)}
            className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-xl transition-colors"
            whileTap={{ scale: 0.9 }}
          >
            <Menu className="w-6 h-6 text-gray-600 dark:text-gray-300" />
          </motion.button>
          <div className="flex items-center gap-2">
            <div className="w-9 h-9 bg-gradient-to-br from-primary-500 to-medical-600 rounded-xl flex items-center justify-center shadow-md shadow-primary-600/25">
              <Stethoscope className="w-5 h-5 text-white" />
            </div>
            <span className="font-black font-heading text-gray-900 dark:text-white">
              Secure<span className="text-gradient">Med</span>
            </span>
          </div>
          <NavLink to="/notifications" className="relative p-2">
            <motion.div whileTap={{ scale: 0.85 }}>
              <Bell className={`w-5 h-5 text-gray-600 dark:text-gray-300 ${unreadCount > 0 ? 'animate-heartbeat' : ''}`} />
              {unreadCount > 0 && (
                <span className="absolute top-0 right-0 bg-gradient-to-l from-red-500 to-rose-500 text-white text-xs font-bold px-1.5 py-0.5 rounded-full">
                  {unreadCount}
                </span>
              )}
            </motion.div>
          </NavLink>
        </header>

        {/* Route transitions */}
        <main className="flex-1 p-4 lg:p-8 overflow-x-auto">
          <AnimatePresence mode="wait" initial={false}>
            <motion.div key={location.pathname}>{outlet}</motion.div>
          </AnimatePresence>
        </main>
      </div>

      {/* Global search modal (Ctrl+K) */}
      <GlobalSearch open={searchOpen} onClose={() => setSearchOpen(false)} />

      {/* AI Smart Assistant panel */}
      <AIAssistant open={aiOpen} onClose={() => setAiOpen(false)} />

      {/* Floating AI button (bottom-left corner) */}
      <motion.button
        onClick={() => setAiOpen(true)}
        className="fixed bottom-6 left-6 z-50 w-14 h-14 rounded-full bg-gradient-to-br from-primary-500 via-primary-600 to-medical-600 text-white shadow-xl shadow-primary-600/40 flex items-center justify-center"
        title="المساعد الذكي"
        aria-label="فتح المساعد الذكي"
        whileHover={{ scale: 1.1, rotate: -8 }}
        whileTap={{ scale: 0.92 }}
        initial={{ opacity: 0, scale: 0 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ delay: 0.6, type: 'spring', stiffness: 260, damping: 18 }}
      >
        <span className="absolute inset-0 rounded-full bg-primary-500/40 animate-pulse-ring" />
        <Bot className="w-6 h-6 relative" />
      </motion.button>
    </div>
  );
}
