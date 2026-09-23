import React, { useRef } from 'react';
import { Printer, QrCode, HeartPulse, Droplet, AlertTriangle, Phone, Calendar, CreditCard, ShieldCheck, X, Download } from 'lucide-react';
import Modal from '../common/Modal';

interface EmergencyPatient {
  id: string;
  full_name: string;
  national_id?: string;
  date_of_birth?: string;
  gender?: string;
  blood_type?: string;
  phone?: string;
  emergency_contact?: string;
  emergency_contact_name?: string;
  emergency_contact_phone?: string;
  chronic_conditions?: string[];
  allergies?: string[];
}

interface EmergencyMedicalCardModalProps {
  isOpen: boolean;
  onClose: () => void;
  patient: EmergencyPatient;
}

export default function EmergencyMedicalCardModal({
  isOpen,
  onClose,
  patient,
}: EmergencyMedicalCardModalProps) {
  const cardRef = useRef<HTMLDivElement>(null);

  const handlePrint = () => {
    window.print();
  };

  if (!isOpen || !patient) return null;

  const qrData = encodeURIComponent(
    `SECUREMED-EMERGENCY:ID=${patient.id};NAME=${patient.full_name};BLOOD=${patient.blood_type || 'UNK'}`
  );
  const qrUrl = `https://api.qrserver.com/v1/create-qr-code/?size=160x160&data=${qrData}`;

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="📄 بطاقة الطوارئ الطبية الذكية (Emergency Medical Card)"
      maxWidth="max-w-2xl"
    >
      <div className="space-y-6" dir="rtl">
        {/* Print Instruction Notice (hidden during print) */}
        <div className="p-3.5 rounded-2xl bg-teal-50 dark:bg-teal-950/30 border border-teal-200 dark:border-teal-900/40 flex items-center justify-between text-xs text-teal-800 dark:text-teal-200 no-print">
          <div className="flex items-center gap-2">
            <ShieldCheck className="w-4 h-4 text-teal-600 dark:text-teal-400 shrink-0" />
            <span>
              بطاقة هوية طبية معتمدة لحالات الطوارئ (CR80 Standard). تحوي بيانات الإسعاف الحرجة ورمز الاستجابة السريع.
            </span>
          </div>
          <button
            type="button"
            onClick={handlePrint}
            className="px-3.5 py-1.5 rounded-xl bg-teal-600 hover:bg-teal-700 text-white font-bold text-xs flex items-center gap-1.5 shadow-sm transition-colors cursor-pointer"
          >
            <Printer className="w-3.5 h-3.5" />
            طباعة البطاقة
          </button>
        </div>

        {/* The Card Itself (Formatted for screen and physical print) */}
        <div
          ref={cardRef}
          className="printable-area max-w-xl mx-auto rounded-3xl overflow-hidden border-2 border-primary-500/40 bg-gradient-to-br from-white via-gray-50 to-teal-50/30 dark:from-gray-900 dark:via-gray-900 dark:to-gray-950 p-6 shadow-2xl relative text-gray-900 dark:text-white"
        >
          {/* Card Header */}
          <div className="flex items-center justify-between border-b-2 border-primary-500/20 pb-4 mb-4">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 rounded-2xl bg-gradient-to-tr from-red-600 to-rose-500 text-white flex items-center justify-center shadow-md shadow-red-500/30">
                <HeartPulse className="w-7 h-7 animate-pulse" />
              </div>
              <div>
                <h2 className="text-base font-black text-gray-900 dark:text-white tracking-wide">
                  بطاقة الطوارئ الطبية السريعة
                </h2>
                <p className="text-[11px] font-bold text-primary-600 dark:text-primary-400">
                  SecureMed Emergency Medical ID
                </p>
              </div>
            </div>

            {/* Blood Type Badge */}
            <div className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-2xl bg-red-600 text-white shadow-md shadow-red-600/30">
              <Droplet className="w-4 h-4 fill-white" />
              <div className="text-center">
                <span className="text-[10px] block leading-none opacity-90">فصيلة الدم</span>
                <span className="text-base font-black tracking-wider leading-tight">
                  {patient.blood_type || '—'}
                </span>
              </div>
            </div>
          </div>

          {/* Patient Details & QR Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            {/* Demographic Info */}
            <div className="sm:col-span-2 space-y-3 text-xs">
              <div>
                <p className="text-[10px] font-bold text-gray-400 uppercase">اسم المريض الكامل</p>
                <p className="text-sm font-bold text-gray-900 dark:text-white mt-0.5">
                  {patient.full_name}
                </p>
              </div>

              <div className="grid grid-cols-2 gap-2">
                <div>
                  <p className="text-[10px] font-bold text-gray-400">رقم الهوية الوطنية</p>
                  <p className="font-mono font-semibold text-gray-800 dark:text-gray-200 mt-0.5">
                    {patient.national_id || '—'}
                  </p>
                </div>
                <div>
                  <p className="text-[10px] font-bold text-gray-400">تاريخ الميلاد</p>
                  <p className="font-semibold text-gray-800 dark:text-gray-200 mt-0.5">
                    {patient.date_of_birth || '—'}
                  </p>
                </div>
              </div>

              {/* Critical Allergies */}
              <div>
                <p className="text-[10px] font-bold text-red-600 dark:text-red-400 flex items-center gap-1">
                  <AlertTriangle className="w-3 h-3" />
                  الحساسية المفرطة المسجلة:
                </p>
                <div className="flex flex-wrap gap-1 mt-1">
                  {patient.allergies && patient.allergies.length > 0 ? (
                    patient.allergies.map((a: string, i: number) => (
                      <span
                        key={i}
                        className="px-2 py-0.5 rounded-md bg-red-100 dark:bg-red-900/40 text-red-700 dark:text-red-300 font-bold text-[11px] border border-red-300 dark:border-red-800"
                      >
                        {a}
                      </span>
                    ))
                  ) : (
                    <span className="text-gray-500 font-medium text-[11px]">لا توجد حساسية معروفة مسجلة</span>
                  )}
                </div>
              </div>

              {/* Chronic Conditions */}
              {patient.chronic_conditions && patient.chronic_conditions.length > 0 && (
                <div>
                  <p className="text-[10px] font-bold text-gray-400">الأمراض المزمنة:</p>
                  <div className="flex flex-wrap gap-1 mt-1">
                    {patient.chronic_conditions.map((c: string, i: number) => (
                      <span
                        key={i}
                        className="px-2 py-0.5 rounded-md bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 font-medium text-[11px] border border-gray-200 dark:border-gray-700"
                      >
                        {c}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Emergency Contact */}
              <div className="pt-2 border-t border-gray-200 dark:border-gray-800">
                <p className="text-[10px] font-bold text-gray-400">جهة الاتصال للطوارئ:</p>
                <p className="font-semibold text-gray-900 dark:text-white mt-0.5 flex items-center gap-2">
                  <Phone className="w-3.5 h-3.5 text-primary-500" />
                  <span>{patient.emergency_contact_name || 'ولي الأمر / المرافق'}</span>
                  <span className="font-mono text-primary-600 dark:text-primary-400">
                    ({patient.emergency_contact_phone || patient.phone || '—'})
                  </span>
                </p>
              </div>
            </div>

            {/* QR Code Column */}
            <div className="flex flex-col items-center justify-center p-3 rounded-2xl bg-white dark:bg-gray-950 border border-gray-200 dark:border-gray-800 text-center">
              <img
                src={qrUrl}
                alt="QR Code"
                className="w-28 h-28 object-contain rounded-lg shadow-sm"
              />
              <p className="text-[10px] font-bold text-gray-400 mt-2">
                مسح ضوئي إسعافي
              </p>
              <p className="text-[9px] text-primary-600 dark:text-primary-400 font-mono mt-0.5">
                {patient.id.slice(0, 8)}
              </p>
            </div>
          </div>

          {/* Watermark / Attribution footer on the card */}
          <div className="mt-4 pt-3 border-t border-gray-200/80 dark:border-gray-800 flex items-center justify-between text-[9px] text-gray-400">
            <span>منصة الرعاية الصحية الآمنة SecureMed • مشفرة بمعايير HIPAA</span>
            <span>تاريخ الإصدار: {new Date().toLocaleDateString('ar-SA')}</span>
          </div>
        </div>

        {/* Modal Actions */}
        <div className="flex items-center justify-end gap-3 pt-2 no-print">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 rounded-xl border border-gray-300 dark:border-gray-700 text-xs font-semibold text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
          >
            إغلاق
          </button>
          <button
            type="button"
            onClick={handlePrint}
            className="px-5 py-2 rounded-xl bg-gradient-to-r from-primary-600 to-teal-600 hover:from-primary-500 hover:to-teal-500 text-white font-bold text-xs flex items-center gap-1.5 shadow-md shadow-primary-500/20 cursor-pointer"
          >
            <Printer className="w-4 h-4" />
            طباعة البطاقة الطبية
          </button>
        </div>
      </div>
    </Modal>
  );
}
