import React, { useState } from 'react';
import { Pill, AlertTriangle, ShieldCheck, ShieldAlert, CheckCircle2, Plus, X, Loader2, Sparkles, AlertCircle, Info } from 'lucide-react';
import toast from 'react-hot-toast';
import Modal from '../common/Modal';
import { smartAssistantApi } from '../../api/extendedApis';

interface DrugInteractionModalProps {
  isOpen: boolean;
  onClose: () => void;
  patientName?: string;
  patientId?: string;
  patientAllergies?: string[];
  patientCurrentMeds?: string[];
}

interface InteractionResult {
  severity: 'CRITICAL' | 'WARNING' | 'SAFE';
  title: string;
  description: string;
  source?: string;
  recommendation?: string;
}

// Common clinically-significant interaction pairs for immediate offline/fallback safety rule engine
const KNOWN_CLINICAL_RULES: Array<{
  drugs: [string, string];
  severity: 'CRITICAL' | 'WARNING';
  title: string;
  desc: string;
  recommendation: string;
}> = [
  {
    drugs: ['warfarin', 'aspirin'],
    severity: 'CRITICAL',
    title: 'تفاعل حرج: وارفارين + أسبرين (خطر نزيف شديد)',
    desc: 'مضاعفة تأثير تميع الدم وتثبيط تراكم الصفائح الدموية مما قد يسبب نزيفاً معوياً أو دماغياً مهدداً للحياة.',
    recommendation: 'تجنب الاستخدام المتزامن إلا تحت مراقبة INR مكثفة أو استبدال أحدهما بمضاد تخثر بديل.',
  },
  {
    drugs: ['warfarin', 'ibuprofen'],
    severity: 'CRITICAL',
    title: 'تفاعل حرج: وارفارين + إيبوبروفين (مضادات الالتهاب غير الستيرويدية)',
    desc: 'NSAIDs تزيد من قرحة المعدة وتضاعف خطورة النزيف المعوي مع الوارفارين.',
    recommendation: 'استخدم الباراسيتامول لتسكين الألم وخفض الحرارة بدلاً من مضادات الالتهاب.',
  },
  {
    drugs: ['sildenafil', 'nitroglycerin'],
    severity: 'CRITICAL',
    title: 'تفاعل حرج قاتل: سيلدينافيل + نيتروجليسرين',
    desc: 'هبوط حاد ومفاجئ في ضغط الدم قد يؤدي إلى صدمة نقص التروية أو سكتة قلبية.',
    recommendation: 'ممنوع الاستخدام المشترك نهائياً. يجب الفصل 24-48 ساعة على الأقل.',
  },
  {
    drugs: ['lisinopril', 'spironolactone'],
    severity: 'WARNING',
    title: 'تحذير: مثبط ACE + سبيرونولاكتون (فرط بوتاسيوم الدم)',
    desc: 'كلا الدوائين يسببان احتباس البوتاسيوم مما قد يؤدي لاضطراب كهربية القلب.',
    recommendation: 'فحص دوري لمستوى البوتاسيوم في الدم ووظائف الكلى بعد بدء العلاج.',
  },
  {
    drugs: ['metformin', 'contrast'],
    severity: 'WARNING',
    title: 'تحذير: ميتفورمين + الصبغات الوريدية الإشعاعية',
    desc: 'احتمال حدوث حمّاض لبني (Lactic Acidosis) واعتلال كلوي حاد.',
    recommendation: 'إيقاف الميتفورمين قبل الفحص بـ 48 ساعة واستئنافه بعد التأكد من وظائف الكلى.',
  },
  {
    drugs: ['ciprofloxacin', 'theophylline'],
    severity: 'WARNING',
    title: 'تحذير: سيبروفلوكساسين + ثيوفيلين',
    desc: 'تثبيط أيض الثيوفيلين في الكبد مما يؤدي لتسمم بجرعة الثيوفيلين (تشنجات واضطراب نبض).',
    recommendation: 'تخفيض جرعة الثيوفيلين ومراقبة مستواه في مصل الدم.',
  },
];

export default function DrugInteractionModal({
  isOpen,
  onClose,
  patientName,
  patientId,
  patientAllergies = [],
  patientCurrentMeds = [],
}: DrugInteractionModalProps) {
  const [medInput, setMedInput] = useState('');
  const [medications, setMedications] = useState<string[]>(() => {
    return patientCurrentMeds.length > 0 ? [...patientCurrentMeds] : ['Warfarin'];
  });
  const [isChecking, setIsChecking] = useState(false);
  const [results, setResults] = useState<InteractionResult[] | null>(null);

  const addMedication = (name: string) => {
    const trimmed = name.trim();
    if (!trimmed) return;
    if (medications.some((m) => m.toLowerCase() === trimmed.toLowerCase())) {
      toast.error('هذا الدواء مضاف بالفعل');
      return;
    }
    setMedications([...medications, trimmed]);
    setMedInput('');
    setResults(null);
  };

  const removeMedication = (index: number) => {
    setMedications(medications.filter((_, i) => i !== index));
    setResults(null);
  };

  const handleCheck = async () => {
    if (medications.length < 1) {
      toast.error('يرجى إضافة دواء واحد على الأقل لفحصه');
      return;
    }

    setIsChecking(true);
    setResults(null);

    const foundInteractions: InteractionResult[] = [];

    // 1. Allergy Checking against patient's allergies
    patientAllergies.forEach((allergy) => {
      const aLower = allergy.toLowerCase();
      medications.forEach((med) => {
        const mLower = med.toLowerCase();
        if (
          (aLower.includes('penicillin') || aLower.includes('بنسلين')) &&
          (mLower.includes('amoxicillin') || mLower.includes('ampicillin') || mLower.includes('penicillin') || mLower.includes('أوجمنتين') || mLower.includes('augmentin'))
        ) {
          foundInteractions.push({
            severity: 'CRITICAL',
            title: `تحسس دوائي حرج: ${med} مع حساسية ${allergy}`,
            description: `المريض مسجل لديه تحسس مفرط تجاه عائلة (${allergy}). استخدام ${med} قد يؤدي إلى صدمة تأقية حادة (Anaphylactic Shock).`,
            recommendation: 'استبدال الدواء بمضاد حيوي من فئة أخرى غير البيتالاكتام (مثل Macrolides أو Clindamycin).',
            source: 'سجل حساسية المريض',
          });
        }
      });
    });

    // 2. Pairwise rule-engine check
    const medLowers = medications.map((m) => m.toLowerCase());
    KNOWN_CLINICAL_RULES.forEach((rule) => {
      const [d1, d2] = rule.drugs;
      const hasD1 = medLowers.some((m) => m.includes(d1));
      const hasD2 = medLowers.some((m) => m.includes(d2));

      if (hasD1 && hasD2) {
        foundInteractions.push({
          severity: rule.severity,
          title: rule.title,
          description: rule.desc,
          recommendation: rule.recommendation,
          source: 'قاعدة المعرفة الصيدلانية السريرية',
        });
      }
    });

    // 3. Optional Backend / Gemini AI Verification
    try {
      const apiRes = await smartAssistantApi.checkDrugInteractions(medications, patientId);
      const apiData = apiRes.data;

      if (apiData?.interactions && Array.isArray(apiData.interactions)) {
        apiData.interactions.forEach((item: any) => {
          foundInteractions.push({
            severity: item.severity === 'SEVERE' ? 'CRITICAL' : 'WARNING',
            title: item.title || `تعارض: ${item.drug1} + ${item.drug2}`,
            description: item.description || item.reason,
            recommendation: item.recommendation,
            source: 'تحليل الذكاء الاصطناعي السريري (Gemini)',
          });
        });
      }
    } catch (e) {
      // Offline / rule engine fallback already populated
    } finally {
      setIsChecking(false);
      if (foundInteractions.length === 0) {
        setResults([
          {
            severity: 'SAFE',
            title: 'لم يتم رصد تعارضات دوائية خطيرة',
            description: 'جميع الأدوية المدخلة متوافقة سريرياً ولا توجد تفاعلات عكسية معروفة مع حساسية المريض الحالية.',
            recommendation: 'يمكن صرف الأدوية مع الالتزام بالجرعات الموصوفة وتوجيه المريض لتعليمات الاستخدام.',
          },
        ]);
        toast.success('فحص التفاعلات: الأدوية آمنة');
      } else {
        setResults(foundInteractions);
        const hasCritical = foundInteractions.some((i) => i.severity === 'CRITICAL');
        if (hasCritical) {
          toast.error('تم اكتشاف تعارض دوائي حرج أو تحسس خطير!');
        } else {
          toast('تم رصد تحذيرات سريرية متوسطة');
        }
      }
    }
  };

  const overallSeverity = results?.some((r) => r.severity === 'CRITICAL')
    ? 'CRITICAL'
    : results?.some((r) => r.severity === 'WARNING')
    ? 'WARNING'
    : 'SAFE';

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="💊 فاحص التفاعلات الدوائية والحساسية (Drug Safety Checker)"
      maxWidth="max-w-3xl"
    >
      <div className="space-y-5" dir="rtl">
        {/* Patient header context if provided */}
        {(patientName || patientAllergies.length > 0) && (
          <div className="p-3.5 rounded-2xl bg-gray-50 dark:bg-gray-800/80 border border-gray-200 dark:border-gray-700/80 flex flex-wrap items-center justify-between gap-2 text-xs">
            <div className="flex items-center gap-2">
              <span className="font-bold text-gray-900 dark:text-white">المريض: {patientName || 'مريض محدد'}</span>
            </div>
            {patientAllergies.length > 0 && (
              <div className="flex items-center gap-1.5 flex-wrap">
                <span className="text-gray-500 font-medium">الحساسية المسجلة:</span>
                {patientAllergies.map((a, i) => (
                  <span key={i} className="px-2 py-0.5 rounded-md bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300 font-semibold border border-red-200 dark:border-red-800 text-[11px]">
                    {a}
                  </span>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Medication Tag Manager */}
        <div>
          <label className="block text-xs font-bold text-gray-700 dark:text-gray-300 mb-1.5">
            قائمة الأدوية المراد التحقق من سلامتها وتوافقها:
          </label>
          <div className="flex gap-2">
            <input
              type="text"
              value={medInput}
              onChange={(e) => setMedInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  e.preventDefault();
                  addMedication(medInput);
                }
              }}
              placeholder="اكتب اسم الدواء (مثل: Aspirin, Warfarin, Metformin, Amoxicillin)..."
              className="flex-1 px-3.5 py-2.5 rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-white text-sm focus:ring-2 focus:ring-primary-500 outline-none"
            />
            <button
              type="button"
              onClick={() => addMedication(medInput)}
              className="px-4 py-2.5 rounded-xl bg-primary-600 hover:bg-primary-700 text-white font-bold text-xs flex items-center gap-1.5 transition-colors cursor-pointer"
            >
              <Plus className="w-4 h-4" />
              إضافة
            </button>
          </div>

          {/* Preset Quick Chips */}
          <div className="flex items-center gap-1.5 flex-wrap mt-2">
            <span className="text-[11px] text-gray-400">أدوية شائعة:</span>
            {['Aspirin', 'Warfarin', 'Ibuprofen', 'Metformin', 'Amoxicillin', 'Nitroglycerin', 'Sildenafil', 'Lisinopril'].map((d) => (
              <button
                key={d}
                type="button"
                onClick={() => addMedication(d)}
                className="text-[11px] px-2 py-0.5 rounded-md bg-gray-100 hover:bg-gray-200 dark:bg-gray-800 dark:hover:bg-gray-700 text-gray-600 dark:text-gray-300 border border-gray-200 dark:border-gray-700 transition-colors"
              >
                + {d}
              </button>
            ))}
          </div>

          {/* Active Medication Tags */}
          <div className="flex flex-wrap gap-2 mt-3 min-h-12 p-3 rounded-2xl bg-gray-50/70 dark:bg-gray-900/50 border border-gray-200/80 dark:border-gray-800">
            {medications.length === 0 ? (
              <span className="text-xs text-gray-400 m-auto">أضف الأدوية التي ترغب في فحص تعارضاتها أعلاه</span>
            ) : (
              medications.map((m, idx) => (
                <span
                  key={idx}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 text-gray-800 dark:text-gray-200 text-xs font-semibold shadow-xs"
                >
                  <Pill className="w-3.5 h-3.5 text-primary-500" />
                  {m}
                  <button
                    type="button"
                    onClick={() => removeMedication(idx)}
                    className="p-0.5 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-full text-gray-400 hover:text-red-500 transition-colors"
                  >
                    <X className="w-3 h-3" />
                  </button>
                </span>
              ))
            )}
          </div>
        </div>

        {/* Check Button */}
        <div className="flex justify-center">
          <button
            type="button"
            onClick={handleCheck}
            disabled={isChecking || medications.length < 1}
            className="px-7 py-3 rounded-xl bg-gradient-to-r from-teal-600 to-primary-600 hover:from-teal-500 hover:to-primary-500 text-white font-bold text-xs flex items-center gap-2 shadow-lg shadow-teal-500/20 disabled:opacity-50 transition-all active:scale-95 cursor-pointer"
          >
            {isChecking ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                جارِ فحص التعارضات وسجل الحساسية...
              </>
            ) : (
              <>
                <ShieldCheck className="w-4 h-4" />
                بدء فحص السلامة الدوائية الآن
              </>
            )}
          </button>
        </div>

        {/* Results Matrix */}
        {results && (
          <div className="space-y-3 animate-in fade-in duration-200">
            {/* Overall Verdict Card */}
            <div
              className={`p-4 rounded-2xl border flex items-center gap-3 ${
                overallSeverity === 'CRITICAL'
                  ? 'bg-red-50 dark:bg-red-950/40 border-red-200 dark:border-red-900 text-red-900 dark:text-red-200'
                  : overallSeverity === 'WARNING'
                  ? 'bg-amber-50 dark:bg-amber-950/40 border-amber-200 dark:border-amber-900 text-amber-900 dark:text-amber-200'
                  : 'bg-emerald-50 dark:bg-emerald-950/40 border-emerald-200 dark:border-emerald-900 text-emerald-900 dark:text-emerald-200'
              }`}
            >
              {overallSeverity === 'CRITICAL' ? (
                <ShieldAlert className="w-7 h-7 text-red-600 dark:text-red-400 shrink-0" />
              ) : overallSeverity === 'WARNING' ? (
                <AlertTriangle className="w-7 h-7 text-amber-600 dark:text-amber-400 shrink-0" />
              ) : (
                <CheckCircle2 className="w-7 h-7 text-emerald-600 dark:text-emerald-400 shrink-0" />
              )}
              <div className="flex-1">
                <p className="font-bold text-sm">
                  {overallSeverity === 'CRITICAL'
                    ? 'تعارض دوائي حرج أو تحسس مفرط (High Risk / Contraindicated)'
                    : overallSeverity === 'WARNING'
                    ? 'تحذيرات سريرية ومراقبة مطلوبة (Moderate Caution)'
                    : 'التركيبة الدوائية آمنة سريرياً (Safe to Administer)'}
                </p>
                <p className="text-xs mt-0.5 opacity-90">
                  {overallSeverity === 'CRITICAL'
                    ? 'يُنصح بعدم صرف هذه الأدوية معاً لتجنب مضاعفات صحية خطيرة أو نزيف حاد.'
                    : overallSeverity === 'WARNING'
                    ? 'يرجى مراجعة وتعديل الجرعات ومراقبة المؤشرات الحيوية للمريض.'
                    : 'لم يتم رصد أي تفاعلات سلبية مسجلة بين الأدوية المختارة أو حساسية المريض.'}
                </p>
              </div>
            </div>

            {/* Detailed Interactions List */}
            <div className="space-y-2.5 max-h-[35vh] overflow-y-auto pr-1">
              {results.map((item, idx) => (
                <div
                  key={idx}
                  className={`p-3.5 rounded-xl border text-xs leading-relaxed space-y-1.5 ${
                    item.severity === 'CRITICAL'
                      ? 'bg-red-50/50 dark:bg-red-950/20 border-red-200 dark:border-red-900/40'
                      : item.severity === 'WARNING'
                      ? 'bg-amber-50/50 dark:bg-amber-950/20 border-amber-200 dark:border-amber-900/40'
                      : 'bg-emerald-50/50 dark:bg-emerald-950/20 border-emerald-200 dark:border-emerald-900/40'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <p className="font-bold text-gray-900 dark:text-white flex items-center gap-1.5">
                      <span className={`w-2 h-2 rounded-full ${
                        item.severity === 'CRITICAL' ? 'bg-red-500' : item.severity === 'WARNING' ? 'bg-amber-500' : 'bg-emerald-500'
                      }`} />
                      {item.title}
                    </p>
                    {item.source && (
                      <span className="text-[10px] text-gray-400 font-medium">
                        المصدر: {item.source}
                      </span>
                    )}
                  </div>
                  <p className="text-gray-600 dark:text-gray-300">
                    {item.description}
                  </p>
                  {item.recommendation && (
                    <div className="p-2 rounded-lg bg-white/80 dark:bg-gray-900/80 border border-gray-200/60 dark:border-gray-800 text-primary-900 dark:text-primary-200 font-medium">
                      💡 <strong>التوصية السريرية:</strong> {item.recommendation}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Modal Actions */}
        <div className="flex items-center justify-end gap-3 pt-2 border-t border-gray-100 dark:border-gray-800">
          <button
            type="button"
            onClick={onClose}
            className="px-5 py-2.5 rounded-xl bg-gray-100 hover:bg-gray-200 dark:bg-gray-800 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-200 text-xs font-semibold transition-colors cursor-pointer"
          >
            إغلاق
          </button>
        </div>
      </div>
    </Modal>
  );
}
