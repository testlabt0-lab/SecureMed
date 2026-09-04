import { useEffect, useRef, useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { MessagesSquare, SendHorizonal, Loader2 } from 'lucide-react';
import { chatApi } from '../api/extendedApis';
import { useAuthStore } from '../store/authStore';
import toast from 'react-hot-toast';

const roleBadge: Record<string, string> = {
  SUPER_ADMIN: 'مدير نظام',
  HOSPITAL_ADMIN: 'مدير مستشفى',
  DOCTOR: 'طبيب',
  NURSE: 'ممرض',
  LAB_TECH: 'فني مختبر',
  PHARMACIST: 'صيدلي',
  AUDITOR: 'مراجع',
};

const roleChipColor: Record<string, string> = {
  DOCTOR: 'bg-blue-100 text-blue-700',
  NURSE: 'bg-teal-100 text-teal-700',
  LAB_TECH: 'bg-purple-100 text-purple-700',
  PHARMACIST: 'bg-orange-100 text-orange-700',
  SUPER_ADMIN: 'bg-red-100 text-red-700',
  HOSPITAL_ADMIN: 'bg-amber-100 text-amber-700',
};

export default function ChannelChat({ channelId }: { channelId: string }) {
  const user = useAuthStore(state => state.user);
  const queryClient = useQueryClient();
  const [text, setText] = useState('');
  const scrollRef = useRef<HTMLDivElement>(null);
  const lastCountRef = useRef(0);

  // Polling chat (every 3s) — same-origin API with JWT auth
  const { data, isLoading } = useQuery({
    queryKey: ['channel-messages', channelId],
    queryFn: () => chatApi.list(channelId),
    refetchInterval: 3000,
  });

  const messages: any[] = data?.data || [];

  // Auto-scroll on new messages
  useEffect(() => {
    if (messages.length !== lastCountRef.current) {
      lastCountRef.current = messages.length;
      scrollRef.current?.scrollTo({
        top: scrollRef.current.scrollHeight,
        behavior: 'smooth',
      });
    }
  }, [messages.length]);

  const sendMutation = useMutation({
    mutationFn: (body: string) => chatApi.send(channelId, body),
    onSuccess: () => {
      setText('');
      queryClient.invalidateQueries({ queryKey: ['channel-messages', channelId] });
    },
    onError: (err: any) =>
      toast.error(err.response?.data?.detail || 'فشل إرسال الرسالة'),
  });

  const handleSend = (e: React.FormEvent) => {
    e.preventDefault();
    const t = text.trim();
    if (!t) return;
    sendMutation.mutate(t);
  };

  return (
    <div className="card flex flex-col">
      <div className="flex items-center justify-between mb-3">
        <h2 className="font-bold text-gray-900 dark:text-white flex items-center gap-2">
          <MessagesSquare className="w-5 h-5 text-primary-600" />
          دردشة الحالة
        </h2>
        <span className="flex items-center gap-1.5 text-xs text-green-600">
          <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
          مباشر
        </span>
      </div>

      {/* Messages */}
      <div
        ref={scrollRef}
        className="h-80 overflow-y-auto space-y-3 p-3 bg-gray-50 dark:bg-gray-700/40 rounded-xl mb-3"
      >
        {isLoading ? (
          <div className="flex justify-center py-8">
            <Loader2 className="w-6 h-6 animate-spin text-primary-400" />
          </div>
        ) : messages.length === 0 ? (
          <div className="text-center py-10">
            <MessagesSquare className="w-10 h-10 text-gray-300 dark:text-gray-600 mx-auto mb-2" />
            <p className="text-sm text-gray-400">
              لا توجد رسائل بعد — ابدأ مناقشة الحالة مع فريقك
            </p>
          </div>
        ) : (
          messages.map((m) => {
            const isMine = user?.id === m.sender;
            return (
              <div key={m.id} className={`flex gap-2 ${isMine ? 'flex-row-reverse' : ''}`}>
                <div
                  className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold flex-shrink-0 ${
                    isMine
                      ? 'bg-primary-600 text-white'
                      : 'bg-white dark:bg-gray-600 text-gray-600 dark:text-gray-200 border'
                  }`}
                >
                  {m.sender_name?.charAt(0)}
                </div>
                <div className={`max-w-[75%] ${isMine ? 'items-end text-left' : ''}`}>
                  <div className={`flex items-center gap-1.5 mb-0.5 ${isMine ? 'justify-end' : ''}`}>
                    <span className="text-xs font-medium text-gray-600 dark:text-gray-300">
                      {isMine ? 'أنت' : m.sender_name}
                    </span>
                    <span className={`text-[10px] px-1.5 py-0.5 rounded-full ${roleChipColor[m.sender_role] || 'bg-gray-100 text-gray-500'}`}>
                      {roleBadge[m.sender_role] || m.sender_role}
                    </span>
                    <span className="text-[10px] text-gray-400">
                      {new Date(m.created_at).toLocaleTimeString('ar', {
                        hour: '2-digit', minute: '2-digit',
                      })}
                    </span>
                  </div>
                  <div
                    className={`inline-block px-3.5 py-2 rounded-2xl text-sm leading-relaxed whitespace-pre-wrap break-words ${
                      isMine
                        ? 'bg-primary-600 text-white rounded-tl-sm'
                        : 'bg-white dark:bg-gray-700 text-gray-800 dark:text-gray-100 border border-gray-100 dark:border-gray-600 rounded-tr-sm'
                    }`}
                  >
                    {m.body}
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>

      {/* Input */}
      <form onSubmit={handleSend} className="flex items-center gap-2">
        <input
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="اكتب رسالة للفريق الطبي..."
          className="flex-1 input-field !py-2.5"
          maxLength={4000}
        />
        <button
          type="submit"
          disabled={sendMutation.isPending || !text.trim()}
          className="w-10 h-10 bg-primary-600 hover:bg-primary-700 disabled:opacity-40 text-white rounded-xl flex items-center justify-center transition-colors flex-shrink-0"
          aria-label="إرسال"
        >
          {sendMutation.isPending ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <SendHorizonal className="w-4 h-4" />
          )}
        </button>
      </form>
    </div>
  );
}
