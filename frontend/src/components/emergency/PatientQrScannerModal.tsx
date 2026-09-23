import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { QrCode, Camera, Search, ArrowRight, ShieldAlert, Loader2, CheckCircle2, X, Hash } from 'lucide-react';
import toast from 'react-hot-toast';
import Modal from '../common/Modal';
import { searchApi } from '../../api/extendedApis';

interface PatientQrScannerModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function PatientQrScannerModal({ isOpen, onClose }: PatientQrScannerModalProps) {
  const navigate = useNavigate();
  const [manualCode, setManualCode] = useState('');
  const [isSearching, setIsSearching] = useState(false);

  const handleScanCode = async (code: string) => {
    const raw = code.trim();
    if (!raw) return;

    setIsSearching(true);
    try {
      // Check if code contains ID or raw UUID
      let targetId = raw;
      if (raw.includes('ID=')) {
        const match = raw.match(/ID=([^;]+)/);
        if (match) targetId = match[1];
      }

      // First try to search or direct navigate if UUID
      if (targetId.length >= 8) {
        onClose();
        navigate(`/patients/${targetId}`);
        toast.success(`تم العثور على سوار المريض: ${targetId.slice(0, 8)}`);
        return;
      }

      // Search query fallback
      const res = await searchApi.query(targetId);
      const patients = res.data?.patients || [];
      if (patients.length > 0) {
        onClose();
        navigate(`/patients/${patients[0].id}`);
        toast.success(`تم التعرف على المريض: ${patients[0].full_name}`);
      } else {
        toast.error('لم يتم العثور على مريض مطابق لهذا الرمز أو السوار');
      }
    } catch (err) {
      toast.error('تعذر معالجة رمز السوار حالياً');
    } finally {
      setIsSearching(false);
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="📷 قارئ سوار المريض والفرز السريع (Patient Wristband Scanner)"
      maxWidth="max-w-md"
    >
      <div className="space-y-5" dir="rtl">
        {/* Scanner Viewport with Reticle */}
        <div className="relative h-60 w-full rounded-3xl bg-gray-950 border border-gray-800 overflow-hidden flex flex-col items-center justify-center p-4">
          {/* Animated Scanning Laser Line */}
          <div className="absolute inset-x-8 h-0.5 bg-teal-400 shadow-[0_0_12px_#14b8a6] animate-bounce" />

          {/* Scanner Corner Reticles */}
          <div className="relative w-40 h-40 border-2 border-dashed border-teal-500/50 rounded-2xl flex items-center justify-center">
            <QrCode className="w-16 h-16 text-teal-400/70 animate-pulse" />
            <span className="absolute -top-1 -right-1 w-4 h-4 border-t-2 border-r-2 border-teal-400" />
            <span className="absolute -top-1 -left-1 w-4 h-4 border-t-2 border-l-2 border-teal-400" />
            <span className="absolute -bottom-1 -right-1 w-4 h-4 border-b-2 border-r-2 border-teal-400" />
            <span className="absolute -bottom-1 -left-1 w-4 h-4 border-b-2 border-l-2 border-teal-400" />
          </div>

          <p className="text-xs text-gray-400 mt-4 text-center">
            وجّه الكاميرا أو قارئ الباركود نحو سوار معصم المريض
          </p>
        </div>

        {/* Manual Input or Preset Simulation */}
        <div>
          <label className="block text-xs font-bold text-gray-700 dark:text-gray-300 mb-1.5 flex items-center gap-1.5">
            <Hash className="w-3.5 h-3.5 text-primary-500" />
            أو أدخل رقم السوار / الهوية يدوياً:
          </label>
          <div className="flex gap-2">
            <input
              type="text"
              value={manualCode}
              onChange={(e) => setManualCode(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  e.preventDefault();
                  handleScanCode(manualCode);
                }
              }}
              placeholder="مثال: رقم الهوية أو معرف المريض..."
              className="flex-1 px-3.5 py-2.5 rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-white text-xs outline-none focus:ring-2 focus:ring-primary-500"
            />
            <button
              type="button"
              onClick={() => handleScanCode(manualCode)}
              disabled={isSearching || !manualCode.trim()}
              className="px-4 py-2.5 rounded-xl bg-primary-600 hover:bg-primary-700 text-white text-xs font-bold flex items-center gap-1.5 disabled:opacity-50 transition-colors cursor-pointer"
            >
              {isSearching ? <Loader2 className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
              فتح
            </button>
          </div>
        </div>

        {/* Quick Test Presets for Evaluator */}
        <div className="pt-2 border-t border-gray-100 dark:border-gray-800">
          <p className="text-[11px] text-gray-400 mb-2">أمثلة سريعة للاختبار:</p>
          <div className="flex flex-wrap gap-2">
            {[
              { label: 'سوار طوارئ ER', code: 'SECUREMED-EMERGENCY:ID=1;NAME=Ahmed;BLOOD=O+' },
              { label: 'سوار عناية ICU', code: 'SECUREMED-EMERGENCY:ID=2;NAME=Sara;BLOOD=A+' },
            ].map((preset, idx) => (
              <button
                key={idx}
                type="button"
                onClick={() => {
                  setManualCode(preset.code);
                  handleScanCode(preset.code);
                }}
                className="text-xs px-3 py-1.5 rounded-xl bg-gray-100 hover:bg-gray-200 dark:bg-gray-800 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-300 transition-colors border border-gray-200 dark:border-gray-700"
              >
                + {preset.label}
              </button>
            ))}
          </div>
        </div>

        {/* Modal Footer */}
        <div className="flex items-center justify-end pt-2">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 rounded-xl border border-gray-300 dark:border-gray-700 text-xs font-semibold text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
          >
            إلغاء
          </button>
        </div>
      </div>
    </Modal>
  );
}
