import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Video, Phone, PhoneOff, Mic, MicOff, MessageSquare, MonitorUp, Settings,
  Users, Calendar, Clock, FileText, CheckCircle, XCircle, Search, Play, StopCircle, User,
  Plus
} from 'lucide-react';
import toast from 'react-hot-toast';
import { telemedicineAPI } from '../api/extendedApis';
import { useAuthStore } from '../store/authStore';

export default function Telemedicine() {
  const { user } = useAuthStore();
  const [activeTab, setActiveTab] = useState<'upcoming' | 'history'>('upcoming');
  const [consultations, setConsultations] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [activeSession, setActiveSession] = useState<any | null>(null);

  // Video state mock
  const [isMuted, setIsMuted] = useState(false);
  const [isVideoOff, setIsVideoOff] = useState(false);
  const [messages, setMessages] = useState<any[]>([]);
  const [newMessage, setNewMessage] = useState('');
  const chatEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    fetchConsultations();
  }, [activeTab]);

  useEffect(() => {
    if (activeSession) {
      fetchMessages();
      const interval = setInterval(fetchMessages, 5000);
      return () => clearInterval(interval);
    }
  }, [activeSession]);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const fetchConsultations = async () => {
    try {
      setIsLoading(true);
      const status = activeTab === 'upcoming' ? 'SCHEDULED' : 'COMPLETED';
      const { data } = await telemedicineAPI.consultations({ status });
      setConsultations(Array.isArray(data.results) ? data.results : data);
    } catch (error) {
      toast.error('فشل في جلب الجلسات');
    } finally {
      setIsLoading(false);
    }
  };

  const fetchMessages = async () => {
    if (!activeSession) return;
    try {
      const { data } = await telemedicineAPI.messages(activeSession.id);
      setMessages(Array.isArray(data.results) ? data.results : data);
    } catch (error) {
      console.error(error);
    }
  };

  const joinSession = async (consultation: any) => {
    try {
      if (user?.role === 'DOCTOR' && consultation.status === 'SCHEDULED') {
        const { data } = await telemedicineAPI.joinConsultation(consultation.id);
        setActiveSession(data);
      } else {
        setActiveSession(consultation);
      }
      toast.success('تم الانضمام للجلسة بنجاح');
    } catch (error) {
      toast.error('فشل في الانضمام للغرفة');
    }
  };

  const endSession = async () => {
    if (!activeSession) return;
    try {
      if (user?.role === 'DOCTOR') {
        await telemedicineAPI.completeConsultation(activeSession.id, {
          notes: 'تم إنهاء الجلسة بواسطة الطبيب'
        });
        toast.success('تم إنهاء الجلسة وحفظ السجل');
      }
      setActiveSession(null);
      fetchConsultations();
    } catch (error) {
      toast.error('فشل في إنهاء الجلسة');
    }
  };

  const sendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newMessage.trim() || !activeSession) return;
    
    try {
      await telemedicineAPI.sendMessage({
        consultation: activeSession.id,
        content: newMessage
      });
      setNewMessage('');
      fetchMessages();
    } catch (error) {
      toast.error('لم يتم إرسال الرسالة');
    }
  };

  // If inside a session, render the video room
  if (activeSession) {
    return (
      <div className="flex flex-col lg:flex-row h-[calc(100vh-8rem)] gap-4">
        {/* Main Video Area */}
        <div className="flex-1 bg-gray-900 rounded-3xl overflow-hidden relative flex flex-col shadow-xl">
          {/* Mock remote video */}
          <div className="absolute inset-0 flex items-center justify-center">
            {isVideoOff ? (
              <div className="w-32 h-32 rounded-full bg-gray-800 flex items-center justify-center border-4 border-gray-700">
                <User className="w-16 h-16 text-gray-500" />
              </div>
            ) : (
              <img 
                src={`https://images.unsplash.com/photo-1579684385127-1ef15d508118?auto=format&fit=crop&w=800&q=80`} 
                alt="Remote video" 
                className="w-full h-full object-cover opacity-80" 
              />
            )}
          </div>
          
          {/* Header */}
          <div className="absolute top-0 inset-x-0 p-4 bg-gradient-to-b from-black/60 to-transparent flex justify-between items-center text-white z-10">
            <div>
              <h3 className="font-bold text-lg">{user?.role === 'DOCTOR' ? activeSession.patient_name : activeSession.doctor_name}</h3>
              <p className="text-sm text-gray-300">جلسة استشارة جارية...</p>
            </div>
            <div className="flex items-center gap-2 bg-red-500/20 text-red-100 px-3 py-1 rounded-full text-sm font-medium backdrop-blur-md border border-red-500/30">
              <span className="w-2 h-2 rounded-full bg-red-500 animate-pulse" />
              00:15:32
            </div>
          </div>

          {/* Self video thumbnail */}
          <div className="absolute bottom-24 right-6 w-48 h-64 bg-gray-800 rounded-2xl overflow-hidden border-2 border-white/20 shadow-lg z-10">
            <img 
              src={`https://images.unsplash.com/photo-1612349317150-e413f6a5b16d?auto=format&fit=crop&w=400&q=80`} 
              alt="Self video" 
              className="w-full h-full object-cover" 
            />
          </div>

          {/* Controls */}
          <div className="absolute bottom-0 inset-x-0 p-6 flex justify-center items-end bg-gradient-to-t from-black/80 to-transparent z-10">
            <div className="flex items-center gap-4 bg-white/10 backdrop-blur-xl p-3 rounded-2xl border border-white/10">
              <button 
                onClick={() => setIsMuted(!isMuted)}
                className={`p-4 rounded-xl transition-all ${isMuted ? 'bg-red-500/80 text-white' : 'bg-gray-100 text-gray-900 hover:bg-white'}`}
              >
                {isMuted ? <MicOff className="w-6 h-6" /> : <Mic className="w-6 h-6" />}
              </button>
              <button 
                onClick={() => setIsVideoOff(!isVideoOff)}
                className={`p-4 rounded-xl transition-all ${isVideoOff ? 'bg-red-500/80 text-white' : 'bg-gray-100 text-gray-900 hover:bg-white'}`}
              >
                {isVideoOff ? <Video className="w-6 h-6" /> : <Video className="w-6 h-6" />}
              </button>
              <button className="p-4 rounded-xl bg-gray-100 text-gray-900 hover:bg-white transition-all hidden md:block">
                <MonitorUp className="w-6 h-6" />
              </button>
              <button className="p-4 rounded-xl bg-gray-100 text-gray-900 hover:bg-white transition-all">
                <Settings className="w-6 h-6" />
              </button>
              <button 
                onClick={endSession}
                className="p-4 rounded-xl bg-red-600 text-white hover:bg-red-500 transition-all flex items-center gap-2 px-6"
              >
                <PhoneOff className="w-6 h-6" />
                <span className="font-bold hidden md:inline">إنهاء الجلسة</span>
              </button>
            </div>
          </div>
        </div>

        {/* Chat & Notes Area */}
        <div className="w-full lg:w-96 flex flex-col bg-white dark:bg-gray-800 rounded-3xl shadow-xl overflow-hidden border border-gray-100 dark:border-gray-700">
          <div className="p-4 border-b border-gray-100 dark:border-gray-700 bg-gray-50 dark:bg-gray-900">
            <h3 className="font-bold text-gray-900 dark:text-white flex items-center gap-2">
              <MessageSquare className="w-5 h-5 text-primary-500" />
              الدردشة المباشرة
            </h3>
          </div>
          
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {messages.map((msg, idx) => {
              const isMine = msg.sender === user?.id;
              return (
                <div key={idx} className={`flex flex-col ${isMine ? 'items-end' : 'items-start'}`}>
                  <span className="text-xs text-gray-500 mb-1">{isMine ? 'أنت' : msg.sender_name}</span>
                  <div className={`p-3 rounded-2xl max-w-[85%] ${
                    isMine 
                      ? 'bg-primary-600 text-white rounded-tl-sm' 
                      : 'bg-gray-100 dark:bg-gray-700 text-gray-900 dark:text-white rounded-tr-sm'
                  }`}>
                    <p className="text-sm">{msg.content}</p>
                  </div>
                </div>
              )
            })}
            <div ref={chatEndRef} />
          </div>

          <form onSubmit={sendMessage} className="p-4 border-t border-gray-100 dark:border-gray-700 bg-gray-50 dark:bg-gray-900">
            <div className="flex gap-2">
              <input
                type="text"
                value={newMessage}
                onChange={e => setNewMessage(e.target.value)}
                placeholder="اكتب رسالة..."
                className="flex-1 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl px-4 py-2 text-sm focus:ring-2 focus:ring-primary-500 outline-none text-gray-900 dark:text-white"
              />
              <button 
                type="submit"
                disabled={!newMessage.trim()}
                className="bg-primary-600 text-white p-2 rounded-xl hover:bg-primary-500 disabled:opacity-50 transition-colors"
              >
                <MessageSquare className="w-5 h-5" />
              </button>
            </div>
          </form>
        </div>
      </div>
    );
  }

  // Dashboard View
  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-2xl font-black text-gray-900 dark:text-white flex items-center gap-3">
            <div className="p-2.5 bg-primary-500/10 rounded-xl text-primary-600 dark:text-primary-400">
              <Video className="w-6 h-6" />
            </div>
            العيادة الافتراضية
          </h1>
          <p className="text-gray-500 dark:text-gray-400 mt-1">
            إدارة جلسات الاستشارة عن بعد والتواصل المباشر مع المرضى
          </p>
        </div>
        
        {user?.role === 'DOCTOR' && (
          <button className="bg-primary-600 text-white px-5 py-2.5 rounded-xl font-bold flex items-center gap-2 hover:bg-primary-500 transition-all shadow-lg shadow-primary-500/25">
            <Plus className="w-5 h-5" />
            جلسة جديدة
          </button>
        )}
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-white dark:bg-gray-800 p-6 rounded-3xl border border-gray-100 dark:border-gray-700 shadow-sm relative overflow-hidden group">
          <div className="absolute inset-0 bg-gradient-to-l from-primary-500/5 to-transparent" />
          <div className="flex items-center justify-between relative z-10">
            <div>
              <p className="text-sm font-medium text-gray-500 dark:text-gray-400">جلسات اليوم</p>
              <h3 className="text-3xl font-black text-gray-900 dark:text-white mt-1">12</h3>
            </div>
            <div className="w-12 h-12 rounded-2xl bg-primary-50 dark:bg-primary-500/10 flex items-center justify-center text-primary-600 dark:text-primary-400 transition-transform group-hover:scale-110">
              <Calendar className="w-6 h-6" />
            </div>
          </div>
        </div>
        
        <div className="bg-white dark:bg-gray-800 p-6 rounded-3xl border border-gray-100 dark:border-gray-700 shadow-sm relative overflow-hidden group">
          <div className="flex items-center justify-between relative z-10">
            <div>
              <p className="text-sm font-medium text-gray-500 dark:text-gray-400">قيد الانتظار</p>
              <h3 className="text-3xl font-black text-gray-900 dark:text-white mt-1">3</h3>
            </div>
            <div className="w-12 h-12 rounded-2xl bg-amber-50 dark:bg-amber-500/10 flex items-center justify-center text-amber-600 dark:text-amber-400 transition-transform group-hover:scale-110">
              <Clock className="w-6 h-6" />
            </div>
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 p-6 rounded-3xl border border-gray-100 dark:border-gray-700 shadow-sm relative overflow-hidden group">
          <div className="flex items-center justify-between relative z-10">
            <div>
              <p className="text-sm font-medium text-gray-500 dark:text-gray-400">إجمالي الساعات</p>
              <h3 className="text-3xl font-black text-gray-900 dark:text-white mt-1">45h</h3>
            </div>
            <div className="w-12 h-12 rounded-2xl bg-medical-50 dark:bg-medical-500/10 flex items-center justify-center text-medical-600 dark:text-medical-400 transition-transform group-hover:scale-110">
              <Video className="w-6 h-6" />
            </div>
          </div>
        </div>
      </div>

      {/* Tabs & List */}
      <div className="bg-white dark:bg-gray-800 border border-gray-100 dark:border-gray-700 rounded-3xl shadow-sm overflow-hidden flex flex-col min-h-[500px]">
        <div className="border-b border-gray-100 dark:border-gray-700 p-4 sm:px-6 flex flex-col sm:flex-row gap-4 justify-between items-center bg-gray-50/50 dark:bg-gray-900/50">
          <div className="flex gap-2 p-1 bg-gray-100 dark:bg-gray-900 rounded-xl w-full sm:w-auto">
            <button
              onClick={() => setActiveTab('upcoming')}
              className={`flex-1 sm:flex-none px-6 py-2 rounded-lg text-sm font-bold transition-all ${
                activeTab === 'upcoming' 
                  ? 'bg-white dark:bg-gray-800 text-gray-900 dark:text-white shadow-sm' 
                  : 'text-gray-500 hover:text-gray-700 dark:hover:text-gray-300'
              }`}
            >
              المواعيد القادمة
            </button>
            <button
              onClick={() => setActiveTab('history')}
              className={`flex-1 sm:flex-none px-6 py-2 rounded-lg text-sm font-bold transition-all ${
                activeTab === 'history' 
                  ? 'bg-white dark:bg-gray-800 text-gray-900 dark:text-white shadow-sm' 
                  : 'text-gray-500 hover:text-gray-700 dark:hover:text-gray-300'
              }`}
            >
              السجل السابق
            </button>
          </div>
          
          <div className="relative w-full sm:w-64">
            <Search className="w-4 h-4 absolute right-3 top-1/2 -translate-y-1/2 text-gray-400" />
            <input 
              type="text"
              placeholder="ابحث عن مريض..."
              className="w-full bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl pr-10 pl-4 py-2 text-sm focus:ring-2 focus:ring-primary-500 outline-none text-gray-900 dark:text-white"
            />
          </div>
        </div>

        <div className="p-4 sm:p-6 flex-1">
          {isLoading ? (
            <div className="flex justify-center items-center h-64">
              <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-primary-600"></div>
            </div>
          ) : consultations.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-64 text-center">
              <div className="w-16 h-16 bg-gray-50 dark:bg-gray-800 rounded-full flex items-center justify-center mb-4">
                <Video className="w-8 h-8 text-gray-400" />
              </div>
              <h3 className="text-lg font-bold text-gray-900 dark:text-white">لا توجد جلسات</h3>
              <p className="text-gray-500 dark:text-gray-400 mt-1 max-w-sm">
                لم يتم العثور على أي جلسات في هذه القائمة.
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              <AnimatePresence>
                {consultations.map((session, idx) => (
                  <motion.div
                    key={session.id}
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, scale: 0.95 }}
                    transition={{ delay: idx * 0.05 }}
                    className="bg-white dark:bg-gray-900 border border-gray-100 dark:border-gray-700 p-5 rounded-2xl hover:shadow-lg transition-all group"
                  >
                    <div className="flex justify-between items-start mb-4">
                      <div className="flex items-center gap-3">
                        <div className="w-12 h-12 bg-primary-50 dark:bg-primary-900/30 text-primary-600 dark:text-primary-400 rounded-full flex items-center justify-center font-bold text-lg">
                          {user?.role === 'DOCTOR' ? session.patient_name[0] : session.doctor_name[0]}
                        </div>
                        <div>
                          <h4 className="font-bold text-gray-900 dark:text-white">
                            {user?.role === 'DOCTOR' ? session.patient_name : session.doctor_name}
                          </h4>
                          <p className="text-xs text-gray-500 dark:text-gray-400">معرف الجلسة: #{session.id.substring(0,6)}</p>
                        </div>
                      </div>
                      <span className={`px-2.5 py-1 rounded-full text-xs font-bold ${
                        session.status === 'SCHEDULED' ? 'bg-amber-100 text-amber-700 dark:bg-amber-500/10 dark:text-amber-400' :
                        session.status === 'IN_PROGRESS' ? 'bg-primary-100 text-primary-700 dark:bg-primary-500/10 dark:text-primary-400' :
                        'bg-green-100 text-green-700 dark:bg-green-500/10 dark:text-green-400'
                      }`}>
                        {session.status === 'SCHEDULED' ? 'مجدول' : session.status === 'IN_PROGRESS' ? 'جارية' : 'مكتملة'}
                      </span>
                    </div>

                    <div className="space-y-2 mb-6">
                      <div className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-300">
                        <Calendar className="w-4 h-4 text-gray-400" />
                        {new Date(session.scheduled_time).toLocaleDateString('ar-SA')}
                      </div>
                      <div className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-300">
                        <Clock className="w-4 h-4 text-gray-400" />
                        {new Date(session.scheduled_time).toLocaleTimeString('ar-SA', { hour: '2-digit', minute: '2-digit' })}
                      </div>
                    </div>

                    {activeTab === 'upcoming' ? (
                      <button 
                        onClick={() => joinSession(session)}
                        className="w-full bg-primary-50 hover:bg-primary-100 dark:bg-primary-500/10 dark:hover:bg-primary-500/20 text-primary-700 dark:text-primary-400 font-bold py-2.5 rounded-xl transition-colors flex items-center justify-center gap-2"
                      >
                        <Video className="w-4 h-4" />
                        الانضمام للغرفة
                      </button>
                    ) : (
                      <button className="w-full bg-gray-50 hover:bg-gray-100 dark:bg-gray-800 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-300 font-bold py-2.5 rounded-xl transition-colors flex items-center justify-center gap-2">
                        <FileText className="w-4 h-4" />
                        عرض التقرير
                      </button>
                    )}
                  </motion.div>
                ))}
              </AnimatePresence>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
