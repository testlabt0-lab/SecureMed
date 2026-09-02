import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Bed, Building2, UserPlus, LogOut, Search, Clock, AlertTriangle,
  CheckCircle, X, ChevronDown, Activity, Settings2, Trash2, Filter
} from 'lucide-react';
import toast from 'react-hot-toast';
import PageHeader from '../components/common/PageHeader';
import Card from '../components/common/Card';
import { wardsAPI } from '../api/extendedApis';

// ─── Types ───────────────────────────────────────────────────────────────
interface Ward {
  id: string;
  name: string;
  floor: string;
  is_active: boolean;
  total_beds: number;
  occupied_beds: number;
  rooms: Room[];
}

interface Room {
  id: string;
  ward: string;
  ward_name: string;
  room_number: string;
  room_type: string;
  is_active: boolean;
  beds: BedModel[];
}

interface BedModel {
  id: string;
  room: string;
  room_number: string;
  room_type: string;
  ward_name: string;
  bed_number: string;
  status: string;
  notes: string;
}

interface BedAssignment {
  id: string;
  bed: string;
  bed_details: BedModel;
  patient: string;
  patient_name: string;
  admitted_by_name: string;
  admission_date: string;
  discharge_date: string | null;
  diagnosis_on_admission: string;
  is_active: boolean;
}

interface WardStats {
  total_beds: number;
  occupied_beds: number;
  free_beds: number;
  maintenance_cleaning: number;
  occupancy_rate: number;
  active_admissions: number;
  admitted_today: number;
  discharged_today: number;
}

// ─── Helpers ─────────────────────────────────────────────────────────────
const extractArray = (data: any): any[] =>
  Array.isArray(data) ? data : Array.isArray(data?.results) ? data.results : [];

const statusConfig: Record<string, { label: string; cls: string; border: string }> = {
  FREE: { label: 'متاح', cls: 'bg-emerald-50 dark:bg-emerald-500/10 text-emerald-700 dark:text-emerald-400', border: 'border-emerald-200 dark:border-emerald-500/30' },
  OCCUPIED: { label: 'مشغول', cls: 'bg-rose-50 dark:bg-rose-500/10 text-rose-700 dark:text-rose-400', border: 'border-rose-200 dark:border-rose-500/30' },
  MAINTENANCE: { label: 'صيانة', cls: 'bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-400', border: 'border-slate-300 dark:border-slate-600' },
  CLEANING: { label: 'قيد التنظيف', cls: 'bg-blue-50 dark:bg-blue-500/10 text-blue-700 dark:text-blue-400', border: 'border-blue-200 dark:border-blue-500/30' },
  RESERVED: { label: 'محجوز', cls: 'bg-amber-50 dark:bg-amber-500/10 text-amber-700 dark:text-amber-400', border: 'border-amber-200 dark:border-amber-500/30' },
};

const roomTypeConfig: Record<string, string> = {
  GENERAL: 'عامة', PRIVATE: 'خاصة', ISOLATION: 'عزل', ICU: 'عناية مركزة', VIP: 'VIP'
};

// ─── Main Component ──────────────────────────────────────────────────────
export default function WardManagement() {
  const qc = useQueryClient();
  const [selectedWard, setSelectedWard] = useState<string>('');
  const [showAdmitModal, setShowAdmitModal] = useState<BedModel | null>(null);
  const [selectedBed, setSelectedBed] = useState<BedModel | null>(null);

  // Queries
  const { data: statsData } = useQuery({
    queryKey: ['wards-stats'],
    queryFn: () => wardsAPI.stats().then(r => r.data),
  });
  const stats: WardStats = statsData || {} as WardStats;

  const { data: wardsRaw } = useQuery({
    queryKey: ['wards-list'],
    queryFn: () => wardsAPI.wards().then(r => r.data),
  });
  const wards: Ward[] = extractArray(wardsRaw);

  const { data: assignmentsRaw } = useQuery({
    queryKey: ['wards-assignments-active'],
    queryFn: () => wardsAPI.assignments(true).then(r => r.data),
  });
  const activeAssignments: BedAssignment[] = extractArray(assignmentsRaw);

  // Default to first ward if none selected
  if (!selectedWard && wards.length > 0) {
    setSelectedWard(wards[0].id);
  }

  const currentWard = wards.find(w => w.id === selectedWard);

  // Find assignment for a specific bed
  const getAssignmentForBed = (bedId: string) => {
    return activeAssignments.find(a => a.bed === bedId);
  };

  // Mutations
  const dischargeMutation = useMutation({
    mutationFn: (id: string) => wardsAPI.discharge(id),
    onSuccess: () => {
      toast.success('تم إخراج المريض بنجاح');
      setSelectedBed(null);
      qc.invalidateQueries({ queryKey: ['wards-list'] });
      qc.invalidateQueries({ queryKey: ['wards-stats'] });
      qc.invalidateQueries({ queryKey: ['wards-assignments-active'] });
    },
    onError: (err: any) => toast.error(err?.response?.data?.detail || 'فشل إخراج المريض'),
  });

  const changeStatusMutation = useMutation({
    mutationFn: ({ id, status }: { id: string; status: string }) => wardsAPI.changeBedStatus(id, status),
    onSuccess: () => {
      toast.success('تم تحديث حالة السرير');
      setSelectedBed(null);
      qc.invalidateQueries({ queryKey: ['wards-list'] });
      qc.invalidateQueries({ queryKey: ['wards-stats'] });
    },
    onError: (err: any) => toast.error(err?.response?.data?.detail || 'فشل تحديث الحالة'),
  });

  return (
    <div className="space-y-6 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 animate-in fade-in zoom-in duration-500">
      <PageHeader
        title="إدارة الأسرّة والأجنحة"
        description="لوحة تحكم تفاعلية لإدارة إشغال الأسرّة، التنويم، وحالة الغرف"
        icon={<Bed className="w-8 h-8 text-indigo-500" />}
      />

      {/* ─── Stats Cards ───────────────────────────────────────────── */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { label: 'نسبة الإشغال', value: `${stats.occupancy_rate ?? 0}%`, icon: Activity, color: stats.occupancy_rate > 85 ? 'rose' : 'indigo' },
          { label: 'مرضى منومين', value: stats.active_admissions ?? 0, icon: Bed, color: 'blue' },
          { label: 'أسرّة متاحة', value: stats.free_beds ?? 0, icon: CheckCircle, color: 'emerald' },
          { label: 'دخول اليوم', value: stats.admitted_today ?? 0, icon: UserPlus, color: 'violet' },
        ].map((s, i) => (
          <div key={i} className={`relative overflow-hidden rounded-2xl border border-slate-200/60 dark:border-slate-700/60 bg-white dark:bg-slate-900 p-5 shadow-sm`}>
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-slate-500 dark:text-slate-400">{s.label}</p>
                <p className={`text-2xl font-bold mt-1 text-${s.color}-600 dark:text-${s.color}-400`}>{s.value}</p>
              </div>
              <div className={`p-3 rounded-xl bg-${s.color}-100 dark:bg-${s.color}-500/20`}>
                <s.icon className={`w-6 h-6 text-${s.color}-600 dark:text-${s.color}-400`} />
              </div>
            </div>
            <div className={`absolute bottom-0 left-0 right-0 h-1 bg-gradient-to-r from-${s.color}-400 to-${s.color}-600`} />
          </div>
        ))}
      </div>

      <div className="flex flex-col lg:flex-row gap-6">
        {/* ─── Sidebar: Wards List ────────────────────────────────── */}
        <div className="w-full lg:w-64 shrink-0 space-y-3">
          <h3 className="text-sm font-bold text-slate-500 uppercase tracking-wider mb-2">الأجنحة (Wards)</h3>
          {wards.map(ward => (
            <button
              key={ward.id}
              onClick={() => setSelectedWard(ward.id)}
              className={`w-full text-right p-4 rounded-xl border transition-all ${
                selectedWard === ward.id
                  ? 'border-indigo-500 bg-indigo-50 dark:bg-indigo-500/10 shadow-sm'
                  : 'border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 hover:border-indigo-300 dark:hover:border-indigo-600'
              }`}
            >
              <div className="flex justify-between items-center mb-1">
                <span className={`font-bold ${selectedWard === ward.id ? 'text-indigo-700 dark:text-indigo-300' : 'text-slate-700 dark:text-slate-300'}`}>
                  {ward.name}
                </span>
                <span className="text-xs text-slate-400">ط {ward.floor}</span>
              </div>
              <div className="flex items-center justify-between mt-2">
                <span className="text-xs text-slate-500 dark:text-slate-400">الإشغال:</span>
                <span className="text-sm font-medium text-slate-900 dark:text-white">
                  {ward.occupied_beds} / {ward.total_beds}
                </span>
              </div>
              <div className="w-full bg-slate-200 dark:bg-slate-700 rounded-full h-1.5 mt-2">
                <div
                  className={`h-1.5 rounded-full ${
                    (ward.occupied_beds / (ward.total_beds || 1)) > 0.85 ? 'bg-rose-500' : 'bg-indigo-500'
                  }`}
                  style={{ width: `${(ward.occupied_beds / (ward.total_beds || 1)) * 100}%` }}
                />
              </div>
            </button>
          ))}
        </div>

        {/* ─── Main Content: Visual Bed Map ───────────────────────── */}
        <div className="flex-1">
          {currentWard ? (
            <div className="space-y-6">
              <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
                <h2 className="text-2xl font-bold text-slate-900 dark:text-white">{currentWard.name}</h2>
                <div className="flex gap-2">
                  <div className="flex items-center gap-1.5 text-xs text-emerald-600"><div className="w-3 h-3 rounded-full bg-emerald-400" /> متاح</div>
                  <div className="flex items-center gap-1.5 text-xs text-rose-600"><div className="w-3 h-3 rounded-full bg-rose-400" /> مشغول</div>
                  <div className="flex items-center gap-1.5 text-xs text-blue-600"><div className="w-3 h-3 rounded-full bg-blue-400" /> تنظيف</div>
                  <div className="flex items-center gap-1.5 text-xs text-slate-500"><div className="w-3 h-3 rounded-full bg-slate-400" /> صيانة</div>
                </div>
              </div>

              {currentWard.rooms.length === 0 ? (
                <Card className="p-12 text-center">
                  <Building2 className="w-16 h-16 text-slate-300 dark:text-slate-600 mx-auto mb-4" />
                  <p className="text-slate-500">لا توجد غرف في هذا الجناح</p>
                </Card>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
                  {currentWard.rooms.map(room => (
                    <Card key={room.id} className="p-4 bg-slate-50/50 dark:bg-slate-900/50">
                      <div className="flex justify-between items-center mb-4 border-b border-slate-200 dark:border-slate-700 pb-2">
                        <div className="flex items-center gap-2">
                          <Building2 className="w-5 h-5 text-indigo-500" />
                          <h4 className="font-bold text-slate-900 dark:text-white">غرفة {room.room_number}</h4>
                        </div>
                        <span className="text-xs px-2 py-0.5 rounded-full bg-slate-200 text-slate-700 dark:bg-slate-700 dark:text-slate-300">
                          {roomTypeConfig[room.room_type] || room.room_type}
                        </span>
                      </div>
                      
                      {room.beds.length === 0 ? (
                        <p className="text-sm text-slate-500 text-center py-4">لا يوجد أسرّة</p>
                      ) : (
                        <div className="grid grid-cols-2 gap-3">
                          {room.beds.map(bed => {
                            const sc = statusConfig[bed.status] || statusConfig.FREE;
                            const assignment = getAssignmentForBed(bed.id);

                            return (
                              <button
                                key={bed.id}
                                onClick={() => setSelectedBed(bed)}
                                className={`flex flex-col items-center justify-center p-3 rounded-xl border-2 transition-all hover:scale-105 ${sc.cls} ${sc.border} ${selectedBed?.id === bed.id ? 'ring-2 ring-indigo-500 ring-offset-2 dark:ring-offset-slate-900' : ''}`}
                              >
                                <Bed className={`w-8 h-8 mb-2 ${bed.status === 'OCCUPIED' ? 'text-rose-500' : bed.status === 'FREE' ? 'text-emerald-500' : 'text-slate-400'}`} />
                                <span className="text-sm font-bold">سرير {bed.bed_number}</span>
                                {assignment && (
                                  <span className="text-xs font-medium truncate w-full text-center mt-1 opacity-90">
                                    {assignment.patient_name.split(' ')[0]}
                                  </span>
                                )}
                              </button>
                            );
                          })}
                        </div>
                      )}
                    </Card>
                  ))}
                </div>
              )}
            </div>
          ) : (
            <div className="flex items-center justify-center h-full min-h-[400px] text-slate-500">
              يرجى اختيار جناح لعرض الأسرّة
            </div>
          )}
        </div>
      </div>

      {/* ─── Bed Details & Actions Panel ───────────────────────── */}
      {selectedBed && (
        <div className="fixed bottom-0 left-0 right-0 z-40 p-4 pointer-events-none">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pointer-events-auto">
            <Card className="p-4 shadow-2xl border-t-4 border-indigo-500 animate-in slide-in-from-bottom-8 flex flex-col md:flex-row justify-between items-center gap-4">
              <div className="flex items-center gap-4">
                <div className={`p-3 rounded-full ${statusConfig[selectedBed.status]?.cls}`}>
                  <Bed className="w-6 h-6" />
                </div>
                <div>
                  <h3 className="text-lg font-bold text-slate-900 dark:text-white">
                    سرير {selectedBed.bed_number} <span className="text-sm font-normal text-slate-500">({selectedBed.room_number})</span>
                  </h3>
                  <div className="text-sm mt-0.5">
                    <span className="text-slate-500 mr-2">الحالة:</span>
                    <span className={`font-bold ${statusConfig[selectedBed.status]?.cls} px-2 py-0.5 rounded-full text-xs`}>
                      {statusConfig[selectedBed.status]?.label}
                    </span>
                  </div>
                </div>
              </div>

              {/* Dynamic Actions based on bed status */}
              <div className="flex flex-wrap items-center gap-2">
                {selectedBed.status === 'FREE' && (
                  <>
                    <button
                      onClick={() => setShowAdmitModal(selectedBed)}
                      className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl text-sm font-medium transition-colors flex items-center"
                    >
                      <UserPlus className="w-4 h-4 ml-2" /> تنويم مريض
                    </button>
                    <button
                      onClick={() => changeStatusMutation.mutate({ id: selectedBed.id, status: 'MAINTENANCE' })}
                      className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 dark:bg-slate-800 dark:hover:bg-slate-700 dark:text-slate-300 rounded-xl text-sm font-medium transition-colors"
                    >
                      <Settings2 className="w-4 h-4 ml-2" /> صيانة
                    </button>
                  </>
                )}

                {selectedBed.status === 'OCCUPIED' && getAssignmentForBed(selectedBed.id) && (
                  <button
                    onClick={() => {
                      if (confirm('تأكيد إخراج المريض؟ سيتم تحويل السرير إلى قيد التنظيف.')) {
                        dischargeMutation.mutate(getAssignmentForBed(selectedBed.id)!.id);
                      }
                    }}
                    disabled={dischargeMutation.isPending}
                    className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl text-sm font-medium transition-colors flex items-center disabled:opacity-50"
                  >
                    <LogOut className="w-4 h-4 ml-2" /> إخراج المريض (Discharge)
                  </button>
                )}

                {['MAINTENANCE', 'CLEANING'].includes(selectedBed.status) && (
                  <button
                    onClick={() => changeStatusMutation.mutate({ id: selectedBed.id, status: 'FREE' })}
                    disabled={changeStatusMutation.isPending}
                    className="px-4 py-2 bg-emerald-100 hover:bg-emerald-200 text-emerald-700 dark:bg-emerald-500/20 dark:hover:bg-emerald-500/30 dark:text-emerald-300 rounded-xl text-sm font-medium transition-colors flex items-center"
                  >
                    <CheckCircle className="w-4 h-4 ml-2" /> تعيين كمتاح
                  </button>
                )}

                <button
                  onClick={() => setSelectedBed(null)}
                  className="p-2 text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 bg-slate-50 hover:bg-slate-100 dark:bg-slate-800 dark:hover:bg-slate-700 rounded-xl transition-colors"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>
            </Card>
          </div>
        </div>
      )}

      {/* ─── Admission Modal ─────────────────────────────────────── */}
      {showAdmitModal && (
        <AdmissionModal
          bed={showAdmitModal}
          onClose={() => setShowAdmitModal(null)}
          onAdmitted={() => {
            setShowAdmitModal(null);
            setSelectedBed(null);
            qc.invalidateQueries({ queryKey: ['wards-list'] });
            qc.invalidateQueries({ queryKey: ['wards-stats'] });
            qc.invalidateQueries({ queryKey: ['wards-assignments-active'] });
          }}
        />
      )}
    </div>
  );
}

// ─── Admission Modal Component ───────────────────────────────────────────
function AdmissionModal({ bed, onClose, onAdmitted }: { bed: BedModel; onClose: () => void; onAdmitted: () => void }) {
  const [patientId, setPatientId] = useState('');
  const [diagnosis, setDiagnosis] = useState('');
  const [saving, setSaving] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!patientId) { toast.error('رقم المريض مطلوب'); return; }
    setSaving(true);
    try {
      await wardsAPI.createAssignment({
        bed: bed.id,
        patient: patientId,
        diagnosis_on_admission: diagnosis,
      });
      toast.success('تم تنويم المريض بنجاح');
      onAdmitted();
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || err?.response?.data?.patient?.[0] || 'فشل عملية التنويم');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4" onClick={onClose}>
      <div className="bg-white dark:bg-slate-900 rounded-2xl shadow-xl max-w-md w-full p-6" onClick={e => e.stopPropagation()}>
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-xl font-bold text-slate-900 dark:text-white">تنويم مريض</h2>
          <button onClick={onClose} className="p-2 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-xl transition-colors">
            <X className="w-5 h-5 text-slate-500" />
          </button>
        </div>
        
        <div className="mb-6 p-4 bg-indigo-50 dark:bg-indigo-500/10 rounded-xl flex items-center gap-3">
          <Bed className="w-8 h-8 text-indigo-500" />
          <div>
            <h4 className="font-bold text-indigo-900 dark:text-indigo-300">سرير {bed.bed_number}</h4>
            <p className="text-sm text-indigo-700 dark:text-indigo-400">{bed.ward_name} — {bed.room_number}</p>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">رقم المريض (UUID)</label>
            <input
              type="text"
              required
              value={patientId}
              onChange={e => setPatientId(e.target.value)}
              placeholder="00000000-0000-0000-0000-000000000000"
              className="w-full px-4 py-2.5 border border-slate-200 dark:border-slate-700 rounded-xl bg-slate-50/50 dark:bg-slate-800/50 text-slate-900 dark:text-white focus:ring-2 focus:ring-indigo-500/20 font-mono text-sm"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">التشخيص عند الدخول (اختياري)</label>
            <textarea
              value={diagnosis}
              onChange={e => setDiagnosis(e.target.value)}
              rows={3}
              placeholder="وصف حالة المريض عند التنويم..."
              className="w-full px-4 py-2.5 border border-slate-200 dark:border-slate-700 rounded-xl bg-slate-50/50 dark:bg-slate-800/50 text-slate-900 dark:text-white focus:ring-2 focus:ring-indigo-500/20 resize-none"
            />
          </div>
          <button type="submit" disabled={saving} className="w-full py-3 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl font-medium transition-colors disabled:opacity-50">
            {saving ? 'جارٍ الحفظ...' : 'تأكيد التنويم'}
          </button>
        </form>
      </div>
    </div>
  );
}
