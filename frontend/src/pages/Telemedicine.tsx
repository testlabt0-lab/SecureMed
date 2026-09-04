import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Video, PhoneOff, Mic, MicOff, MessageSquare, MonitorUp, Settings,
  Calendar, Clock, FileText, CheckCircle, Search, User,
  Plus, Stethoscope, Save, Maximize2, Minimize2, AlertCircle, ShieldAlert
} from 'lucide-react';
import toast from 'react-hot-toast';
import { telemedicineAPI } from '../api/extendedApis';
import { useAuthStore } from '../store/authStore';
import CreateSessionModal from '../components/telemedicine/CreateSessionModal';

export default function Telemedicine() {
  const { user } = useAuthStore();
  const [activeTab, setActiveTab] = useState<'upcoming' | 'history'>('upcoming');
  const [consultations, setConsultations] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [activeSession, setActiveSession] = useState<any | null>(null);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');

  // WebRTC & Media Stream state
  const [isMuted, setIsMuted] = useState(false);
  const [isVideoOff, setIsVideoOff] = useState(false);
  const [isScreenSharing, setIsScreenSharing] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [sidePanelTab, setSidePanelTab] = useState<'chat' | 'notes'>('chat');

  // Video element refs
  const localVideoRef = useRef<HTMLVideoElement>(null);
  const screenShareVideoRef = useRef<HTMLVideoElement>(null);
  const localStreamRef = useRef<MediaStream | null>(null);
  const screenStreamRef = useRef<MediaStream | null>(null);
  const videoContainerRef = useRef<HTMLDivElement>(null);

  // In-call duration timer
  const [callDuration, setCallDuration] = useState(0);

  // In-call clinical notes & diagnosis
  const [clinicalNotes, setClinicalNotes] = useState('');
  const [clinicalDiagnosis, setClinicalDiagnosis] = useState('');
  const [isSavingNotes, setIsSavingNotes] = useState(false);

  // Chat state
  const [messages, setMessages] = useState<any[]>([]);
  const [newMessage, setNewMessage] = useState('');
  const chatEndRef = useRef<HTMLDivElement>(null);

  const canManageSessions = ['DOCTOR', 'SUPER_ADMIN', 'HOSPITAL_ADMIN'].includes(user?.role || '');

  useEffect(() => {
    fetchConsultations();
  }, [activeTab]);

  // Handle active session media setup and teardown
  useEffect(() => {
    let timerInterval: any = null;

    if (activeSession) {
      setClinicalNotes(activeSession.notes || '');
      setClinicalDiagnosis(activeSession.diagnosis || '');
      setCallDuration(0);

      // Start duration counter
      timerInterval = setInterval(() => {
        setCallDuration(prev => prev + 1);
      }, 1000);

      // Start local webcam & mic
      startLocalMedia();

      // Poll messages
      fetchMessages();
      const msgInterval = setInterval(fetchMessages, 4000);

      return () => {
        clearInterval(timerInterval);
        clearInterval(msgInterval);
        stopAllMedia();
      };
    } else {
      stopAllMedia();
    }
  }, [activeSession]);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const startLocalMedia = async () => {
    try {
      if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
        const stream = await navigator.mediaDevices.getUserMedia({
          video: true,
          audio: true,
        });
        localStreamRef.current = stream;
        if (localVideoRef.current) {
          localVideoRef.current.srcObject = stream;
        }
      }
    } catch (err) {
      console.warn('Webcam/mic access declined or not available:', err);
      // Still allow session with mock feed fallback
    }
  };

  const stopAllMedia = () => {
    if (localStreamRef.current) {
      localStreamRef.current.getTracks().forEach(track => track.stop());
      localStreamRef.current = null;
    }
    if (screenStreamRef.current) {
      screenStreamRef.current.getTracks().forEach(track => track.stop());
      screenStreamRef.current = null;
    }
    setIsScreenSharing(false);
  };

  const toggleMute = () => {
    if (localStreamRef.current) {
      const audioTracks = localStreamRef.current.getAudioTracks();
      audioTracks.forEach(t => {
        t.enabled = !t.enabled;
      });
    }
    setIsMuted(!isMuted);
  };

  const toggleVideo = () => {
    if (localStreamRef.current) {
      const videoTracks = localStreamRef.current.getVideoTracks();
      videoTracks.forEach(t => {
        t.enabled = !t.enabled;
      });
    }
    setIsVideoOff(!isVideoOff);
  };

  const toggleScreenShare = async () => {
    if (isScreenSharing) {
      if (screenStreamRef.current) {
        screenStreamRef.current.getTracks().forEach(track => track.stop());
        screenStreamRef.current = null;
      }
      setIsScreenSharing(false);
    } else {
      try {
        if (navigator.mediaDevices && navigator.mediaDevices.getDisplayMedia) {
          const screenStream = await navigator.mediaDevices.getDisplayMedia({ video: true });
          screenStreamRef.current = screenStream;
          if (screenShareVideoRef.current) {
            screenShareVideoRef.current.srcObject = screenStream;
          }
          setIsScreenSharing(true);

          screenStream.getVideoTracks()[0].onended = () => {
            setIsScreenSharing(false);
            screenStreamRef.current = null;
          };
        }
      } catch (err) {
        toast.error('تعذر بدء مشاركة الشاشة');
      }
    }
  };

  const toggleFullscreen = () => {
    if (!document.fullscreenElement) {
      videoContainerRef.current?.requestFullscreen?.();
      setIsFullscreen(true);
    } else {
      document.exitFullscreen?.();
      setIsFullscreen(false);
    }
  };

  const fetchConsultations = async () => {
    try {
      setIsLoading(true);
      const status = activeTab === 'upcoming' ? 'SCHEDULED' : 'COMPLETED';
      const { data } = await telemedicineAPI.consultations({ status });
      setConsultations(Array.isArray(data.results) ? data.results : Array.isArray(data) ? data : []);
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
      setMessages(Array.isArray(data.results) ? data.results : Array.isArray(data) ? data : []);
    } catch (error) {
      console.error(error);
    }
  };

  const joinSession = async (consultation: any) => {
    try {
      if (canManageSessions && consultation.status === 'SCHEDULED') {
        const { data } = await telemedicineAPI.joinConsultation(consultation.id);
        setActiveSession(data);
      } else {
        setActiveSession(consultation);
      }
      toast.success('تم الانضمام للغرفة الافتراضية بنجاح');
    } catch (error) {
      toast.error('فشل في الانضمام للغرفة');
    }
  };

  const saveClinicalNotes = async () => {
    if (!activeSession) return;
    try {
      setIsSavingNotes(true);
      await telemedicineAPI.completeConsultation(activeSession.id, {
        notes: clinicalNotes,
        diagnosis: clinicalDiagnosis,
      });
      toast.success('تم حفظ الملاحظات والتشخيص السريري');
    } catch (error) {
      toast.error('فشل حفظ الملاحظات');
    } finally {
      setIsSavingNotes(false);
    }
  };

  const endSession = async () => {
    if (!activeSession) return;
    try {
      if (canManageSessions) {
        await telemedicineAPI.completeConsultation(activeSession.id, {
          notes: clinicalNotes || 'تم إنهاء الجلسة بنجاح',
          diagnosis: clinicalDiagnosis,
        });
        toast.success('تم إنهاء الجلسة وحفظ التقرير الطبي');
      }
      stopAllMedia();
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
        content: newMessage.trim(),
      });
      setNewMessage('');
      fetchMessages();
    } catch (error) {
      toast.error('لم يتم إرسال الرسالة');
    }
  };

  // Format call seconds to HH:MM:SS
  const formatDuration = (secs: number) => {
    const hrs = Math.floor(secs / 3600);
    const mins = Math.floor((secs % 3600) / 60);
    const s = secs % 60;
    return `${hrs ? `${String(hrs).padStart(2, '0')}:` : ''}${String(mins).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
  };

  const filteredConsultations = consultations.filter((c: any) => {
    const q = searchQuery.toLowerCase().trim();
    if (!q) return true;
    return (
      (c.patient_name && c.patient_name.toLowerCase().includes(q)) ||
      (c.doctor_name && c.doctor_name.toLowerCase().includes(q)) ||
      (c.diagnosis && c.diagnosis.toLowerCase().includes(q)) ||
      (c.room_id && c.room_id.toLowerCase().includes(q))
    );
  });

  // Render Live Video Room if session is active
  if (activeSession) {
    const otherPartyName = user?.role === 'DOCTOR' ? activeSession.patient_name : activeSession.doctor_name;

    return (
      <div className="flex flex-col lg:flex-row h-[calc(100vh-7.5rem)] gap-4 animate-in fade-in duration-300">
        {/* Main Video Stage */}
        <div
          ref={videoContainerRef}
          className="flex-1 bg-gray-950 rounded-3xl overflow-hidden relative flex flex-col shadow-2xl border border-gray-800"
        >
          {/* Main Display: Screen Share or Remote Feed */}
          <div className="absolute inset-0 flex items-center justify-center bg-gray-900">
            {isScreenSharing ? (
              <video
                ref={screenShareVideoRef}
                autoPlay
                playsInline
                className="w-full h-full object-contain bg-black"
              />
            ) : (
              <div className="w-full h-full relative flex items-center justify-center">
                {/* Fallback ambient medical backdrop */}
                <img
                  src="https://images.unsplash.com/photo-1579684385127-1ef15d508118?auto=format&fit=crop&w=1200&q=80"
                  alt="Remote party"
                  className="w-full h-full object-cover opacity-60 filter blur-xs"
                />
                <div className="absolute flex flex-col items-center gap-3 bg-black/40 backdrop-blur-md p-6 rounded-3xl border border-white/10 text-white text-center">
                  <div className="w-24 h-24 rounded-full bg-gradient-to-br from-primary-500 to-medical-600 flex items-center justify-center text-3xl font-bold shadow-xl">
                    {otherPartyName?.charAt(0) || 'م'}
                  </div>
                  <div>
                    <h3 className="text-xl font-bold">{otherPartyName}</h3>
                    <p className="text-xs text-gray-300 mt-0.5">غرفة الاستشارة الافتراضية مشفرة من طرف لطرف</p>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Top Bar Overlay */}
          <div className="absolute top-0 inset-x-0 p-4 sm:p-5 bg-gradient-to-b from-black/80 via-black/40 to-transparent flex justify-between items-center text-white z-20">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-primary-600/80 rounded-xl backdrop-blur-md">
                <Video className="w-5 h-5 text-white" />
              </div>
              <div>
                <h3 className="font-bold text-base sm:text-lg flex items-center gap-2">
                  {otherPartyName}
                  <span className="text-[11px] font-normal px-2 py-0.5 bg-white/10 rounded-full border border-white/10">
                    ID: #{activeSession.room_id?.slice(0, 8)}
                  </span>
                </h3>
                <p className="text-xs text-emerald-400 flex items-center gap-1.5 mt-0.5">
                  <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                  اتصال حي آمن ومباشر
                </p>
              </div>
            </div>

            <div className="flex items-center gap-3">
              <div className="flex items-center gap-2 bg-black/50 text-white px-3.5 py-1.5 rounded-full text-xs font-mono font-bold backdrop-blur-md border border-white/15">
                <span className="w-2.5 h-2.5 rounded-full bg-red-500 animate-pulse" />
                {formatDuration(callDuration)}
              </div>
              <button
                onClick={toggleFullscreen}
                className="p-2 rounded-xl bg-white/10 hover:bg-white/20 transition-colors text-white"
                title="ملء الشاشة"
              >
                {isFullscreen ? <Minimize2 className="w-4 h-4" /> : <Maximize2 className="w-4 h-4" />}
              </button>
            </div>
          </div>

          {/* Self Camera Feed (PiP Window) */}
          <div className="absolute bottom-24 right-5 w-36 sm:w-52 aspect-[3/4] bg-gray-900 rounded-2xl overflow-hidden border-2 border-white/20 shadow-2xl z-20 transition-all hover:scale-105">
            {isVideoOff ? (
              <div className="w-full h-full flex flex-col items-center justify-center bg-gray-800 text-gray-400 p-2 text-center">
                <User className="w-10 h-10 mb-1" />
                <span className="text-[10px]">الكاميرا معطلة</span>
              </div>
            ) : (
              <video
                ref={localVideoRef}
                autoPlay
                playsInline
                muted
                className="w-full h-full object-cover mirror scale-x-[-1]"
              />
            )}
            <div className="absolute bottom-1.5 right-1.5 left-1.5 px-2 py-0.5 bg-black/60 backdrop-blur-md rounded-lg text-[10px] text-white flex items-center justify-between">
              <span>أنت ({user?.full_name?.split(' ')[0]})</span>
              {isMuted && <MicOff className="w-3 h-3 text-red-400" />}
            </div>
          </div>

          {/* Bottom Call Controls Bar */}
          <div className="absolute bottom-0 inset-x-0 p-5 flex justify-center items-center bg-gradient-to-t from-black/90 via-black/50 to-transparent z-20">
            <div className="flex items-center gap-3 sm:gap-4 bg-white/10 backdrop-blur-2xl p-2.5 sm:p-3 rounded-2xl border border-white/15 shadow-2xl">
              {/* Mic Toggle */}
              <button
                onClick={toggleMute}
                className={`p-3.5 rounded-xl transition-all shadow-md ${
                  isMuted
                    ? 'bg-red-500/90 text-white hover:bg-red-600'
                    : 'bg-white/20 hover:bg-white/30 text-white'
                }`}
                title={isMuted ? 'إلغاء كتم الصوت' : 'كتم الميكروفون'}
              >
                {isMuted ? <MicOff className="w-5 h-5" /> : <Mic className="w-5 h-5" />}
              </button>

              {/* Video Toggle */}
              <button
                onClick={toggleVideo}
                className={`p-3.5 rounded-xl transition-all shadow-md ${
                  isVideoOff
                    ? 'bg-red-500/90 text-white hover:bg-red-600'
                    : 'bg-white/20 hover:bg-white/30 text-white'
                }`}
                title={isVideoOff ? 'تشغيل الكاميرا' : 'إيقاف الكاميرا'}
              >
                {isVideoOff ? <Video className="w-5 h-5 text-red-300" /> : <Video className="w-5 h-5" />}
              </button>

              {/* Screen Share Toggle */}
              <button
                onClick={toggleScreenShare}
                className={`p-3.5 rounded-xl transition-all shadow-md ${
                  isScreenSharing
                    ? 'bg-primary-600 text-white'
                    : 'bg-white/20 hover:bg-white/30 text-white'
                }`}
                title={isScreenSharing ? 'إيقاف مشاركة الشاشة' : 'مشاركة الشاشة'}
              >
                <MonitorUp className="w-5 h-5" />
              </button>

              {/* End Call Button */}
              <button
                onClick={endSession}
                className="p-3.5 sm:px-6 rounded-xl bg-red-600 hover:bg-red-500 text-white transition-all flex items-center gap-2 font-bold shadow-lg shadow-red-600/40"
                title="إنهاء الجلسة"
              >
                <PhoneOff className="w-5 h-5" />
                <span className="hidden sm:inline text-sm">إنهاء الجلسة</span>
              </button>
            </div>
          </div>
        </div>

        {/* Side Panel: Live Chat & Clinical Notes */}
        <div className="w-full lg:w-96 flex flex-col bg-white dark:bg-gray-800 rounded-3xl shadow-xl overflow-hidden border border-gray-100 dark:border-gray-700">
          {/* Tab Selector */}
          <div className="p-3 border-b border-gray-100 dark:border-gray-700 bg-gray-50/70 dark:bg-gray-900/50 flex gap-2">
            <button
              onClick={() => setSidePanelTab('chat')}
              className={`flex-1 py-2 rounded-xl text-xs font-bold transition-all flex items-center justify-center gap-1.5 ${
                sidePanelTab === 'chat'
                  ? 'bg-white dark:bg-gray-800 text-primary-600 dark:text-primary-400 shadow-sm'
                  : 'text-gray-500 hover:text-gray-800 dark:hover:text-gray-200'
              }`}
            >
              <MessageSquare className="w-4 h-4" />
              الدردشة المباشرة
            </button>
            {canManageSessions && (
              <button
                onClick={() => setSidePanelTab('notes')}
                className={`flex-1 py-2 rounded-xl text-xs font-bold transition-all flex items-center justify-center gap-1.5 ${
                  sidePanelTab === 'notes'
                    ? 'bg-white dark:bg-gray-800 text-primary-600 dark:text-primary-400 shadow-sm'
                    : 'text-gray-500 hover:text-gray-800 dark:hover:text-gray-200'
                }`}
              >
                <Stethoscope className="w-4 h-4" />
                الملاحظات والتشخيص
              </button>
            )}
          </div>

          {/* Chat Content */}
          {sidePanelTab === 'chat' ? (
            <>
              <div className="flex-1 overflow-y-auto p-4 space-y-3 max-h-[500px]">
                {messages.length === 0 ? (
                  <div className="text-center py-12 text-gray-400 text-xs">
                    لا توجد رسائل بعد. يمكنك بدء المحادثة الآن.
                  </div>
                ) : (
                  messages.map((msg, idx) => {
                    const isMine = msg.sender === user?.id;
                    return (
                      <div key={idx} className={`flex flex-col ${isMine ? 'items-end' : 'items-start'}`}>
                        <span className="text-[10px] text-gray-400 mb-1">
                          {isMine ? 'أنت' : msg.sender_name}
                        </span>
                        <div
                          className={`p-3 rounded-2xl max-w-[85%] text-xs leading-relaxed shadow-sm ${
                            isMine
                              ? 'bg-primary-600 text-white rounded-tl-none'
                              : 'bg-gray-100 dark:bg-gray-700 text-gray-900 dark:text-white rounded-tr-none'
                          }`}
                        >
                          {msg.content}
                        </div>
                      </div>
                    );
                  })
                )}
                <div ref={chatEndRef} />
              </div>

              {/* Chat Input */}
              <form
                onSubmit={sendMessage}
                className="p-3 border-t border-gray-100 dark:border-gray-700 bg-gray-50 dark:bg-gray-900/60"
              >
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={newMessage}
                    onChange={(e) => setNewMessage(e.target.value)}
                    placeholder="اكتب رسالة للمريض..."
                    className="flex-1 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl px-3 py-2 text-xs focus:ring-2 focus:ring-primary-500 outline-none text-gray-900 dark:text-white"
                  />
                  <button
                    type="submit"
                    disabled={!newMessage.trim()}
                    className="btn-primary p-2.5 rounded-xl disabled:opacity-50 transition-all flex items-center justify-center"
                  >
                    <MessageSquare className="w-4 h-4" />
                  </button>
                </div>
              </form>
            </>
          ) : (
            /* Clinical Notes Tab */
            <div className="flex-1 p-4 flex flex-col gap-4 overflow-y-auto">
              <div>
                <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1.5 flex items-center gap-1.5">
                  <Stethoscope className="w-3.5 h-3.5 text-primary-500" />
                  التشخيص المبدئي
                </label>
                <input
                  type="text"
                  placeholder="اكتب التشخيص المستنتج..."
                  value={clinicalDiagnosis}
                  onChange={(e) => setClinicalDiagnosis(e.target.value)}
                  className="w-full px-3 py-2 text-xs bg-gray-50 dark:bg-gray-700/50 border border-gray-200 dark:border-gray-700 rounded-xl focus:ring-2 focus:ring-primary-500 outline-none text-gray-900 dark:text-white"
                />
              </div>

              <div className="flex-1 flex flex-col">
                <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1.5 flex items-center gap-1.5">
                  <FileText className="w-3.5 h-3.5 text-primary-500" />
                  ملاحظات الطبيب وتوصيات العلاج
                </label>
                <textarea
                  rows={8}
                  placeholder="سجل تفاصيل الاستشارة، الخطة العلاجية، الأدوية الموصوفة..."
                  value={clinicalNotes}
                  onChange={(e) => setClinicalNotes(e.target.value)}
                  className="w-full flex-1 p-3 text-xs bg-gray-50 dark:bg-gray-700/50 border border-gray-200 dark:border-gray-700 rounded-xl focus:ring-2 focus:ring-primary-500 outline-none text-gray-900 dark:text-white resize-none"
                />
              </div>

              <button
                type="button"
                onClick={saveClinicalNotes}
                disabled={isSavingNotes}
                className="btn-primary w-full py-2.5 text-xs font-semibold inline-flex items-center justify-center gap-2 rounded-xl"
              >
                <Save className="w-4 h-4" />
                {isSavingNotes ? 'جارٍ حفظ الملاحظات...' : 'حفظ الملاحظات الطبية'}
              </button>
            </div>
          )}
        </div>
      </div>
    );
  }

  // Consultation Dashboard View
  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-2xl font-black text-gray-900 dark:text-white flex items-center gap-3">
            <div className="p-2.5 bg-primary-500/10 rounded-2xl text-primary-600 dark:text-primary-400">
              <Video className="w-6 h-6" />
            </div>
            العيادة الافتراضية والاستشارات عن بعد
          </h1>
          <p className="text-gray-500 dark:text-gray-400 text-sm mt-1">
            إدارة جلسات الطب الاتصالي المشفرة ومكالمات الفيديو الفورية مع المرضى
          </p>
        </div>

        {canManageSessions && (
          <button
            onClick={() => setShowCreateModal(true)}
            className="btn-primary px-5 py-2.5 rounded-xl font-bold flex items-center gap-2 shadow-lg shadow-primary-500/20 text-sm"
          >
            <Plus className="w-5 h-5" />
            جدولة استشارة جديدة
          </button>
        )}
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="card shadow-sm border border-gray-100 dark:border-gray-800 p-5 flex items-center justify-between">
          <div>
            <p className="text-xs font-semibold text-gray-500 dark:text-gray-400">جلسات قادمة</p>
            <h3 className="text-2xl font-bold text-gray-900 dark:text-white mt-1">
              {consultations.filter(c => c.status === 'SCHEDULED').length}
            </h3>
          </div>
          <div className="w-12 h-12 rounded-2xl bg-primary-50 dark:bg-primary-900/30 text-primary-600 dark:text-primary-400 flex items-center justify-center">
            <Calendar className="w-6 h-6" />
          </div>
        </div>

        <div className="card shadow-sm border border-gray-100 dark:border-gray-800 p-5 flex items-center justify-between">
          <div>
            <p className="text-xs font-semibold text-gray-500 dark:text-gray-400">جلسات جارية الآن</p>
            <h3 className="text-2xl font-bold text-gray-900 dark:text-white mt-1">
              {consultations.filter(c => c.status === 'IN_PROGRESS').length}
            </h3>
          </div>
          <div className="w-12 h-12 rounded-2xl bg-amber-50 dark:bg-amber-900/30 text-amber-600 dark:text-amber-400 flex items-center justify-center">
            <Clock className="w-6 h-6" />
          </div>
        </div>

        <div className="card shadow-sm border border-gray-100 dark:border-gray-800 p-5 flex items-center justify-between">
          <div>
            <p className="text-xs font-semibold text-gray-500 dark:text-gray-400">إجمالي الجلسات</p>
            <h3 className="text-2xl font-bold text-gray-900 dark:text-white mt-1">
              {consultations.length}
            </h3>
          </div>
          <div className="w-12 h-12 rounded-2xl bg-emerald-50 dark:bg-emerald-900/30 text-emerald-600 dark:text-emerald-400 flex items-center justify-center">
            <CheckCircle className="w-6 h-6" />
          </div>
        </div>
      </div>

      {/* Main List Container */}
      <div className="bg-white dark:bg-gray-800 border border-gray-100 dark:border-gray-700 rounded-3xl shadow-sm overflow-hidden flex flex-col min-h-[500px]">
        {/* Filter and Search Bar */}
        <div className="border-b border-gray-100 dark:border-gray-700 p-4 sm:px-6 flex flex-col sm:flex-row gap-4 justify-between items-center bg-gray-50/50 dark:bg-gray-900/50">
          <div className="flex gap-2 p-1 bg-gray-100 dark:bg-gray-900 rounded-xl w-full sm:w-auto">
            <button
              onClick={() => setActiveTab('upcoming')}
              className={`flex-1 sm:flex-none px-6 py-2 rounded-lg text-xs sm:text-sm font-bold transition-all ${
                activeTab === 'upcoming'
                  ? 'bg-white dark:bg-gray-800 text-gray-900 dark:text-white shadow-sm'
                  : 'text-gray-500 hover:text-gray-700 dark:hover:text-gray-300'
              }`}
            >
              المواعيد القادمة
            </button>
            <button
              onClick={() => setActiveTab('history')}
              className={`flex-1 sm:flex-none px-6 py-2 rounded-lg text-xs sm:text-sm font-bold transition-all ${
                activeTab === 'history'
                  ? 'bg-white dark:bg-gray-800 text-gray-900 dark:text-white shadow-sm'
                  : 'text-gray-500 hover:text-gray-700 dark:hover:text-gray-300'
              }`}
            >
              السجل السابق
            </button>
          </div>

          <div className="relative w-full sm:w-72">
            <Search className="w-4 h-4 absolute right-3 top-1/2 -translate-y-1/2 text-gray-400" />
            <input
              type="text"
              placeholder="ابحث باسم المريض أو الطبيب..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl pr-9 pl-3 py-2 text-xs focus:ring-2 focus:ring-primary-500 outline-none text-gray-900 dark:text-white"
            />
          </div>
        </div>

        {/* Consultations Grid */}
        <div className="p-4 sm:p-6 flex-1">
          {isLoading ? (
            <div className="flex justify-center items-center h-64">
              <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-primary-600"></div>
            </div>
          ) : filteredConsultations.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-64 text-center">
              <div className="w-16 h-16 bg-gray-50 dark:bg-gray-800 rounded-full flex items-center justify-center mb-3">
                <Video className="w-8 h-8 text-gray-400" />
              </div>
              <h3 className="text-base font-bold text-gray-900 dark:text-white">
                {consultations.length === 0 ? 'لا توجد جلسات مجدولة' : 'لا توجد نتائج للبحث'}
              </h3>
              <p className="text-gray-500 dark:text-gray-400 text-xs mt-1 max-w-sm">
                {consultations.length === 0 && canManageSessions
                  ? 'يمكنك جدولة أول استشارة عن بعد بالنقر على زر "جدولة استشارة جديدة"'
                  : 'لم يتم العثور على أي جلسات تطابق معايير البحث الحالية.'}
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              <AnimatePresence>
                {filteredConsultations.map((session, idx) => (
                  <motion.div
                    key={session.id}
                    initial={{ opacity: 0, y: 15 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, scale: 0.95 }}
                    transition={{ delay: idx * 0.04 }}
                    className="bg-white dark:bg-gray-900 border border-gray-100 dark:border-gray-700 p-5 rounded-2xl hover:shadow-lg transition-all group flex flex-col justify-between"
                  >
                    <div>
                      <div className="flex justify-between items-start mb-4">
                        <div className="flex items-center gap-3">
                          <div className="w-11 h-11 bg-primary-50 dark:bg-primary-900/30 text-primary-600 dark:text-primary-400 rounded-xl flex items-center justify-center font-bold text-base shadow-sm">
                            {session.patient_name?.charAt(0) || 'م'}
                          </div>
                          <div>
                            <h4 className="font-bold text-sm text-gray-900 dark:text-white">
                              {session.patient_name}
                            </h4>
                            <p className="text-[11px] text-gray-500 dark:text-gray-400">
                              الطبيب: {session.doctor_name}
                            </p>
                          </div>
                        </div>
                        <span
                          className={`px-2.5 py-0.5 rounded-full text-[11px] font-bold ${
                            session.status === 'SCHEDULED'
                              ? 'bg-amber-100 text-amber-700 dark:bg-amber-500/10 dark:text-amber-400'
                              : session.status === 'IN_PROGRESS'
                              ? 'bg-primary-100 text-primary-700 dark:bg-primary-500/10 dark:text-primary-400 animate-pulse'
                              : 'bg-emerald-100 text-emerald-700 dark:bg-emerald-500/10 dark:text-emerald-400'
                          }`}
                        >
                          {session.status === 'SCHEDULED'
                            ? 'مجدولة'
                            : session.status === 'IN_PROGRESS'
                            ? 'جارية الآن'
                            : 'مكتملة'}
                        </span>
                      </div>

                      {/* Diagnosis / Notes Preview */}
                      {session.diagnosis && (
                        <div className="p-2.5 mb-3 bg-gray-50 dark:bg-gray-800 rounded-xl text-xs text-gray-700 dark:text-gray-300">
                          <span className="font-semibold text-primary-600 dark:text-primary-400 block mb-0.5">
                            التشخيص المبدئي:
                          </span>
                          {session.diagnosis}
                        </div>
                      )}

                      <div className="space-y-1.5 mb-5 text-xs text-gray-600 dark:text-gray-400">
                        <div className="flex items-center gap-2">
                          <Calendar className="w-3.5 h-3.5 text-gray-400" />
                          <span>{new Date(session.scheduled_time).toLocaleDateString('ar-SA')}</span>
                        </div>
                        <div className="flex items-center gap-2">
                          <Clock className="w-3.5 h-3.5 text-gray-400" />
                          <span>
                            {new Date(session.scheduled_time).toLocaleTimeString('ar-SA', {
                              hour: '2-digit',
                              minute: '2-digit',
                            })}
                          </span>
                        </div>
                      </div>
                    </div>

                    {activeTab === 'upcoming' ? (
                      <button
                        onClick={() => joinSession(session)}
                        className="w-full btn-primary py-2 text-xs font-bold rounded-xl transition-all flex items-center justify-center gap-2 shadow-md shadow-primary-500/15"
                      >
                        <Video className="w-3.5 h-3.5" />
                        الانضمام لغرفة الاستشارة
                      </button>
                    ) : (
                      <div className="p-2.5 bg-gray-50 dark:bg-gray-800/60 rounded-xl text-xs text-gray-500 dark:text-gray-400 flex items-center justify-between">
                        <span>انتهت الجلسة</span>
                        <CheckCircle className="w-4 h-4 text-emerald-500" />
                      </div>
                    )}
                  </motion.div>
                ))}
              </AnimatePresence>
            </div>
          )}
        </div>
      </div>

      <CreateSessionModal
        isOpen={showCreateModal}
        onClose={() => setShowCreateModal(false)}
        onSuccess={fetchConsultations}
      />
    </div>
  );
}
