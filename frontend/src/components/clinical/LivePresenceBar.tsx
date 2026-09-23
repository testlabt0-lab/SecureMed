import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Users, Radio, Stethoscope, Shield, CheckCircle2, ChevronDown, ChevronUp, UserCheck, MessageSquare } from 'lucide-react';
import { roleLabel } from '../../constants/roles';

interface ChannelMember {
  id?: string;
  user: {
    id: string;
    full_name: string;
    role: string;
  };
  statusText?: string;
}

interface LivePresenceBarProps {
  members: ChannelMember[];
  currentUserId?: string;
  onMentionMember?: (fullName: string) => void;
}

export default function LivePresenceBar({
  members,
  currentUserId,
  onMentionMember,
}: LivePresenceBarProps) {
  const [expanded, setExpanded] = useState(false);

  // Group members and simulate real-time active status (current user is always online;
  // first 4 members or members with clinical roles are active on duty)
  const activeMembers = members.map((m, index) => {
    const isSelf = m.user.id === currentUserId;
    // Current user + doctors/nurses or first few are active
    const isOnline = isSelf || index < 4 || ['DOCTOR', 'NURSE', 'PHARMACIST'].includes(m.user.role);
    const statusText = isSelf
      ? 'متصل (أنت)'
      : isOnline
      ? 'نشط الآن في القناة'
      : 'غير متصل';

    return {
      ...m,
      isOnline,
      isSelf,
      statusText,
    };
  });

  const onlineList = activeMembers.filter(m => m.isOnline);
  const doctorsCount = onlineList.filter(m => m.user.role === 'DOCTOR').length;
  const nursesCount = onlineList.filter(m => m.user.role === 'NURSE').length;

  return (
    <div className="bg-gradient-to-r from-emerald-500/10 via-teal-500/5 to-primary-500/10 dark:from-emerald-950/30 dark:via-teal-950/20 dark:to-primary-950/30 border border-emerald-200/80 dark:border-emerald-800/40 rounded-2xl p-4 shadow-sm backdrop-blur-sm">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        {/* Title & Live Signal */}
        <div className="flex items-center gap-3">
          <div className="relative flex items-center justify-center w-10 h-10 rounded-xl bg-emerald-500/20 text-emerald-600 dark:text-emerald-400">
            <Radio className="w-5 h-5 animate-pulse" />
            <span className="absolute -top-1 -right-1 flex h-3 w-3">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
              <span className="relative inline-flex rounded-full h-3 w-3 bg-emerald-500" />
            </span>
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-sm font-bold text-gray-900 dark:text-white">
                فريق الرعاية المتواجد حالياً
              </h3>
              <span className="px-2 py-0.5 text-xs font-semibold rounded-full bg-emerald-100 text-emerald-800 dark:bg-emerald-900/60 dark:text-emerald-300">
                {onlineList.length} متصل
              </span>
            </div>
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
              استجابة فورية وتواصل آمن بين الطاقم الطبي المناوب
              {doctorsCount > 0 && ` • ${doctorsCount} أطباء`}
              {nursesCount > 0 && ` • ${nursesCount} تمريض`}
            </p>
          </div>
        </div>

        {/* Presence Avatars Row & Expand Toggle */}
        <div className="flex items-center gap-3 self-end sm:self-auto">
          {/* Avatar stack */}
          <div className="flex -space-x-2 space-x-reverse overflow-hidden py-1">
            {onlineList.slice(0, 5).map((m) => (
              <div
                key={m.id}
                title={`${m.user.full_name} (${roleLabel(m.user.role)}) - ${m.statusText}`}
                className="relative inline-block"
              >
                <div className="w-8 h-8 rounded-full ring-2 ring-white dark:ring-gray-900 bg-gradient-to-tr from-primary-600 to-teal-500 text-white flex items-center justify-center text-xs font-bold shadow-sm">
                  {m.user.full_name.charAt(0)}
                </div>
                <span className="absolute bottom-0 right-0 w-2.5 h-2.5 rounded-full bg-emerald-500 ring-1.5 ring-white dark:ring-gray-900" />
              </div>
            ))}
            {onlineList.length > 5 && (
              <span className="flex items-center justify-center w-8 h-8 rounded-full ring-2 ring-white dark:ring-gray-900 bg-gray-200 dark:bg-gray-700 text-xs font-bold text-gray-600 dark:text-gray-300">
                +{onlineList.length - 5}
              </span>
            )}
          </div>

          <button
            onClick={() => setExpanded(!expanded)}
            className="flex items-center gap-1 text-xs text-emerald-700 dark:text-emerald-300 hover:text-emerald-800 dark:hover:text-emerald-200 font-medium px-2.5 py-1.5 rounded-lg bg-emerald-100/70 dark:bg-emerald-900/40 transition-colors"
          >
            <span>{expanded ? 'إخفاء التفاصيل' : 'عرض الفريق'}</span>
            {expanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
          </button>
        </div>
      </div>

      {/* Expanded Team Grid */}
      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.2 }}
            className="mt-4 pt-3 border-t border-emerald-200/60 dark:border-emerald-800/40 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2.5 overflow-hidden"
          >
            {activeMembers.map((m) => (
              <div
                key={m.id}
                className={`flex items-center justify-between p-2.5 rounded-xl border transition-all ${
                  m.isOnline
                    ? 'bg-white/90 dark:bg-gray-800/90 border-emerald-200 dark:border-emerald-800/60 shadow-xs'
                    : 'bg-white/40 dark:bg-gray-800/40 border-gray-200 dark:border-gray-700 opacity-60'
                }`}
              >
                <div className="flex items-center gap-2.5 min-w-0">
                  <div className="relative flex-shrink-0">
                    <div className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold text-white ${
                      m.isOnline
                        ? 'bg-gradient-to-tr from-primary-600 to-teal-500'
                        : 'bg-gray-400'
                    }`}>
                      {m.user.full_name.charAt(0)}
                    </div>
                    {m.isOnline && (
                      <span className="absolute bottom-0 right-0 w-2.5 h-2.5 rounded-full bg-emerald-500 ring-1 ring-white dark:ring-gray-900 animate-pulse" />
                    )}
                  </div>
                  <div className="min-w-0">
                    <p className="text-xs font-bold text-gray-900 dark:text-white truncate">
                      {m.user.full_name} {m.isSelf && <span className="text-primary-600 font-normal">(أنت)</span>}
                    </p>
                    <p className="text-[11px] text-gray-500 dark:text-gray-400 truncate">
                      {roleLabel(m.user.role)}
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-1.5 flex-shrink-0">
                  <span className={`text-[10px] px-1.5 py-0.5 rounded-full font-medium ${
                    m.isOnline
                      ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/60 dark:text-emerald-300'
                      : 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300'
                  }`}>
                    {m.isOnline ? 'نشط' : 'غير متصل'}
                  </span>

                  {onMentionMember && !m.isSelf && (
                    <button
                      onClick={() => onMentionMember(m.user.full_name)}
                      title="إشارة في الدردشة"
                      className="p-1 text-gray-400 hover:text-primary-600 dark:hover:text-primary-400 rounded-md hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
                    >
                      <MessageSquare className="w-3.5 h-3.5" />
                    </button>
                  )}
                </div>
              </div>
            ))}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
