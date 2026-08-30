import { Outlet, NavLink, useNavigate } from 'react-router-dom';
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

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex">
      {/* Sidebar */}
      <aside
        className={`fixed lg:sticky top-0 right-0 z-40 h-screen w-72 bg-white dark:bg-gray-800 border-l border-gray-200 dark:border-gray-700 transition-transform duration-300 ${
          sidebarOpen ? 'translate-x-0' : 'translate-x-full lg:translate-x-0'
        }`}
      >
        <div className="flex items-center justify-between h-16 px-6 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center gap-2">
            <div className="w-10 h-10 bg-gradient-to-br from-primary-600 to-medical-600 rounded-xl flex items-center justify-center">
              <Stethoscope className="w-6 h-6 text-white" />
            </div>
            <div>
              <h1 className="font-bold text-gray-900 dark:text-white">SecureMed</h1>
              <p className="text-xs text-gray-500 dark:text-gray-400">منصة صحية آمنة</p>
            </div>
          </div>
          <button
            className="lg:hidden p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg"
            onClick={() => setSidebarOpen(false)}
          >
            <X className="w-5 h-5 text-gray-600 dark:text-gray-400" />
          </button>
        </div>

        <nav className="p-4 space-y-1">
          {navItems.map((item) => (
            <NavLink
              key={item.path}
              to={item.path}
              onClick={() => setSidebarOpen(false)}
              className={({ isActive }) =>
                `flex items-center gap-3 px-4 py-3 rounded-lg text-sm font-medium transition-colors ${
                  isActive
                    ? 'bg-primary-50 dark:bg-primary-900/30 text-primary-700 dark:text-primary-400'
                    : 'text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700'
                }`
              }
            >
              <item.icon className="w-5 h-5" />
              <span className="flex-1">{item.label}</span>
              {item.badge && item.badge > 0 ? (
                <span className="bg-red-500 text-white text-xs font-bold px-2 py-0.5 rounded-full">
                  {item.badge}
                </span>
              ) : null}
            </NavLink>
          ))}
        </nav>

        {/* Dark mode toggle */}
        <div className="absolute bottom-20 left-0 right-0 px-4">
          <button
            onClick={toggleTheme}
            className="w-full flex items-center justify-center gap-2 px-4 py-2 text-sm text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
          >
            {theme === 'light' ? (
              <>
                <Moon className="w-4 h-4" />
                الوضع الليلي
              </>
            ) : (
              <>
                <Sun className="w-4 h-4" />
                الوضع النهاري
              </>
            )}
          </button>
        </div>

        {/* User info */}
        <div className="absolute bottom-0 left-0 right-0 p-4 border-t border-gray-200 dark:border-gray-700">
          <div className="flex items-center gap-3 mb-3">
            <div className="w-10 h-10 bg-primary-100 dark:bg-primary-900/30 rounded-full flex items-center justify-center">
              <span className="text-primary-700 dark:text-primary-400 font-semibold">
                {user?.full_name?.charAt(0) || 'م'}
              </span>
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-gray-900 dark:text-white truncate">
                {user?.full_name}
              </p>
              <p className="text-xs text-gray-500 dark:text-gray-400">
                {user ? roleLabels[user.role] : ''}
              </p>
            </div>
          </div>
          <button
            onClick={handleLogout}
            className="w-full flex items-center justify-center gap-2 px-4 py-2 text-sm text-red-600 hover:bg-red-50 dark:hover:bg-red-900/30 rounded-lg transition-colors"
          >
            <LogOut className="w-4 h-4" />
            تسجيل الخروج
          </button>
        </div>
      </aside>

      {/* Overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-30 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Main content */}
      <div className="flex-1 flex flex-col min-h-screen">
        {/* Mobile header */}
        <header className="lg:hidden sticky top-0 z-20 bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 px-4 h-16 flex items-center justify-between">
          <button
            onClick={() => setSidebarOpen(true)}
            className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg"
          >
            <Menu className="w-6 h-6 text-gray-600 dark:text-gray-300" />
          </button>
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 bg-gradient-to-br from-primary-600 to-medical-600 rounded-lg flex items-center justify-center">
              <Stethoscope className="w-5 h-5 text-white" />
            </div>
            <span className="font-bold text-gray-900 dark:text-white">SecureMed</span>
          </div>
          {/* Notifications bell for mobile */}
          <NavLink to="/notifications" className="relative p-2">
            <Bell className="w-5 h-5 text-gray-600 dark:text-gray-300" />
            {unreadCount > 0 && (
              <span className="absolute top-1 right-1 bg-red-500 text-white text-xs font-bold px-1.5 py-0.5 rounded-full">
                {unreadCount}
              </span>
            )}
          </NavLink>
        </header>

        <main className="flex-1 p-4 lg:p-8 overflow-x-auto">
          <Outlet />
        </main>
      </div>

      {/* Global search modal (Ctrl+K) */}
      <GlobalSearch open={searchOpen} onClose={() => setSearchOpen(false)} />

      {/* AI Smart Assistant panel */}
      <AIAssistant open={aiOpen} onClose={() => setAiOpen(false)} />

      {/* Floating AI button (bottom-left corner) */}
      <button
        onClick={() => setAiOpen(true)}
        className="fixed bottom-6 left-6 z-50 w-14 h-14 rounded-full bg-gradient-to-br from-primary-600 to-medical-600 text-white shadow-lg shadow-primary-600/30 hover:scale-105 transition-transform flex items-center justify-center"
        title="المساعد الذكي"
        aria-label="فتح المساعد الذكي"
      >
        <Bot className="w-6 h-6" />
      </button>
    </div>
  );
}
