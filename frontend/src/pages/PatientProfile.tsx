import { useState, useMemo } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  ArrowRight, HeartPulse, FolderKanban, FileText, ImageIcon,
  Droplet, Calendar, Phone, Hash, AlertTriangle, Loader2, CreditCard,
  Sparkles, Copy, Check, RefreshCw, Plus, Search, Filter, Activity,
  Heart, Thermometer, Wind, CheckCircle2, Stethoscope, Clock, ShieldAlert,
  Mic, Wand2, BrainCircuit
} from 'lucide-react';
import { patientsExtendedApi, smartAssistantApi } from '../api/extendedApis';
import { patientsAPI } from '../api/client';
import api from '../api/client';
import Modal from '../components/common/Modal';

/** Minimal markdown renderer for the AI summary: headings, **bold**, bullets. */
function renderSummary(text: string) {
  return text.split('\n').map((line, i) => {
    if (!line.trim()) return <div key={i} className="h-1.5" />;
    const heading = /^#{1,4}\s*(.+)/.exec(line);
    const parts = (heading ? heading[1] : line).split(/(\*\*[^*]+\*\*)/g);
    const rendered = parts.map((p, j) =>
      p.startsWith('**') && p.endsWith('**') ? (
        <strong key={j} className="font-bold text-gray-900 dark:text-white">
          {p.slice(2, -2)}
        </strong>
      ) : (
        <span key={j}>{p}</span>
      ),
    );
    const isBullet = /^\s*[-•*]\s+/.test(line);
    if (heading) {
      return (
        <p key={i} className="font-bold text-medical-700 dark:text-medical-300 mt-2 mb-0.5">
          {heading[1].replace(/\*\*/g, '')}
        </p>
      );
    }
    return (
      <p key={i} className={`text-sm leading-6 ${isBullet ? 'pr-4' : ''}`}>
        {isBullet ? '• ' : ''}
        {rendered}
      </p>
    );
  });
}

const recordTypeLabels: Record<string, string> = {
  DIAGNOSIS: 'تشخيص',
  PRESCRIPTION: 'وصفة طبية',
  LAB_ORDER: 'طلب تحاليل',
  LAB_RESULT: 'نتيجة مختبر',
  VITALS: 'علامات حيوية',
  VITAL_SIGNS: 'علامات حيوية',
  NOTES: 'ملاحظات',
  NOTE: 'ملاحظات',
  IMAGING: 'تصوير طبي',
  PROCEDURE: 'إجراء طبي',
  OTHER: 'أخرى',
};

const recordTypeColors: Record<string, { bg: string; text: string; border: string }> = {
  DIAGNOSIS: { bg: 'bg-blue-50 dark:bg-blue-900/20', text: 'text-blue-700 dark:text-blue-300', border: 'border-blue-200 dark:border-blue-800' },
  PRESCRIPTION: { bg: 'bg-emerald-50 dark:bg-emerald-900/20', text: 'text-emerald-700 dark:text-emerald-300', border: 'border-emerald-200 dark:border-emerald-800' },
  LAB_RESULT: { bg: 'bg-amber-50 dark:bg-amber-900/20', text: 'text-amber-700 dark:text-amber-300', border: 'border-amber-200 dark:border-amber-800' },
  LAB_ORDER: { bg: 'bg-orange-50 dark:bg-orange-900/20', text: 'text-orange-700 dark:text-orange-300', border: 'border-orange-200 dark:border-orange-800' },
  VITALS: { bg: 'bg-purple-50 dark:bg-purple-900/20', text: 'text-purple-700 dark:text-purple-300', border: 'border-purple-200 dark:border-purple-800' },
  VITAL_SIGNS: { bg: 'bg-purple-50 dark:bg-purple-900/20', text: 'text-purple-700 dark:text-purple-300', border: 'border-purple-200 dark:border-purple-800' },
  IMAGING: { bg: 'bg-cyan-50 dark:bg-cyan-900/20', text: 'text-cyan-700 dark:text-cyan-300', border: 'border-cyan-200 dark:border-cyan-800' },
  PROCEDURE: { bg: 'bg-indigo-50 dark:bg-indigo-900/20', text: 'text-indigo-700 dark:text-indigo-300', border: 'border-indigo-200 dark:border-indigo-800' },
  NOTES: { bg: 'bg-gray-100 dark:bg-gray-800', text: 'text-gray-700 dark:text-gray-300', border: 'border-gray-200 dark:border-gray-700' },
  NOTE: { bg: 'bg-gray-100 dark:bg-gray-800', text: 'text-gray-700 dark:text-gray-300', border: 'border-gray-200 dark:border-gray-700' },
  OTHER: { bg: 'bg-gray-100 dark:bg-gray-800', text: 'text-gray-700 dark:text-gray-300', border: 'border-gray-200 dark:border-gray-700' },
};

const channelTypes: Record<string, string> = {
  EMERGENCY: 'حالة طارئة',
  INPATIENT: 'مريض مقيم',
  OUTPATIENT: 'مريض خارجي',
  CONSULTATION: 'استشارة',
  FOLLOW_UP: 'متابعة',
};

const priorityStyles: Record<string, string> = {
  LOW: 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300',
  MEDIUM: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300',
  HIGH: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-300',
  URGENT: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300',
};

function ageFrom(dob?: string) {
  if (!dob) return '—';
  const d = new Date(dob);
  const now = new Date();
  return String(now.getFullYear() - d.getFullYear());
}

export default function PatientProfile() {
  const { id } = useParams<{ id: string }>();
  const queryClient = useQueryClient();

  const [summary, setSummary] = useState<any>(null);
  const [copied, setCopied] = useState(false);

  // Timeline controls
  const [filterType, setFilterType] = useState<string>('ALL');
  const [searchQuery, setSearchQuery] = useState<string>('');

  // Modal and record creation state
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [successToast, setSuccessToast] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const [formData, setFormData] = useState({
    channel: '',
    record_type: 'DIAGNOSIS',
    title: '',
    content: '',
    is_critical: false,
    blood_pressure_systolic: '',
    blood_pressure_diastolic: '',
    heart_rate: '',
    temperature: '',
    respiratory_rate: '',
    oxygen_saturation: '',
  });

  const [triageResult, setTriageResult] = useState<any>(null);
  const [isRecording, setIsRecording] = useState(false);
  const [analyzingFileId, setAnalyzingFileId] = useState<string | null>(null);
  const [imageAnalysisResult, setImageAnalysisResult] = useState<{ id: string, result: string } | null>(null);

  const { data, isLoading, isError } = useQuery({
    queryKey: ['patient-profile', id],
    queryFn: () => patientsExtendedApi.profile(id!),
    enabled: !!id && id !== 'undefined',
  });

  const summaryMutation = useMutation({
    mutationFn: () => patientsExtendedApi.aiSummary(id!),
    onSuccess: (res) => setSummary(res.data),
  });

  const triageMutation = useMutation({
    mutationFn: () => smartAssistantApi.triage({
      patient: data?.data?.patient,
      symptoms: data?.data?.records?.filter((r: any) => r.record_type === 'DIAGNOSIS' || r.record_type === 'NOTES').map((r: any) => r.content).join(' '),
      vitals: latestVitals,
      lab_results: data?.data?.records?.filter((r: any) => r.record_type === 'LAB_RESULT'),
    }),
    onSuccess: (res) => setTriageResult(res.data),
  });

  const structureNoteMutation = useMutation({
    mutationFn: (text: string) => smartAssistantApi.structureNote(text),
    onSuccess: (res) => {
      setFormData(prev => ({ ...prev, content: res.data.structuredNote }));
    }
  });

  const handleStartRecording = () => {
    // @ts-ignore
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      alert("متصفحك لا يدعم التسجيل الصوتي (Web Speech API). يرجى استخدام متصفح مدعوم مثل Chrome.");
      return;
    }
    const recognition = new SpeechRecognition();
    recognition.lang = 'ar-SA';
    recognition.interimResults = false;
    recognition.onstart = () => setIsRecording(true);
    recognition.onresult = (event: any) => {
      const transcript = event.results[0][0].transcript;
      setFormData(prev => ({ ...prev, content: prev.content ? prev.content + ' ' + transcript : transcript }));
    };
    recognition.onend = () => setIsRecording(false);
    recognition.onerror = () => setIsRecording(false);
    recognition.start();
  };

  const handleAnalyzeImage = async (fileId: string) => {
    try {
      setAnalyzingFileId(fileId);
      setImageAnalysisResult(null);
      // 1. Download file as blob
      const res = await api.get(`/patients/files/${fileId}/download/`, { responseType: 'blob' });
      const blob = res.data;
      
      // 2. Convert to base64
      const reader = new FileReader();
      reader.readAsDataURL(blob);
      reader.onloadend = async () => {
        const base64data = reader.result as string;
        
        // 3. Send to AI
        try {
          const aiRes = await smartAssistantApi.analyzeImage(base64data);
          setImageAnalysisResult({ id: fileId, result: aiRes.data.analysis });
        } catch (err) {
          alert("خطأ أثناء تحليل الصورة بالذكاء الاصطناعي. يرجى التأكد أن خدمة الذكاء الاصطناعي تعمل.");
        } finally {
          setAnalyzingFileId(null);
        }
      };
    } catch (err) {
      alert("خطأ في تنزيل الملف للتحليل");
      setAnalyzingFileId(null);
    }
  };

  const createRecordMutation = useMutation({
    mutationFn: (payload: any) => patientsAPI.createRecord(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['patient-profile', id] });
      setIsModalOpen(false);
      setFormError(null);
      setSuccessToast('تمت إضافة السجل الطبي وتحديث الخط الزمني بنجاح');
      setTimeout(() => setSuccessToast(null), 4000);
      setFormData({
        channel: data?.data?.channels?.[0]?.id || '',
        record_type: 'DIAGNOSIS',
        title: '',
        content: '',
        is_critical: false,
        blood_pressure_systolic: '',
        blood_pressure_diastolic: '',
        heart_rate: '',
        temperature: '',
        respiratory_rate: '',
        oxygen_saturation: '',
      });
    },
    onError: (err: any) => {
      const msg =
        err.response?.data?.detail ||
        (err.response?.data?.channel && `القناة: ${err.response.data.channel[0]}`) ||
        (err.response?.data?.title && `العنوان: ${err.response.data.title[0]}`) ||
        (err.response?.data?.content && `المحتوى: ${err.response.data.content[0]}`) ||
        'تعذر حفظ السجل الطبي. يرجى التحقق من المدخلات والصلاحيات.';
      setFormError(msg);
    },
  });

  const copySummary = async () => {
    if (!summary?.summary) return;
    try {
      await navigator.clipboard.writeText(summary.summary);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch { /* clipboard unavailable */ }
  };

  const openAddRecordModal = () => {
    const defaultChannel = data?.data?.channels?.[0]?.id || '';
    setFormData((prev) => ({
      ...prev,
      channel: prev.channel || defaultChannel,
    }));
    setFormError(null);
    setIsModalOpen(true);
  };

  const handleSubmitRecord = (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.title.trim()) {
      setFormError('يرجى كتابة عنوان للسجل الطبي');
      return;
    }
    if (!formData.content.trim()) {
      setFormError('يرجى كتابة تفاصيل أو محتوى السجل الطبي');
      return;
    }
    if (!formData.channel && data?.data?.channels?.length > 0) {
      setFormError('يرجى اختيار القناة الطبية المرتبطة');
      return;
    }

    const payload: any = {
      record_type: formData.record_type,
      title: formData.title.trim(),
      content: formData.content.trim(),
      is_critical: formData.is_critical,
    };

    if (formData.channel) {
      payload.channel = formData.channel;
    }

    if (formData.record_type === 'VITALS') {
      if (formData.blood_pressure_systolic) payload.blood_pressure_systolic = parseInt(formData.blood_pressure_systolic);
      if (formData.blood_pressure_diastolic) payload.blood_pressure_diastolic = parseInt(formData.blood_pressure_diastolic);
      if (formData.heart_rate) payload.heart_rate = parseInt(formData.heart_rate);
      if (formData.temperature) payload.temperature = parseFloat(formData.temperature);
      if (formData.respiratory_rate) payload.respiratory_rate = parseInt(formData.respiratory_rate);
      if (formData.oxygen_saturation) payload.oxygen_saturation = parseInt(formData.oxygen_saturation);
    }

    createRecordMutation.mutate(payload);
  };

  // Filtered records
  const records = data?.data?.records || [];
  const filteredRecords = useMemo(() => {
    return records.filter((r: any) => {
      const matchesType =
        filterType === 'ALL' ||
        r.record_type === filterType ||
        (filterType === 'VITALS' && (r.record_type === 'VITALS' || r.record_type === 'VITAL_SIGNS')) ||
        (filterType === 'NOTES' && (r.record_type === 'NOTES' || r.record_type === 'NOTE'));

      const q = searchQuery.toLowerCase().trim();
      const matchesSearch =
        !q ||
        (r.title && r.title.toLowerCase().includes(q)) ||
        (r.content && r.content.toLowerCase().includes(q)) ||
        (r.channel_name && r.channel_name.toLowerCase().includes(q));

      return matchesType && matchesSearch;
    });
  }, [records, filterType, searchQuery]);

  // Latest vitals detection for quick summary card
  const latestVitals = useMemo(() => {
    return records.find(
      (r: any) =>
        r.record_type === 'VITALS' ||
        r.record_type === 'VITAL_SIGNS' ||
        r.blood_pressure_systolic ||
        r.heart_rate ||
        r.temperature,
    );
  }, [records]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-24">
        <Loader2 className="w-8 h-8 animate-spin text-primary-500" />
      </div>
    );
  }

  if (isError || !data?.data) {
    return (
      <div className="text-center py-24">
        <AlertTriangle className="w-12 h-12 text-red-400 mx-auto mb-3" />
        <p className="text-gray-500 mb-4">تعذر تحميل ملف المريض أو لا تملك صلاحية الوصول</p>
        <Link to="/patients" className="btn-secondary inline-flex items-center gap-2">
          <ArrowRight className="w-4 h-4" />
          العودة إلى قائمة المرضى
        </Link>
      </div>
    );
  }

  const { patient, channels, files, stats } = data.data;

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      {/* Success notification */}
      {successToast && (
        <div className="p-4 bg-emerald-50 dark:bg-emerald-900/30 border border-emerald-200 dark:border-emerald-800 rounded-xl flex items-center gap-3 text-emerald-800 dark:text-emerald-300 animate-in fade-in slide-in-from-top-2">
          <CheckCircle2 className="w-5 h-5 text-emerald-600 flex-shrink-0" />
          <span className="text-sm font-medium">{successToast}</span>
        </div>
      )}

      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <Link
            to="/patients"
            className="p-2.5 bg-white dark:bg-gray-800 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-xl shadow-sm border border-gray-100 dark:border-gray-700 transition-colors"
            aria-label="عودة"
          >
            <ArrowRight className="w-5 h-5 text-gray-500" />
          </Link>
          <div>
            <h1 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
              <HeartPulse className="w-6 h-6 text-medical-600" />
              ملف المريض والسجل الصحي
            </h1>
            <p className="text-gray-500 text-sm mt-0.5">
              السجل الكامل: {stats?.total_records || records.length} سجلات • {stats?.total_channels || channels.length} قنوات • {stats?.total_files || files.length} ملفات
            </p>
          </div>
        </div>

        <button
          onClick={openAddRecordModal}
          className="btn-primary inline-flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl shadow-md shadow-primary-500/10 font-semibold text-sm"
        >
          <Plus className="w-4 h-4" />
          إضافة سجل طبي
        </button>
      </div>

      {/* Patient info card */}
      <div className="card shadow-sm border border-gray-100 dark:border-gray-800">
        <div className="flex flex-col md:flex-row items-start md:items-center gap-5">
          <div className="w-20 h-20 bg-gradient-to-br from-medical-500 to-primary-500 rounded-2xl flex items-center justify-center flex-shrink-0 shadow-lg shadow-medical-500/20">
            <span className="text-white text-3xl font-bold">
              {patient.full_name?.charAt(0)}
            </span>
          </div>
          <div className="flex-1 w-full">
            <div className="flex flex-wrap items-center justify-between gap-2 mb-3">
              <h2 className="text-xl font-bold text-gray-900 dark:text-white">
                {patient.full_name}
              </h2>
              {patient.basin_name && (
                <span className="text-xs bg-primary-50 text-primary-700 dark:bg-primary-900/30 dark:text-primary-300 px-3 py-1 rounded-full font-medium border border-primary-100 dark:border-primary-800">
                  الحوض الصحي: {patient.basin_name}
                </span>
              )}
            </div>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              <div className="flex items-center gap-2 text-sm">
                <CreditCard className="w-4 h-4 text-gray-400" />
                <span className="text-gray-500">الهوية:</span>
                <span className="font-medium text-gray-900 dark:text-gray-100">{patient.national_id || '—'}</span>
              </div>
              <div className="flex items-center gap-2 text-sm">
                <Calendar className="w-4 h-4 text-gray-400" />
                <span className="text-gray-500">الميلاد:</span>
                <span className="font-medium text-gray-900 dark:text-gray-100">
                  {patient.date_of_birth} ({ageFrom(patient.date_of_birth)} سنة)
                </span>
              </div>
              <div className="flex items-center gap-2 text-sm">
                <Droplet className="w-4 h-4 text-gray-400" />
                <span className="text-gray-500">الدم:</span>
                <span className="font-bold text-red-600 dark:text-red-400">{patient.blood_type || '—'}</span>
              </div>
              <div className="flex items-center gap-2 text-sm">
                <Hash className="w-4 h-4 text-gray-400" />
                <span className="text-gray-500">الجنس:</span>
                <span className="font-medium text-gray-900 dark:text-gray-100">
                  {patient.gender === 'M' ? 'ذكر' : patient.gender === 'F' ? 'أنثى' : 'أخرى'}
                </span>
              </div>
              {patient.phone && (
                <div className="flex items-center gap-2 text-sm">
                  <Phone className="w-4 h-4 text-gray-400" />
                  <span className="text-gray-500">الهاتف:</span>
                  <span className="font-medium text-gray-900 dark:text-gray-100">{patient.phone}</span>
                </div>
              )}
              {patient.height && (
                <div className="flex items-center gap-2 text-sm">
                  <span className="text-gray-500">الطول:</span>
                  <span className="font-medium text-gray-900 dark:text-gray-100">{patient.height} سم</span>
                </div>
              )}
              {patient.weight && (
                <div className="flex items-center gap-2 text-sm">
                  <span className="text-gray-500">الوزن:</span>
                  <span className="font-medium text-gray-900 dark:text-gray-100">{patient.weight} كجم</span>
                </div>
              )}
            </div>

            {/* Medical alerts */}
            <div className="flex flex-wrap gap-2 mt-3">
              {patient.allergies && (
                <div className="flex items-center gap-2 px-3 py-1.5 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg text-xs text-red-700 dark:text-red-300">
                  <AlertTriangle className="w-3.5 h-3.5 text-red-500 flex-shrink-0" />
                  <span><strong>حساسية:</strong> {patient.allergies}</span>
                </div>
              )}
              {patient.chronic_conditions && (
                <div className="flex items-center gap-2 px-3 py-1.5 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg text-xs text-amber-700 dark:text-amber-300">
                  <Activity className="w-3.5 h-3.5 text-amber-500 flex-shrink-0" />
                  <span><strong>أمراض مزمنة:</strong> {patient.chronic_conditions}</span>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Latest Vitals Banner (if present) */}
      {latestVitals && (
        <div className="card bg-gradient-to-r from-purple-500/5 via-primary-500/5 to-transparent border border-purple-100 dark:border-purple-900/40 p-4">
          <div className="flex items-center justify-between gap-3 mb-3">
            <h3 className="text-sm font-bold text-gray-900 dark:text-white flex items-center gap-2">
              <Activity className="w-4 h-4 text-purple-600 dark:text-purple-400" />
              آخر قياس للمؤشرات الحيوية
            </h3>
            <span className="text-xs text-gray-400">
              {new Date(latestVitals.created_at).toLocaleDateString('ar', {
                year: 'numeric', month: 'short', day: 'numeric',
              })}
            </span>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
            {latestVitals.blood_pressure_systolic && (
              <div className="p-3 bg-white dark:bg-gray-800 rounded-xl border border-gray-100 dark:border-gray-700 text-center">
                <p className="text-xs text-gray-400 flex items-center justify-center gap-1">
                  <Stethoscope className="w-3 h-3 text-purple-500" /> ضغط الدم
                </p>
                <p className="text-lg font-bold text-gray-900 dark:text-white mt-0.5">
                  {latestVitals.blood_pressure_systolic}/{latestVitals.blood_pressure_diastolic || '—'}
                  <span className="text-xs font-normal text-gray-400 mr-1">mmHg</span>
                </p>
              </div>
            )}
            {latestVitals.heart_rate && (
              <div className="p-3 bg-white dark:bg-gray-800 rounded-xl border border-gray-100 dark:border-gray-700 text-center">
                <p className="text-xs text-gray-400 flex items-center justify-center gap-1">
                  <Heart className="w-3 h-3 text-red-500" /> النبض
                </p>
                <p className="text-lg font-bold text-gray-900 dark:text-white mt-0.5">
                  {latestVitals.heart_rate}
                  <span className="text-xs font-normal text-gray-400 mr-1">bpm</span>
                </p>
              </div>
            )}
            {latestVitals.temperature && (
              <div className="p-3 bg-white dark:bg-gray-800 rounded-xl border border-gray-100 dark:border-gray-700 text-center">
                <p className="text-xs text-gray-400 flex items-center justify-center gap-1">
                  <Thermometer className="w-3 h-3 text-amber-500" /> الحرارة
                </p>
                <p className="text-lg font-bold text-gray-900 dark:text-white mt-0.5">
                  {latestVitals.temperature}
                  <span className="text-xs font-normal text-gray-400 mr-1">°C</span>
                </p>
              </div>
            )}
            {latestVitals.oxygen_saturation && (
              <div className="p-3 bg-white dark:bg-gray-800 rounded-xl border border-gray-100 dark:border-gray-700 text-center">
                <p className="text-xs text-gray-400 flex items-center justify-center gap-1">
                  <Wind className="w-3 h-3 text-cyan-500" /> الأكسجين SpO2
                </p>
                <p className="text-lg font-bold text-gray-900 dark:text-white mt-0.5">
                  {latestVitals.oxygen_saturation}
                  <span className="text-xs font-normal text-gray-400 mr-1">%</span>
                </p>
              </div>
            )}
            {latestVitals.respiratory_rate && (
              <div className="p-3 bg-white dark:bg-gray-800 rounded-xl border border-gray-100 dark:border-gray-700 text-center">
                <p className="text-xs text-gray-400 flex items-center justify-center gap-1">
                  <Activity className="w-3 h-3 text-blue-500" /> التنفس
                </p>
                <p className="text-lg font-bold text-gray-900 dark:text-white mt-0.5">
                  {latestVitals.respiratory_rate}
                  <span className="text-xs font-normal text-gray-400 mr-1">/min</span>
                </p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* AI clinical summary */}
      <div className="card border-2 border-dashed border-medical-200 dark:border-medical-800 bg-gradient-to-l from-medical-50/60 to-transparent dark:from-medical-900/10">
        <div className="flex items-center justify-between gap-3 mb-3">
          <h3 className="font-bold flex items-center gap-2 text-gray-900 dark:text-white">
            <span className="w-8 h-8 bg-gradient-to-br from-medical-500 to-primary-500 rounded-lg flex items-center justify-center flex-shrink-0">
              <Sparkles className="w-4 h-4 text-white" />
            </span>
            الملخص الذكي للحالة
          </h3>
          <div className="flex items-center gap-2">
            {summary?.summary && (
              <button
                onClick={copySummary}
                className="p-2 hover:bg-white dark:hover:bg-gray-700 rounded-lg transition-colors text-gray-500"
                title="نسخ الملخص"
                aria-label="نسخ الملخص"
              >
                {copied ? <Check className="w-4 h-4 text-green-500" /> : <Copy className="w-4 h-4" />}
              </button>
            )}
            <button
              onClick={() => summaryMutation.mutate()}
              disabled={summaryMutation.isPending}
              className="btn-primary inline-flex items-center gap-2 text-sm disabled:opacity-60"
            >
              {summaryMutation.isPending ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  جارٍ التوليد...
                </>
              ) : summary?.summary ? (
                <>
                  <RefreshCw className="w-4 h-4" />
                  إعادة التوليد
                </>
              ) : (
                <>
                  <Sparkles className="w-4 h-4" />
                  توليد الملخص الذكي
                </>
              )}
            </button>
          </div>
        </div>

        {summaryMutation.isError && (
          <p className="text-sm text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-3">
            تعذر توليد الملخص الذكي — تأكد من تشغيل خدمة الذكاء الاصطناعي ثم أعد المحاولة
          </p>
        )}

        {summary?.summary ? (
          <div className="bg-white dark:bg-gray-800 rounded-lg p-4 border border-gray-100 dark:border-gray-700">
            {renderSummary(summary.summary)}
            <div className="flex flex-wrap items-center justify-between gap-2 mt-4 pt-3 border-t border-gray-100 dark:border-gray-700">
              <p className="text-[11px] text-gray-400 flex items-center gap-1.5">
                <AlertTriangle className="w-3 h-3 text-amber-400" />
                {summary.disclaimer || 'هذا الملخص مولّد آلياً ولا يُغني عن المراجعة الطبية البشرية'}
              </p>
              <p className="text-[11px] text-gray-400">
                مبني على {summary.records_used} سجل طبي
                {summary.generated_at && (
                  <> • {new Date(summary.generated_at).toLocaleString('ar', {
                    hour: '2-digit', minute: '2-digit', day: 'numeric', month: 'short',
                  })}</>
                )}
              </p>
            </div>
          </div>
        ) : null}
      </div>

      {/* AI Triage & Differential Diagnosis */}
      <div className="card border border-primary-200 dark:border-primary-900/50 bg-gradient-to-l from-primary-50/40 to-transparent dark:from-primary-900/10">
        <div className="flex items-center justify-between gap-3 mb-3">
          <h3 className="font-bold flex items-center gap-2 text-primary-900 dark:text-primary-100">
            <span className="w-8 h-8 bg-gradient-to-br from-primary-500 to-blue-500 rounded-lg flex items-center justify-center flex-shrink-0">
              <BrainCircuit className="w-4 h-4 text-white" />
            </span>
            المساعد التشخيصي (AI Triage)
          </h3>
          <button
            onClick={() => triageMutation.mutate()}
            disabled={triageMutation.isPending}
            className="btn-primary inline-flex items-center gap-2 text-sm disabled:opacity-60 bg-primary-600 hover:bg-primary-700"
          >
            {triageMutation.isPending ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                يتم التقييم...
              </>
            ) : triageResult?.triageResult ? (
              <>
                <RefreshCw className="w-4 h-4" />
                إعادة التقييم
              </>
            ) : (
              <>
                <BrainCircuit className="w-4 h-4" />
                اقتراح تشخيص
              </>
            )}
          </button>
        </div>

        {triageMutation.isError && (
          <p className="text-sm text-red-600 dark:text-red-400 p-3 bg-red-50 dark:bg-red-900/20 rounded-lg">
            تعذر الاتصال بخدمة الذكاء الاصطناعي للتشخيص.
          </p>
        )}

        {triageResult?.triageResult ? (
          <div className="bg-white dark:bg-gray-800 rounded-lg p-4 border border-gray-100 dark:border-gray-700 mt-2">
            {renderSummary(triageResult.triageResult)}
          </div>
        ) : (
          !triageMutation.isPending && !triageMutation.isError && (
            <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
              يُحلّل الأعراض، المؤشرات الحيوية، ونتائج المختبر لاقتراح تشخيصات تفريقية وتقييم خطورة الحالة للمساعدة في اتخاذ القرار السريري.
            </p>
          )
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Medical records timeline */}
        <div className="lg:col-span-2 space-y-4">
          <div className="card shadow-sm border border-gray-100 dark:border-gray-800">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-4">
              <h3 className="font-bold flex items-center gap-2 text-gray-900 dark:text-white">
                <FileText className="w-5 h-5 text-primary-600" />
                الخط الزمني للسجلات الطبية ({filteredRecords.length} من {records.length})
              </h3>
              <button
                onClick={openAddRecordModal}
                className="btn-secondary text-xs inline-flex items-center gap-1.5 self-start sm:self-auto py-1.5 px-3"
              >
                <Plus className="w-3.5 h-3.5" />
                إضافة سجل
              </button>
            </div>

            {/* Filter and Search Bar */}
            <div className="space-y-3 mb-5">
              <div className="relative">
                <Search className="w-4 h-4 text-gray-400 absolute right-3 top-1/2 -translate-y-1/2" />
                <input
                  type="text"
                  placeholder="ابحث في عناوين ومحتوى السجلات..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full pr-9 pl-3 py-2 text-sm bg-gray-50 dark:bg-gray-700/50 border border-gray-200 dark:border-gray-700 rounded-xl focus:outline-none focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500 transition-all text-gray-900 dark:text-white"
                />
              </div>

              {/* Filter Pills */}
              <div className="flex items-center gap-1.5 overflow-x-auto pb-1 text-xs scrollbar-none">
                {[
                  { key: 'ALL', label: 'الكل' },
                  { key: 'DIAGNOSIS', label: 'تشخيصات' },
                  { key: 'PRESCRIPTION', label: 'وصفات طبية' },
                  { key: 'VITALS', label: 'علامات حيوية' },
                  { key: 'LAB_RESULT', label: 'تحاليل' },
                  { key: 'IMAGING', label: 'تصوير' },
                  { key: 'NOTES', label: 'ملاحظات' },
                ].map((tab) => (
                  <button
                    key={tab.key}
                    onClick={() => setFilterType(tab.key)}
                    className={`px-3 py-1.5 rounded-lg whitespace-nowrap font-medium transition-all ${
                      filterType === tab.key
                        ? 'bg-primary-600 text-white shadow-sm shadow-primary-500/20'
                        : 'bg-gray-100 dark:bg-gray-700/60 text-gray-600 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700'
                    }`}
                  >
                    {tab.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Timeline records list */}
            {filteredRecords.length === 0 ? (
              <div className="text-center py-12 bg-gray-50 dark:bg-gray-800/50 rounded-2xl border border-dashed border-gray-200 dark:border-gray-700">
                <FileText className="w-10 h-10 text-gray-300 dark:text-gray-600 mx-auto mb-2" />
                <p className="text-gray-500 dark:text-gray-400 text-sm font-medium">
                  {records.length === 0
                    ? 'لا توجد سجلات طبية مسجلة بعد'
                    : 'لا توجد نتائج تطابق معايير البحث والتصفية'}
                </p>
                {records.length === 0 && (
                  <button
                    onClick={openAddRecordModal}
                    className="mt-3 text-xs text-primary-600 hover:text-primary-700 font-semibold inline-flex items-center gap-1"
                  >
                    <Plus className="w-3.5 h-3.5" />
                    أضف أول سجل طبي لهذا المريض
                  </button>
                )}
              </div>
            ) : (
              <div className="relative max-h-[580px] overflow-y-auto pr-3 pl-1">
                <div className="absolute right-[11px] top-2 bottom-2 w-0.5 bg-gray-200 dark:bg-gray-700" />
                <div className="space-y-4">
                  {filteredRecords.map((r: any) => {
                    const typeStyle = recordTypeColors[r.record_type] || recordTypeColors.OTHER;
                    const hasVitals =
                      r.blood_pressure_systolic ||
                      r.heart_rate ||
                      r.temperature ||
                      r.oxygen_saturation ||
                      r.respiratory_rate;

                    return (
                      <div key={r.id} className="relative pr-7 group">
                        {/* Timeline bullet */}
                        <div
                          className={`absolute right-1 top-2.5 w-4 h-4 rounded-full border-2 transition-transform group-hover:scale-125 ${
                            r.is_critical
                              ? 'bg-red-500 border-red-200 dark:border-red-900 shadow-sm shadow-red-500/40 animate-pulse'
                              : 'bg-primary-500 border-primary-200 dark:border-primary-900'
                          }`}
                        />

                        <div
                          className={`p-4 rounded-2xl border transition-all hover:shadow-md ${
                            r.is_critical
                              ? 'bg-red-50/40 dark:bg-red-950/20 border-red-200 dark:border-red-900/50'
                              : 'bg-white dark:bg-gray-800/80 border-gray-100 dark:border-gray-700/80 shadow-sm'
                          }`}
                        >
                          <div className="flex flex-wrap items-center justify-between gap-2 mb-2">
                            <div className="flex items-center gap-2">
                              <span
                                className={`text-xs font-bold px-2.5 py-0.5 rounded-full border ${typeStyle.bg} ${typeStyle.text} ${typeStyle.border}`}
                              >
                                {recordTypeLabels[r.record_type] || r.record_type_display || r.record_type}
                              </span>
                              {r.is_critical && (
                                <span className="inline-flex items-center gap-1 text-[11px] font-bold px-2 py-0.5 rounded-full bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300">
                                  <ShieldAlert className="w-3 h-3" />
                                  حالة حرجة
                                </span>
                              )}
                            </div>
                            <span className="text-xs text-gray-400 flex items-center gap-1">
                              <Clock className="w-3 h-3" />
                              {new Date(r.created_at).toLocaleDateString('ar', {
                                year: 'numeric',
                                month: 'short',
                                day: 'numeric',
                              })}
                            </span>
                          </div>

                          <h4 className="font-bold text-base text-gray-900 dark:text-white mb-1">
                            {r.title}
                          </h4>

                          {r.content && (
                            <p className="text-sm text-gray-600 dark:text-gray-300 whitespace-pre-line leading-relaxed">
                              {r.content}
                            </p>
                          )}

                          {/* Vital Signs Grid if included in this record */}
                          {hasVitals && (
                            <div className="mt-3 pt-3 border-t border-gray-100 dark:border-gray-700/60 grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs">
                              {r.blood_pressure_systolic && (
                                <div className="p-2 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
                                  <span className="text-gray-400 block">ضغط الدم</span>
                                  <strong className="text-gray-800 dark:text-gray-200">
                                    {r.blood_pressure_systolic}/{r.blood_pressure_diastolic || '—'} mmHg
                                  </strong>
                                </div>
                              )}
                              {r.heart_rate && (
                                <div className="p-2 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
                                  <span className="text-gray-400 block">النبض</span>
                                  <strong className="text-gray-800 dark:text-gray-200">{r.heart_rate} bpm</strong>
                                </div>
                              )}
                              {r.temperature && (
                                <div className="p-2 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
                                  <span className="text-gray-400 block">الحرارة</span>
                                  <strong className="text-gray-800 dark:text-gray-200">{r.temperature} °C</strong>
                                </div>
                              )}
                              {r.oxygen_saturation && (
                                <div className="p-2 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
                                  <span className="text-gray-400 block">الأكسجين</span>
                                  <strong className="text-gray-800 dark:text-gray-200">{r.oxygen_saturation}%</strong>
                                </div>
                              )}
                            </div>
                          )}

                          {/* Footer metadata */}
                          <div className="flex flex-wrap items-center justify-between gap-2 mt-3 pt-2 text-xs text-gray-400 border-t border-gray-50 dark:border-gray-700/30">
                            {r.created_by_name && (
                              <span className="flex items-center gap-1 text-gray-500 dark:text-gray-400">
                                <Stethoscope className="w-3 h-3 text-primary-500" />
                                مسجّل بواسطة: {r.created_by_name}
                              </span>
                            )}
                            {r.channel_name && (
                              <Link
                                to={`/channels/${r.channel}`}
                                className="flex items-center gap-1 hover:text-primary-600 transition-colors"
                              >
                                <FolderKanban className="w-3 h-3" />
                                {r.channel_name}
                              </Link>
                            )}
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Side column: channels + files */}
        <div className="space-y-6">
          <div className="card shadow-sm border border-gray-100 dark:border-gray-800">
            <h3 className="font-bold mb-4 flex items-center gap-2 text-gray-900 dark:text-white">
              <FolderKanban className="w-5 h-5 text-primary-600" />
              القنوات وحالات العلاج ({channels.length})
            </h3>
            {channels.length === 0 ? (
              <p className="text-center text-gray-400 py-6 text-sm">لا توجد قنوات مفتوحة</p>
            ) : (
              <div className="space-y-2 max-h-56 overflow-y-auto">
                {channels.map((c: any) => (
                  <Link
                    key={c.id}
                    to={`/channels/${c.id}`}
                    className="block p-3 bg-gray-50 dark:bg-gray-700/40 hover:bg-primary-50 dark:hover:bg-gray-700 rounded-xl transition-colors border border-transparent hover:border-primary-100 dark:hover:border-gray-600"
                  >
                    <div className="flex items-center justify-between gap-2">
                      <p className="text-sm font-semibold text-gray-900 dark:text-white truncate">
                        {c.name}
                      </p>
                      <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full flex-shrink-0 ${priorityStyles[c.priority] || ''}`}>
                        {c.priority}
                      </span>
                    </div>
                    <p className="text-xs text-gray-400 mt-1">
                      {channelTypes[c.channel_type] || c.channel_type}
                    </p>
                  </Link>
                ))}
              </div>
            )}
          </div>

          <div className="card shadow-sm border border-gray-100 dark:border-gray-800">
            <h3 className="font-bold mb-4 flex items-center gap-2 text-gray-900 dark:text-white">
              <ImageIcon className="w-5 h-5 text-primary-600" />
              الملفات والتقارير الطبية ({files.length})
            </h3>
            {files.length === 0 ? (
              <p className="text-center text-gray-400 py-6 text-sm">لا توجد ملفات مرفوعة</p>
            ) : (
              <div className="space-y-2 max-h-56 overflow-y-auto">
                {files.map((f: any) => (
                  <div
                    key={f.id}
                    className="flex flex-col gap-2 p-3 bg-gray-50 dark:bg-gray-700/40 rounded-xl border border-transparent hover:border-gray-200 dark:hover:border-gray-600 transition-colors"
                  >
                    <div className="flex items-center gap-3">
                      <div className="w-9 h-9 bg-primary-100 dark:bg-primary-900/30 text-primary-600 dark:text-primary-400 rounded-xl flex items-center justify-center flex-shrink-0">
                        <ImageIcon className="w-4 h-4" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-semibold text-gray-900 dark:text-white truncate">
                          {f.title}
                        </p>
                        <p className="text-xs text-gray-400">
                          {f.file_type_display} • {Math.round((f.file_size || 0) / 1024)} KB
                        </p>
                      </div>
                      
                      <button
                        onClick={() => handleAnalyzeImage(f.id)}
                        disabled={analyzingFileId === f.id}
                        title="تحليل الصورة بالذكاء الاصطناعي"
                        className="p-1.5 rounded-lg bg-indigo-50 text-indigo-600 hover:bg-indigo-100 dark:bg-indigo-900/30 dark:text-indigo-400 transition-colors disabled:opacity-50"
                      >
                        {analyzingFileId === f.id ? <Loader2 className="w-4 h-4 animate-spin" /> : <Wand2 className="w-4 h-4" />}
                      </button>

                      {f.is_critical && (
                        <AlertTriangle className="w-4 h-4 text-red-500 flex-shrink-0" />
                      )}
                    </div>

                    {/* AI Analysis Result */}
                    {imageAnalysisResult?.id === f.id && (
                      <div className="mt-1 p-3 bg-indigo-50 dark:bg-indigo-900/20 border border-indigo-100 dark:border-indigo-800 rounded-lg">
                        <h4 className="text-xs font-bold text-indigo-800 dark:text-indigo-300 mb-1 flex items-center gap-1">
                          <Sparkles className="w-3 h-3" /> نتيجة التحليل الذكي:
                        </h4>
                        <div className="text-xs text-indigo-900 dark:text-indigo-200">
                          {renderSummary(imageAnalysisResult!.result)}
                        </div>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Modal: Add Medical Record */}
      <Modal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        title="إضافة سجل طبي جديد"
        maxWidth="max-w-xl"
      >
        <form onSubmit={handleSubmitRecord} className="space-y-4">
          {formError && (
            <div className="p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-xl text-red-700 dark:text-red-300 text-xs flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 flex-shrink-0" />
              <span>{formError}</span>
            </div>
          )}

          {/* Channel selector */}
          {channels.length > 0 ? (
            <div>
              <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1.5">
                القناة الطبية / الحالة المرتبطة <span className="text-red-500">*</span>
              </label>
              <select
                value={formData.channel}
                onChange={(e) => setFormData({ ...formData, channel: e.target.value })}
                className="w-full px-3 py-2 text-sm bg-gray-50 dark:bg-gray-700/50 border border-gray-200 dark:border-gray-700 rounded-xl focus:ring-2 focus:ring-primary-500 focus:outline-none text-gray-900 dark:text-white"
                required
              >
                {channels.map((c: any) => (
                  <option key={c.id} value={c.id}>
                    {c.name} ({channelTypes[c.channel_type] || c.channel_type})
                  </option>
                ))}
              </select>
            </div>
          ) : (
            <div className="p-3 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-xl text-amber-800 dark:text-amber-300 text-xs">
              تنبيه: لا توجد قنوات علاجية مفتوحة لهذا المريض حالياً. يمكنك ربطه لاحقاً أو إنشاء قناة أولاً.
            </div>
          )}

          {/* Record type */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1.5">
                نوع السجل <span className="text-red-500">*</span>
              </label>
              <select
                value={formData.record_type}
                onChange={(e) => setFormData({ ...formData, record_type: e.target.value })}
                className="w-full px-3 py-2 text-sm bg-gray-50 dark:bg-gray-700/50 border border-gray-200 dark:border-gray-700 rounded-xl focus:ring-2 focus:ring-primary-500 focus:outline-none text-gray-900 dark:text-white"
              >
                <option value="DIAGNOSIS">تشخيص طبي (Diagnosis)</option>
                <option value="PRESCRIPTION">وصفة علاجية (Prescription)</option>
                <option value="VITALS">علامات حيوية (Vital Signs)</option>
                <option value="LAB_ORDER">طلب تحاليل (Lab Order)</option>
                <option value="LAB_RESULT">نتيجة تحاليل (Lab Result)</option>
                <option value="IMAGING">تصوير طبي (Imaging / Radiology)</option>
                <option value="PROCEDURE">إجراء أو جراحة (Procedure)</option>
                <option value="NOTES">ملاحظات سريرية (Clinical Notes)</option>
              </select>
            </div>

            {/* Title */}
            <div>
              <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1.5">
                العنوان <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                placeholder="مثال: تشخيص التهاب الشعب الهوائية"
                value={formData.title}
                onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                className="w-full px-3 py-2 text-sm bg-gray-50 dark:bg-gray-700/50 border border-gray-200 dark:border-gray-700 rounded-xl focus:ring-2 focus:ring-primary-500 focus:outline-none text-gray-900 dark:text-white"
                required
              />
            </div>
          </div>

          {/* Conditional Vital Signs Form */}
          {formData.record_type === 'VITALS' && (
            <div className="p-4 bg-purple-50/50 dark:bg-purple-950/20 border border-purple-100 dark:border-purple-900/40 rounded-2xl space-y-3">
              <h4 className="text-xs font-bold text-purple-900 dark:text-purple-300 flex items-center gap-1.5">
                <Activity className="w-3.5 h-3.5" />
                بيانات العلامات الحيوية المقاسة
              </h4>
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-2.5">
                <div>
                  <label className="block text-[11px] text-gray-600 dark:text-gray-400 mb-1">
                    ضغط الدم الانقباضي (Systolic)
                  </label>
                  <input
                    type="number"
                    placeholder="120"
                    value={formData.blood_pressure_systolic}
                    onChange={(e) => setFormData({ ...formData, blood_pressure_systolic: e.target.value })}
                    className="w-full px-2.5 py-1.5 text-xs bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg text-gray-900 dark:text-white"
                  />
                </div>
                <div>
                  <label className="block text-[11px] text-gray-600 dark:text-gray-400 mb-1">
                    ضغط الدم الانبساطي (Diastolic)
                  </label>
                  <input
                    type="number"
                    placeholder="80"
                    value={formData.blood_pressure_diastolic}
                    onChange={(e) => setFormData({ ...formData, blood_pressure_diastolic: e.target.value })}
                    className="w-full px-2.5 py-1.5 text-xs bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg text-gray-900 dark:text-white"
                  />
                </div>
                <div>
                  <label className="block text-[11px] text-gray-600 dark:text-gray-400 mb-1">
                    نبض القلب (Heart Rate - bpm)
                  </label>
                  <input
                    type="number"
                    placeholder="75"
                    value={formData.heart_rate}
                    onChange={(e) => setFormData({ ...formData, heart_rate: e.target.value })}
                    className="w-full px-2.5 py-1.5 text-xs bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg text-gray-900 dark:text-white"
                  />
                </div>
                <div>
                  <label className="block text-[11px] text-gray-600 dark:text-gray-400 mb-1">
                    درجة الحرارة (°C)
                  </label>
                  <input
                    type="number"
                    step="0.1"
                    placeholder="37.0"
                    value={formData.temperature}
                    onChange={(e) => setFormData({ ...formData, temperature: e.target.value })}
                    className="w-full px-2.5 py-1.5 text-xs bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg text-gray-900 dark:text-white"
                  />
                </div>
                <div>
                  <label className="block text-[11px] text-gray-600 dark:text-gray-400 mb-1">
                    الأكسجين (SpO2 %)
                  </label>
                  <input
                    type="number"
                    placeholder="98"
                    value={formData.oxygen_saturation}
                    onChange={(e) => setFormData({ ...formData, oxygen_saturation: e.target.value })}
                    className="w-full px-2.5 py-1.5 text-xs bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg text-gray-900 dark:text-white"
                  />
                </div>
                <div>
                  <label className="block text-[11px] text-gray-600 dark:text-gray-400 mb-1">
                    معدل التنفس (/min)
                  </label>
                  <input
                    type="number"
                    placeholder="18"
                    value={formData.respiratory_rate}
                    onChange={(e) => setFormData({ ...formData, respiratory_rate: e.target.value })}
                    className="w-full px-2.5 py-1.5 text-xs bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg text-gray-900 dark:text-white"
                  />
                </div>
              </div>
            </div>
          )}

          {/* Details / Notes */}
          <div>
            <div className="flex items-center justify-between mb-1.5">
              <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300">
                تفاصيل السجل والملاحظات السريرية <span className="text-red-500">*</span>
              </label>
              <div className="flex flex-wrap items-center gap-2">
                <button
                  type="button"
                  onClick={handleStartRecording}
                  className={`text-[11px] flex items-center gap-1 px-2 py-1 rounded-md transition-colors ${
                    isRecording 
                      ? 'bg-red-100 text-red-600 animate-pulse' 
                      : 'bg-gray-100 text-gray-600 hover:bg-gray-200 dark:bg-gray-700 dark:text-gray-300'
                  }`}
                >
                  <Mic className="w-3 h-3" />
                  {isRecording ? 'جاري التسجيل...' : 'إملاء صوتي'}
                </button>
                <button
                  type="button"
                  onClick={() => structureNoteMutation.mutate(formData.content)}
                  disabled={!formData.content || structureNoteMutation.isPending}
                  className="text-[11px] flex items-center gap-1 px-2 py-1 rounded-md bg-medical-50 text-medical-600 hover:bg-medical-100 disabled:opacity-50 transition-colors"
                >
                  {structureNoteMutation.isPending ? <Loader2 className="w-3 h-3 animate-spin" /> : <Wand2 className="w-3 h-3" />}
                  تنسيق SOAP ذكي
                </button>
              </div>
            </div>
            <textarea
              rows={5}
              placeholder="اكتب التقرير، أو استخدم الإملاء الصوتي ثم انقر على (تنسيق ذكي) لتحويل النص العشوائي إلى تقرير طبي مهيكل..."
              value={formData.content}
              onChange={(e) => setFormData({ ...formData, content: e.target.value })}
              className="w-full px-3 py-2 text-sm bg-gray-50 dark:bg-gray-700/50 border border-gray-200 dark:border-gray-700 rounded-xl focus:ring-2 focus:ring-primary-500 focus:outline-none text-gray-900 dark:text-white"
              required
            />
          </div>

          {/* Critical toggle */}
          <div className="flex items-center gap-2 p-3 bg-gray-50 dark:bg-gray-700/40 rounded-xl border border-gray-100 dark:border-gray-700">
            <input
              type="checkbox"
              id="is_critical"
              checked={formData.is_critical}
              onChange={(e) => setFormData({ ...formData, is_critical: e.target.checked })}
              className="w-4 h-4 text-red-600 rounded border-gray-300 focus:ring-red-500"
            />
            <label htmlFor="is_critical" className="text-xs font-medium text-gray-800 dark:text-gray-200 cursor-pointer">
              تحديد كحالة أو سجل حرج (يتطلب تنبيهاً فورياً ومتابعة دقيقة)
            </label>
          </div>

          {/* Buttons */}
          <div className="flex items-center justify-end gap-2 pt-2 border-t border-gray-100 dark:border-gray-700">
            <button
              type="button"
              onClick={() => setIsModalOpen(false)}
              className="btn-secondary text-sm px-4 py-2"
            >
              إلغاء
            </button>
            <button
              type="submit"
              disabled={createRecordMutation.isPending}
              className="btn-primary text-sm px-5 py-2 inline-flex items-center gap-2"
            >
              {createRecordMutation.isPending ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  جارٍ الحفظ المشفر...
                </>
              ) : (
                <>
                  <Check className="w-4 h-4" />
                  حفظ السجل
                </>
              )}
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
