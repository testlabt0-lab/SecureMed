import React, { useState, useEffect, useRef } from 'react';
import { Mic, MicOff, Sparkles, Check, Copy, FileText, RotateCcw, Loader2, Volume2, Wand2, ShieldCheck } from 'lucide-react';
import toast from 'react-hot-toast';
import { smartAssistantApi } from '../../api/extendedApis';
import Modal from '../common/Modal';

interface MedicalScribeModalProps {
  isOpen: boolean;
  onClose: () => void;
  onInsertNote: (note: string) => void;
  patientName?: string;
}

export default function MedicalScribeModal({
  isOpen,
  onClose,
  onInsertNote,
  patientName,
}: MedicalScribeModalProps) {
  const [isRecording, setIsRecording] = useState(false);
  const [transcript, setTranscript] = useState('');
  const [structuredNote, setStructuredNote] = useState('');
  const [isStructuring, setIsStructuring] = useState(false);
  const [lang, setLang] = useState<'ar-SA' | 'en-US'>('ar-SA');
  const [copied, setCopied] = useState(false);

  const recognitionRef = useRef<any>(null);

  useEffect(() => {
    // Check Web Speech API availability
    const SpeechRecognition =
      (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;

    if (SpeechRecognition) {
      const recognition = new SpeechRecognition();
      recognition.continuous = true;
      recognition.interimResults = true;
      recognition.lang = lang;

      recognition.onresult = (event: any) => {
        let currentTranscript = '';
        for (let i = 0; i < event.results.length; i++) {
          currentTranscript += event.results[i][0].transcript + ' ';
        }
        setTranscript(currentTranscript.trim());
      };

      recognition.onerror = (err: any) => {
        console.warn('Speech recognition error:', err);
        setIsRecording(false);
        if (err.error === 'not-allowed') {
          toast.error('يرجى السماح بالوصول إلى الميكروفون في المتصفح');
        }
      };

      recognition.onend = () => {
        setIsRecording(false);
      };

      recognitionRef.current = recognition;
    }

    return () => {
      if (recognitionRef.current) {
        try {
          recognitionRef.current.stop();
        } catch (e) {
          // already stopped / recognition never started — nothing to clean up
        }
      }
    };
  }, [lang]);

  const toggleRecording = () => {
    if (!recognitionRef.current) {
      toast.error('متصفحك الحالي لا يدعم التعرف الصوتي المباشر. يمكنك كتابة الملاحظة وسيقوم الذكاء الاصطناعي بتنظيمها.');
      return;
    }

    if (isRecording) {
      try {
        recognitionRef.current.stop();
      } catch (e) {
        // stop() throws when the session already ended — safe to ignore here
      }
      setIsRecording(false);
      toast('تم إيقاف التسجيل الصوتي');
    } else {
      try {
        recognitionRef.current.lang = lang;
        recognitionRef.current.start();
        setIsRecording(true);
        toast.success('جارِ الاستماع لإملاء الطبيب...');
      } catch (e) {
        console.error(e);
        setIsRecording(false);
      }
    }
  };

  const handleStructureWithAI = async () => {
    if (!transcript.trim()) {
      toast.error('يرجى تسجيل أو كتابة ملاحظات طبية أولاً');
      return;
    }

    setIsStructuring(true);
    try {
      const res = await smartAssistantApi.structureNote(transcript.trim());
      const result = res.data?.structured || '';
      setStructuredNote(result);
      toast.success('تم تنظيم الملاحظة السريرية بصيغة SOAP بنجاح');
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'تعذر تنظيم الملاحظة حالياً');
    } finally {
      setIsStructuring(false);
    }
  };

  const handleCopy = () => {
    const textToCopy = structuredNote || transcript;
    navigator.clipboard.writeText(textToCopy);
    setCopied(true);
    toast.success('تم نسخ الملاحظة إلى الحافظة');
    setTimeout(() => setCopied(false), 2000);
  };

  const handleApply = () => {
    const textToInsert = structuredNote || transcript;
    if (!textToInsert.trim()) {
      toast.error('لا يوجد نص لإدراجه');
      return;
    }
    onInsertNote(textToInsert);
    toast.success('تم إدراج الملاحظة المنظمة في السجل الطبي');
    onClose();
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="🎙️ الكاتب الطبي الذكي (AI Clinical Scribe)"
      maxWidth="max-w-3xl"
    >
      <div className="space-y-5" dir="rtl">
        {/* Banner */}
        <div className="p-3.5 rounded-2xl bg-gradient-to-r from-teal-50 to-primary-50 dark:from-teal-950/30 dark:to-primary-950/30 border border-teal-200 dark:border-teal-900/40 flex items-center justify-between text-xs text-teal-900 dark:text-teal-200">
          <div className="flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-teal-600 dark:text-teal-400 shrink-0" />
            <span>
              سجل ملاحظاتك السريرية شفوياً، وسيقوم الذكاء الاصطناعي (Gemini) بصياغتها وتنظيمها إلى تقرير معتمد بتنسيق <strong>SOAP Note</strong>.
              {patientName && <span className="mr-1 text-teal-700 dark:text-teal-300 font-bold">(المريض: {patientName})</span>}
            </span>
          </div>

          <div className="flex items-center gap-2">
            <select
              value={lang}
              onChange={(e) => setLang(e.target.value as any)}
              disabled={isRecording}
              className="text-xs px-2.5 py-1 rounded-lg border border-teal-300 dark:border-teal-700 bg-white dark:bg-gray-800 text-teal-900 dark:text-teal-100 outline-none"
            >
              <option value="ar-SA">العربية (ar-SA)</option>
              <option value="en-US">English (en-US)</option>
            </select>
          </div>
        </div>

        {/* Microphone / Recording Wave Visualizer */}
        <div className="flex flex-col items-center justify-center p-5 rounded-3xl bg-gray-50 dark:bg-gray-900/60 border border-gray-200/80 dark:border-gray-800">
          <div className="relative">
            {isRecording && (
              <>
                <span className="absolute inset-0 rounded-full bg-red-500/20 animate-ping" />
                <span className="absolute -inset-2 rounded-full bg-red-500/10 animate-pulse" />
              </>
            )}
            <button
              type="button"
              onClick={toggleRecording}
              className={`relative z-10 w-16 h-16 rounded-full flex items-center justify-center text-white shadow-xl transition-all cursor-pointer ${
                isRecording
                  ? 'bg-gradient-to-r from-red-600 to-rose-600 scale-110 shadow-red-500/30'
                  : 'bg-gradient-to-r from-primary-600 to-teal-600 hover:from-primary-500 hover:to-teal-500 hover:scale-105 shadow-primary-500/25'
              }`}
            >
              {isRecording ? (
                <MicOff className="w-7 h-7 animate-pulse" />
              ) : (
                <Mic className="w-7 h-7" />
              )}
            </button>
          </div>

          <p className="text-xs font-semibold mt-3 text-gray-700 dark:text-gray-300">
            {isRecording ? 'جارِ الاستماع والإملاء... اضغط للإيقاف' : 'اضغط على الميكروفون لبدء التسجيل الصوتي'}
          </p>

          {/* Soundwave Simulation Bars */}
          {isRecording && (
            <div className="flex items-center gap-1 mt-3 h-6">
              {[40, 75, 100, 60, 90, 45, 80, 50, 95, 30, 85].map((h, i) => (
                <span
                  key={i}
                  className="w-1 bg-red-500 rounded-full animate-pulse"
                  style={{
                    height: `${h}%`,
                    animationDelay: `${(i * 0.1).toFixed(1)}s`,
                    animationDuration: '0.8s',
                  }}
                />
              ))}
            </div>
          )}
        </div>

        {/* Input / Transcript Area */}
        <div>
          <div className="flex items-center justify-between mb-1.5">
            <label className="text-xs font-bold text-gray-700 dark:text-gray-300 flex items-center gap-1.5">
              <Volume2 className="w-3.5 h-3.5 text-primary-500" />
              النص المفرغ من الإملاء الطبي (أو اكتب هنا يدوياً):
            </label>
            {transcript && (
              <button
                onClick={() => setTranscript('')}
                className="text-[11px] text-gray-400 hover:text-red-500 transition-colors"
              >
                مسح النص
              </button>
            )}
          </div>
          <textarea
            value={transcript}
            onChange={(e) => setTranscript(e.target.value)}
            rows={4}
            placeholder="مثال: مريض يشكو من صداع مستمر منذ يومين مع ارتفاع طفيف بالحرارة. الضغط 130/80، النبض 78، تم فحص قاع العين ولا توجد وذمة. الخطة: باراسيتامول 500 ملغ عند اللزوم ومراجعة بعد أسبوع إذا استمرت الأعراض..."
            className="w-full p-3.5 rounded-2xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-white text-sm focus:ring-2 focus:ring-primary-500 outline-none leading-relaxed"
          />
        </div>

        {/* Action button to structure with AI */}
        <div className="flex justify-center">
          <button
            type="button"
            onClick={handleStructureWithAI}
            disabled={isStructuring || !transcript.trim()}
            className="px-6 py-2.5 rounded-xl bg-gradient-to-r from-primary-600 via-indigo-600 to-teal-600 hover:from-primary-500 hover:to-teal-500 text-white font-bold text-xs flex items-center gap-2 shadow-lg shadow-primary-500/20 disabled:opacity-50 disabled:cursor-not-allowed transition-all active:scale-95 cursor-pointer"
          >
            {isStructuring ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                جارِ تنظيم التقرير السريري عبر الذكاء الاصطناعي...
              </>
            ) : (
              <>
                <Wand2 className="w-4 h-4" />
                تنظيم الملاحظة سريرياً بصيغة SOAP
              </>
            )}
          </button>
        </div>

        {/* Structured Output Area */}
        {structuredNote && (
          <div className="p-4 rounded-2xl bg-medical-50/50 dark:bg-gray-800/80 border border-medical-200 dark:border-medical-800/60 animate-in fade-in duration-200">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-bold text-medical-800 dark:text-medical-300 flex items-center gap-1.5">
                <FileText className="w-4 h-4" />
                الملاحظة السريرية المنظمة (SOAP Format):
              </span>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={handleCopy}
                  className="p-1.5 rounded-lg hover:bg-white dark:hover:bg-gray-700 text-gray-500 dark:text-gray-300 text-xs flex items-center gap-1 transition-colors"
                  title="نسخ"
                >
                  {copied ? <Check className="w-3.5 h-3.5 text-green-500" /> : <Copy className="w-3.5 h-3.5" />}
                  <span>{copied ? 'تم النسخ' : 'نسخ'}</span>
                </button>
              </div>
            </div>

            <textarea
              value={structuredNote}
              onChange={(e) => setStructuredNote(e.target.value)}
              rows={6}
              className="w-full p-3 rounded-xl border border-medical-200/80 dark:border-medical-700/50 bg-white dark:bg-gray-900 text-gray-900 dark:text-white text-xs font-mono leading-relaxed focus:ring-2 focus:ring-medical-500 outline-none"
            />
          </div>
        )}

        {/* Modal Actions */}
        <div className="flex items-center justify-end gap-3 pt-2 border-t border-gray-100 dark:border-gray-800">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 rounded-xl border border-gray-300 dark:border-gray-700 text-xs font-semibold text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
          >
            إغلاق
          </button>

          <button
            type="button"
            onClick={handleApply}
            disabled={!structuredNote && !transcript.trim()}
            className="px-5 py-2 rounded-xl bg-gradient-to-r from-medical-600 to-teal-600 hover:from-medical-500 hover:to-teal-500 text-white font-bold text-xs flex items-center gap-1.5 shadow-md shadow-medical-600/20 disabled:opacity-50 cursor-pointer"
          >
            <Check className="w-4 h-4" />
            إدراج في السجل الطبي للمريض
          </button>
        </div>
      </div>
    </Modal>
  );
}
