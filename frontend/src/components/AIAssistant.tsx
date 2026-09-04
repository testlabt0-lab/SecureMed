import { useEffect, useRef, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import {
  Bot, X, Send, Loader2, Sparkles, User as UserIcon,
} from 'lucide-react';
import toast from 'react-hot-toast';
import { aiApi, analyticsApi } from '../api/extendedApis';
import { useAuthStore } from '../store/authStore';

interface Message {
  role: 'user' | 'assistant';
  content: string;
}

const SUGGESTIONS = [
  'أعطني ملخصاً سريعاً عن وضع المنصة',
  'كم عدد السجلات الحرجة؟',
  'ما ميزات الأمان المتوفرة؟',
  'كيف تعمل المصادقة البيومترية؟',
];

/** Minimal markdown renderer: **bold**, bullets, line breaks. */
function renderContent(text: string) {
  const lines = text.split('\n');
  return lines.map((line, i) => {
    const parts = line.split(/(\*\*[^*]+\*\*)/g);
    const rendered = parts.map((p, j) =>
      p.startsWith('**') && p.endsWith('**') ? (
        <strong key={j}>{p.slice(2, -2)}</strong>
      ) : (
        <span key={j}>{p}</span>
      ),
    );
    const isBullet = /^\s*[-•*]\s+/.test(line);
    return (
      <p key={i} className={isBullet ? 'pr-4' : ''}>
        {isBullet ? '• ' : ''}
        {isBullet ? rendered.map((r) => r.props.children) : rendered}
      </p>
    );
  });
}

export default function AIAssistant({ open, onClose }: { open: boolean; onClose: () => void }) {
  const user = useAuthStore(state => state.user);
  const queryClient = useQueryClient();
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' });
  }, [messages, sending]);

  useEffect(() => {
    if (open && messages.length === 0) {
      setMessages([
        {
          role: 'assistant',
          content: `مرحباً ${user?.full_name?.split(' ')[0] || ''} 👋\nأنا **المساعد الذكي** لمنصة SecureMed. اسألني عن إحصائيات المنصة، الحالات الطبية، أو ميزات الأمان.`,
        },
      ]);
    }
  }, [open]); // eslint-disable-line react-hooks/exhaustive-deps

  const buildContext = async () => {
    // Always fetch a fresh, permission-scoped analytics snapshot on demand
    try {
      const overview: any = await queryClient.fetchQuery({
        queryKey: ['analytics-overview'],
        queryFn: () => analyticsApi.overview(),
        staleTime: 15000,
      });
      const data = overview?.data;
      if (!data) return undefined;
      return {
        total_users: data.total_users,
        active_users: data.active_users,
        users_by_role: data.users_by_role,
        total_channels: data.total_channels,
        active_channels: data.active_channels,
        channels_by_type: data.channels_by_type,
        channels_by_priority: data.channels_by_priority,
        total_patients: data.total_patients,
        new_patients_today: data.new_patients_today,
        new_patients_this_week: data.new_patients_this_week,
        total_medical_records: data.total_medical_records,
        critical_records: data.critical_records,
        security_alerts_today: data.security_alerts_today,
        waf_blocks_today: data.waf_blocks_today,
        failed_logins_today: data.failed_logins_today,
        biometric_logins_today: data.biometric_logins_today,
        recent_channels: data.recent_channels,
        activity_trend: data.activity_trend,
      };
    } catch {
      return undefined;
    }
  };

  const ask = async (question: string) => {
    const trimmed = question.trim();
    if (!trimmed || sending) return;
    setSending(true);
    setInput('');
    const history = messages
      .filter((m) => m.role === 'user' || m.role === 'assistant')
      .slice(-6)
      .map((m) => ({ role: m.role, content: m.content }));
    setMessages((prev) => [...prev, { role: 'user', content: trimmed }]);
    try {
      const context = await buildContext();
      const { data } = await aiApi.ask(
        trimmed,
        context,
        history.slice(0, -1),
      );
      setMessages((prev) => [...prev, { role: 'assistant', content: data.answer }]);
    } catch (err: any) {
      toast.error(err.response?.data?.error || 'تعذر الاتصال بالمساعد الذكي');
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: 'عذراً، حدث خطأ أثناء معالجة سؤالك. حاول مرة أخرى.' },
      ]);
    } finally {
      setSending(false);
    }
  };

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-[70] flex items-end justify-start p-4 lg:p-6 pointer-events-none">
      <div
        className="pointer-events-auto w-full max-w-md h-[70vh] max-h-[620px] bg-white dark:bg-gray-800 rounded-2xl shadow-2xl border border-gray-200 dark:border-gray-700 flex flex-col overflow-hidden"
        style={{ marginRight: 'auto' }}
      >
        {/* Header */}
        <div className="flex items-center gap-3 px-4 py-3 bg-gradient-to-l from-primary-600 to-medical-600 text-white">
          <div className="w-9 h-9 bg-white/20 rounded-xl flex items-center justify-center">
            <Bot className="w-5 h-5" />
          </div>
          <div className="flex-1">
            <p className="font-bold text-sm flex items-center gap-1.5">
              المساعد الذكي
              <Sparkles className="w-3.5 h-3.5" />
            </p>
            <p className="text-xs text-white/80">مدعوم بنموذج GLM — يعرف بيانات منصتك الحية</p>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 hover:bg-white/20 rounded-lg transition-colors"
            aria-label="إغلاق"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Messages */}
        <div ref={scrollRef} className="flex-1 overflow-y-auto p-4 space-y-3">
          {messages.map((m, i) => (
            <div key={i} className={`flex gap-2 ${m.role === 'user' ? 'flex-row-reverse' : ''}`}>
              <div
                className={`w-7 h-7 rounded-full flex items-center justify-center flex-shrink-0 ${
                  m.role === 'user'
                    ? 'bg-primary-100 text-primary-700'
                    : 'bg-gradient-to-br from-primary-500 to-medical-500 text-white'
                }`}
              >
                {m.role === 'user' ? (
                  <UserIcon className="w-3.5 h-3.5" />
                ) : (
                  <Bot className="w-4 h-4" />
                )}
              </div>
              <div
                className={`max-w-[80%] px-3.5 py-2.5 rounded-2xl text-sm leading-relaxed whitespace-pre-wrap ${
                  m.role === 'user'
                    ? 'bg-primary-600 text-white rounded-tl-sm'
                    : 'bg-gray-100 dark:bg-gray-700 text-gray-800 dark:text-gray-100 rounded-tr-sm'
                }`}
              >
                {m.role === 'assistant' ? renderContent(m.content) : m.content}
              </div>
            </div>
          ))}
          {sending && (
            <div className="flex gap-2">
              <div className="w-7 h-7 rounded-full bg-gradient-to-br from-primary-500 to-medical-500 text-white flex items-center justify-center flex-shrink-0">
                <Bot className="w-4 h-4" />
              </div>
              <div className="bg-gray-100 dark:bg-gray-700 px-4 py-3 rounded-2xl rounded-tr-sm">
                <Loader2 className="w-4 h-4 animate-spin text-primary-500" />
              </div>
            </div>
          )}
        </div>

        {/* Suggestions (only at start) */}
        {messages.length <= 1 && !sending && (
          <div className="px-4 pb-2 flex flex-wrap gap-2">
            {SUGGESTIONS.map((s) => (
              <button
                key={s}
                onClick={() => ask(s)}
                className="text-xs px-3 py-1.5 bg-primary-50 dark:bg-gray-700 text-primary-700 dark:text-primary-300 rounded-full hover:bg-primary-100 dark:hover:bg-gray-600 transition-colors"
              >
                {s}
              </button>
            ))}
          </div>
        )}

        {/* Input */}
        <form
          onSubmit={(e) => {
            e.preventDefault();
            ask(input);
          }}
          className="flex items-center gap-2 p-3 border-t border-gray-200 dark:border-gray-700"
        >
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="اكتب سؤالك هنا..."
            className="flex-1 input-field !py-2.5"
            disabled={sending}
          />
          <button
            type="submit"
            disabled={sending || !input.trim()}
            className="w-10 h-10 bg-primary-600 hover:bg-primary-700 disabled:opacity-40 text-white rounded-xl flex items-center justify-center transition-colors"
            aria-label="إرسال"
          >
            <Send className="w-4 h-4" />
          </button>
        </form>
      </div>
    </div>
  );
}
