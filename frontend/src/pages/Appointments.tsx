import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Calendar, Clock, User, MapPin, Video, ChevronLeft, ChevronRight,
  Plus, Check, X, AlertCircle, Phone, Stethoscope, RefreshCw,
  CheckCircle2, XCircle, Eye, Search, Filter,
} from 'lucide-react';
import { format, startOfMonth, endOfMonth, eachDayOfInterval,
         isSameDay, isToday, addMonths, subMonths, parseISO,
         isBefore, startOfDay } from 'date-fns';
import { arSA } from 'date-fns/locale';
import toast from 'react-hot-toast';
import { appointmentsAPI } from '../api/extendedApis';
import { useAuthStore } from '../store/authStore';
import CreateAppointmentModal from '../components/appointments/CreateAppointmentModal';

// ─── Type definitions ────────────────────────────────────────────────────────

type AppointmentStatus = 'SCHEDULED'|'CONFIRMED'|'IN_PROGRESS'|'COMPLETED'|'CANCELLED'|'NO_SHOW'|'RESCHEDULED';

interface Appointment {
  id: string;
  title: string;
  patient_name: string;
  doctor_name: string;
  doctor_specialization: string;
  appointment_type: string;
  type_display: string;
  status: AppointmentStatus;
  status_display: string;
  priority: string;
  priority_display: string;
  scheduled_at: string;
  end_time: string;
  duration_minutes: number;
  location: string;
  room_number: string;
  is_virtual: boolean;
  virtual_link: string;
  notes: string;
  summary: string;
  is_upcoming: boolean;
  is_past: boolean;
  color: string;
}

// ─── Constants ───────────────────────────────────────────────────────────────

const STATUS_CONFIG: Record<AppointmentStatus, { label: string; color: string; bg: string; icon: React.ElementType }> = {
  SCHEDULED:   { label: 'مجدول',    color: 'text-blue-400',    bg: 'bg-blue-500/20 border-blue-500/30',    icon: Clock },
  CONFIRMED:   { label: 'مؤكد',     color: 'text-emerald-400', bg: 'bg-emerald-500/20 border-emerald-500/30', icon: CheckCircle2 },
  IN_PROGRESS: { label: 'جارٍ',     color: 'text-amber-400',   bg: 'bg-amber-500/20 border-amber-500/30',  icon: RefreshCw },
  COMPLETED:   { label: 'مكتمل',    color: 'text-gray-400',    bg: 'bg-gray-500/20 border-gray-500/30',    icon: Check },
  CANCELLED:   { label: 'ملغى',     color: 'text-red-400',     bg: 'bg-red-500/20 border-red-500/30',      icon: XCircle },
  NO_SHOW:     { label: 'لم يحضر',  color: 'text-orange-400',  bg: 'bg-orange-500/20 border-orange-500/30', icon: AlertCircle },
  RESCHEDULED: { label: 'أُعيد جدولته', color: 'text-purple-400', bg: 'bg-purple-500/20 border-purple-500/30', icon: RefreshCw },
};

const PRIORITY_DOT: Record<string, string> = {
  LOW: 'bg-gray-400', MEDIUM: 'bg-blue-400',
  HIGH: 'bg-amber-400', URGENT: 'bg-red-500',
};

// ─── Helper Components ────────────────────────────────────────────────────────

function StatusBadge({ status }: { status: AppointmentStatus }) {
  const cfg = STATUS_CONFIG[status] || STATUS_CONFIG.SCHEDULED;
  const Icon = cfg.icon;
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium border ${cfg.bg} ${cfg.color}`}>
      <Icon className="w-3 h-3" />
      {cfg.label}
    </span>
  );
}

function PriorityDot({ priority }: { priority: string }) {
  return (
    <span className={`inline-block w-2 h-2 rounded-full ${PRIORITY_DOT[priority] || 'bg-gray-400'}`} />
  );
}

// ─── Appointment Card ─────────────────────────────────────────────────────────

function AppointmentCard({ appt, onAction }: { appt: Appointment; onAction: (id: string, action: string) => void }) {
  const [showActions, setShowActions] = useState(false);
  const scheduledDate = parseISO(appt.scheduled_at);

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -8 }}
      className="bg-white/5 border border-white/10 rounded-xl p-4 hover:bg-white/8 hover:border-white/20 transition-all group"
    >
      <div className="flex items-start gap-3">
        {/* Time block */}
        <div className="flex-shrink-0 text-center bg-white/10 rounded-lg px-3 py-2 min-w-[56px]">
          <p className="text-xs text-gray-400">{format(scheduledDate, 'EEE', { locale: arSA })}</p>
          <p className="text-lg font-bold text-white leading-tight">{format(scheduledDate, 'dd')}</p>
          <p className="text-xs text-primary-400 font-medium">{format(scheduledDate, 'HH:mm')}</p>
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between gap-2">
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 mb-1">
                <PriorityDot priority={appt.priority} />
                <span className="text-xs text-gray-400">{appt.type_display}</span>
              </div>
              <p className="text-sm font-semibold text-white truncate">{appt.title}</p>
              <p className="text-xs text-gray-400 mt-0.5 flex items-center gap-1">
                <User className="w-3 h-3" />{appt.patient_name}
              </p>
              <p className="text-xs text-gray-500 flex items-center gap-1">
                <Stethoscope className="w-3 h-3" />د. {appt.doctor_name}
                {appt.doctor_specialization && ` — ${appt.doctor_specialization}`}
              </p>
            </div>
            <StatusBadge status={appt.status} />
          </div>

          {/* Meta row */}
          <div className="flex items-center gap-3 mt-2 text-xs text-gray-500">
            <span className="flex items-center gap-1">
              <Clock className="w-3 h-3" />{appt.duration_minutes} دقيقة
            </span>
            {appt.is_virtual ? (
              <span className="flex items-center gap-1 text-blue-400">
                <Video className="w-3 h-3" />افتراضي
              </span>
            ) : appt.location ? (
              <span className="flex items-center gap-1">
                <MapPin className="w-3 h-3" />{appt.location}
                {appt.room_number && ` • غرفة ${appt.room_number}`}
              </span>
            ) : null}
          </div>
        </div>
      </div>

      {/* Actions */}
      {appt.is_upcoming && (
        <div className="flex gap-2 mt-3 pt-3 border-t border-white/5">
          {appt.status === 'SCHEDULED' && (
            <button
              onClick={() => onAction(appt.id, 'confirm')}
              className="flex-1 btn-sm bg-emerald-600/80 hover:bg-emerald-600 text-white text-xs py-1.5 px-3 rounded-lg transition-colors flex items-center justify-center gap-1"
            >
              <Check className="w-3 h-3" /> تأكيد
            </button>
          )}
          {(appt.status === 'SCHEDULED' || appt.status === 'CONFIRMED') && (
            <button
              onClick={() => onAction(appt.id, 'start')}
              className="flex-1 btn-sm bg-amber-600/80 hover:bg-amber-600 text-white text-xs py-1.5 px-3 rounded-lg transition-colors flex items-center justify-center gap-1"
            >
              <RefreshCw className="w-3 h-3" /> بدء
            </button>
          )}
          {appt.status === 'IN_PROGRESS' && (
            <button
              onClick={() => onAction(appt.id, 'complete')}
              className="flex-1 btn-sm bg-blue-600/80 hover:bg-blue-600 text-white text-xs py-1.5 px-3 rounded-lg transition-colors flex items-center justify-center gap-1"
            >
              <CheckCircle2 className="w-3 h-3" /> إنهاء
            </button>
          )}
          {appt.is_virtual && appt.virtual_link && (
            <a
              href={appt.virtual_link}
              target="_blank"
              rel="noopener noreferrer"
              className="flex-1 btn-sm bg-purple-600/80 hover:bg-purple-600 text-white text-xs py-1.5 px-3 rounded-lg transition-colors flex items-center justify-center gap-1"
            >
              <Video className="w-3 h-3" /> انضمام
            </a>
          )}
          <button
            onClick={() => onAction(appt.id, 'cancel')}
            className="btn-sm bg-red-600/20 hover:bg-red-600/40 text-red-400 text-xs py-1.5 px-3 rounded-lg transition-colors flex items-center justify-center"
          >
            <X className="w-3 h-3" />
          </button>
        </div>
      )}
    </motion.div>
  );
}

// ─── Mini Calendar ────────────────────────────────────────────────────────────

function MiniCalendar({
  currentMonth,
  setCurrentMonth,
  selectedDate,
  setSelectedDate,
  eventDates,
}: {
  currentMonth: Date;
  setCurrentMonth: (d: Date) => void;
  selectedDate: Date | null;
  setSelectedDate: (d: Date) => void;
  eventDates: string[];
}) {
  const days = eachDayOfInterval({
    start: startOfMonth(currentMonth),
    end: endOfMonth(currentMonth),
  });

  const firstDay = startOfMonth(currentMonth).getDay(); // 0 = Sun

  return (
    <div className="bg-white/5 border border-white/10 rounded-2xl p-4">
      {/* Month navigation */}
      <div className="flex items-center justify-between mb-4">
        <button
          onClick={() => setCurrentMonth(subMonths(currentMonth, 1))}
          className="p-1 rounded-lg hover:bg-white/10 transition-colors text-gray-400"
        >
          <ChevronRight className="w-4 h-4" />
        </button>
        <span className="text-sm font-semibold text-white">
          {format(currentMonth, 'MMMM yyyy', { locale: arSA })}
        </span>
        <button
          onClick={() => setCurrentMonth(addMonths(currentMonth, 1))}
          className="p-1 rounded-lg hover:bg-white/10 transition-colors text-gray-400"
        >
          <ChevronLeft className="w-4 h-4" />
        </button>
      </div>

      {/* Day headers */}
      <div className="grid grid-cols-7 mb-2">
        {['أح','اث','ث','أر','خ','ج','س'].map(d => (
          <div key={d} className="text-center text-xs text-gray-500 py-1">{d}</div>
        ))}
      </div>

      {/* Day cells */}
      <div className="grid grid-cols-7 gap-0.5">
        {/* Empty cells for first-of-month offset */}
        {Array.from({ length: firstDay }).map((_, i) => (
          <div key={`empty-${i}`} />
        ))}
        {days.map(day => {
          const dayStr = format(day, 'yyyy-MM-dd');
          const hasEvent = eventDates.includes(dayStr);
          const isSelected = selectedDate ? isSameDay(day, selectedDate) : false;
          const isPast = isBefore(day, startOfDay(new Date()));

          return (
            <button
              key={dayStr}
              onClick={() => setSelectedDate(day)}
              className={`
                relative aspect-square text-xs rounded-lg transition-all flex items-center justify-center
                ${isSelected ? 'bg-primary-600 text-white font-bold' : ''}
                ${isToday(day) && !isSelected ? 'bg-white/20 text-white font-bold ring-1 ring-primary-500' : ''}
                ${!isSelected && !isToday(day) ? (isPast ? 'text-gray-600 hover:bg-white/5' : 'text-gray-300 hover:bg-white/10') : ''}
              `}
            >
              {format(day, 'd')}
              {hasEvent && (
                <span className={`absolute bottom-0.5 left-1/2 -translate-x-1/2 w-1 h-1 rounded-full ${isSelected ? 'bg-white' : 'bg-primary-400'}`} />
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
}

// ─── Stats Bar ────────────────────────────────────────────────────────────────

function StatsBar({ stats }: { stats: any }) {
  if (!stats) return null;
  return (
    <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
      {[
        { label: 'اليوم', value: stats.today, color: 'from-blue-500 to-blue-600' },
        { label: 'هذا الشهر', value: stats.this_month, color: 'from-emerald-500 to-teal-600' },
        { label: 'القادمة (7 أيام)', value: stats.upcoming_7days, color: 'from-purple-500 to-violet-600' },
        { label: 'معدل الاكتمال', value: `${stats.completion_rate}%`, color: 'from-amber-500 to-orange-500' },
      ].map(s => (
        <div key={s.label} className={`bg-gradient-to-br ${s.color} rounded-xl p-3 text-white`}>
          <p className="text-2xl font-bold">{s.value ?? '—'}</p>
          <p className="text-xs opacity-80 mt-0.5">{s.label}</p>
        </div>
      ))}
    </div>
  );
}

// ─── Main Page ────────────────────────────────────────────────────────────────

export default function Appointments() {
  const { user } = useAuthStore();
  const qc = useQueryClient();
  const [currentMonth, setCurrentMonth] = useState(new Date());
  const [selectedDate, setSelectedDate] = useState<Date | null>(null);
  const [view, setView] = useState<'list' | 'calendar'>('list');
  const [statusFilter, setStatusFilter] = useState('');
  const [search, setSearch] = useState('');
  const [isModalOpen, setIsModalOpen] = useState(false);

  // Fetch stats
  const { data: statsRes } = useQuery({
    queryKey: ['appointments-stats'],
    queryFn: () => appointmentsAPI.stats(),
  });
  const stats = statsRes?.data;

  // Fetch all appointments for the current month (calendar events)
  const monthStart = format(startOfMonth(currentMonth), "yyyy-MM-dd'T'HH:mm:ss");
  const monthEnd   = format(endOfMonth(currentMonth),   "yyyy-MM-dd'T'23:59:59");
  const { data: calendarRes } = useQuery({
    queryKey: ['appointments-calendar', monthStart],
    queryFn: () => appointmentsAPI.calendar(monthStart, monthEnd),
  });
  const calendarEvents: Appointment[] = calendarRes?.data || [];

  // Dates that have events (for mini calendar dots)
  const eventDates = [...new Set(calendarEvents.map(e => format(parseISO(e.scheduled_at), 'yyyy-MM-dd')))];

  // Filtered list
  const { data: listRes, isLoading } = useQuery({
    queryKey: ['appointments-list', statusFilter, search],
    queryFn: () => appointmentsAPI.list({ status: statusFilter || undefined, search: search || undefined }),
  });
  const appointments: Appointment[] = listRes?.data?.results || listRes?.data || [];

  // Filter by selected date
  const displayedAppointments = selectedDate
    ? appointments.filter(a => isSameDay(parseISO(a.scheduled_at), selectedDate))
    : appointments;

  // Mutation helper
  const actionMutation = useMutation({
    mutationFn: ({ id, action }: { id: string; action: string }) => {
      switch (action) {
        case 'confirm': return appointmentsAPI.confirm(id);
        case 'start':   return appointmentsAPI.start(id);
        case 'complete': return appointmentsAPI.complete(id, {});
        case 'cancel':  return appointmentsAPI.cancel(id, { reason: 'ملغى بواسطة المستخدم' });
        default: return Promise.reject(new Error('Unknown action'));
      }
    },
    onSuccess: (_, { action }) => {
      const labels: Record<string, string> = {
        confirm: 'تم تأكيد الموعد', start: 'بدأ الموعد',
        complete: 'اكتمل الموعد', cancel: 'تم إلغاء الموعد',
      };
      toast.success(labels[action] || 'تم');
      qc.invalidateQueries({ queryKey: ['appointments-list'] });
      qc.invalidateQueries({ queryKey: ['appointments-stats'] });
      qc.invalidateQueries({ queryKey: ['appointments-calendar'] });
    },
    onError: () => toast.error('حدث خطأ، حاول مجدداً'),
  });

  const handleAction = (id: string, action: string) => actionMutation.mutate({ id, action });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            <Calendar className="w-7 h-7 text-primary-400" />
            المواعيد والجدول الزمني
          </h1>
          <p className="text-gray-400 text-sm mt-1">إدارة مواعيد المرضى والجدول الطبي</p>
        </div>
        <div className="flex items-center gap-2">
          {user && ['SUPER_ADMIN', 'HOSPITAL_ADMIN', 'CENTER_ADMIN', 'DOCTOR', 'NURSE', 'RECEPTIONIST'].includes(user.role) && (
            <button 
              onClick={() => setIsModalOpen(true)}
              className="flex items-center gap-2 px-4 py-2 bg-primary-600 hover:bg-primary-500 text-white text-sm font-bold rounded-xl transition-colors"
            >
              <Plus className="w-4 h-4" />
              إضافة موعد
            </button>
          )}
          <div className="flex bg-white/5 border border-white/10 rounded-xl overflow-hidden">
            {(['list', 'calendar'] as const).map(v => (
              <button
                key={v}
                onClick={() => setView(v)}
                className={`px-4 py-2 text-sm font-medium transition-colors ${
                  view === v ? 'bg-primary-600 text-white' : 'text-gray-400 hover:text-white'
                }`}
              >
                {v === 'list' ? 'قائمة' : 'تقويم'}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Stats */}
      <StatsBar stats={stats} />

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Sidebar: mini calendar + filters */}
        <div className="space-y-4">
          <MiniCalendar
            currentMonth={currentMonth}
            setCurrentMonth={setCurrentMonth}
            selectedDate={selectedDate}
            setSelectedDate={setSelectedDate}
            eventDates={eventDates}
          />

          {selectedDate && (
            <button
              onClick={() => setSelectedDate(null)}
              className="w-full text-xs text-gray-400 hover:text-white py-2 transition-colors"
            >
              عرض جميع المواعيد
            </button>
          )}

          {/* Status filter */}
          <div className="bg-white/5 border border-white/10 rounded-xl p-3 space-y-1">
            <p className="text-xs font-semibold text-gray-400 mb-2 uppercase tracking-wider">الحالة</p>
            {[
              { value: '', label: 'الكل' },
              { value: 'SCHEDULED', label: 'مجدول' },
              { value: 'CONFIRMED', label: 'مؤكد' },
              { value: 'IN_PROGRESS', label: 'جارٍ' },
              { value: 'COMPLETED', label: 'مكتمل' },
              { value: 'CANCELLED', label: 'ملغى' },
            ].map(f => (
              <button
                key={f.value}
                onClick={() => setStatusFilter(f.value)}
                className={`w-full text-right text-sm px-3 py-1.5 rounded-lg transition-colors ${
                  statusFilter === f.value
                    ? 'bg-primary-600/30 text-primary-300'
                    : 'text-gray-400 hover:text-white hover:bg-white/5'
                }`}
              >
                {f.label}
              </button>
            ))}
          </div>
        </div>

        {/* Main content */}
        <div className="lg:col-span-3 space-y-4">
          {/* Search */}
          <div className="relative">
            <Search className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
            <input
              type="text"
              value={search}
              onChange={e => setSearch(e.target.value)}
              placeholder="بحث في المواعيد..."
              className="w-full bg-white/5 border border-white/10 rounded-xl pr-10 pl-4 py-2.5 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-primary-500 transition-colors"
            />
          </div>

          {/* Selected date header */}
          {selectedDate && (
            <div className="flex items-center gap-2 text-sm">
              <Calendar className="w-4 h-4 text-primary-400" />
              <span className="text-white font-medium">
                {format(selectedDate, 'EEEE d MMMM yyyy', { locale: arSA })}
              </span>
              <span className="text-gray-500">({displayedAppointments.length} موعد)</span>
            </div>
          )}

          {/* Appointments list */}
          {isLoading ? (
            <div className="flex items-center justify-center py-16 text-gray-500">
              <RefreshCw className="w-5 h-5 animate-spin mr-2" />
              جاري التحميل...
            </div>
          ) : displayedAppointments.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-16 text-gray-500 space-y-2">
              <Calendar className="w-12 h-12 opacity-30" />
              <p>لا توجد مواعيد</p>
            </div>
          ) : (
            <AnimatePresence mode="popLayout">
              <div className="space-y-3">
                {displayedAppointments.map(appt => (
                  <AppointmentCard
                    key={appt.id}
                    appt={appt}
                    onAction={handleAction}
                  />
                ))}
              </div>
            </AnimatePresence>
          )}
        </div>
      </div>
      
      <CreateAppointmentModal isOpen={isModalOpen} onClose={() => setIsModalOpen(false)} />
    </div>
  );
}
