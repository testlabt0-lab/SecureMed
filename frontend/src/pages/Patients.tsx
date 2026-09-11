import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Plus, Search, Users, Heart } from 'lucide-react';
import { patientsAPI } from '../api/client';
import toast from 'react-hot-toast';
import { useAuthStore } from '../store/authStore';
import { CARE_TEAM_ROLES } from '../constants/roles';
import { ListSkeleton, EmptyState } from '../components/common/States';

export default function Patients() {
  const navigate = useNavigate();
  const [search, setSearch] = useState('');
  const [showCreate, setShowCreate] = useState(false);
  const queryClient = useQueryClient();
  const user = useAuthStore(state => state.user);

  const { data: patientsData, isLoading } = useQuery({
    queryKey: ['patients', { search }],
    queryFn: () => patientsAPI.list({ search }),
  });

  const createMutation = useMutation({
    mutationFn: (data: any) => patientsAPI.create(data),
    onSuccess: () => {
      toast.success('تم إضافة المريض بنجاح');
      queryClient.invalidateQueries({ queryKey: ['patients'] });
      setShowCreate(false);
    },
    onError: (err: any) => toast.error(err.response?.data?.detail || 'فشل'),
  });

  const patients = Array.isArray(patientsData?.data?.results) ? patientsData.data.results : (Array.isArray(patientsData?.data) ? patientsData.data : []);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">المرضى</h1>
          <p className="text-gray-600 text-sm mt-1">إدارة سجلات المرضى (مشفرة)</p>
        </div>
        {user && CARE_TEAM_ROLES.includes(user.role) && (
          <button onClick={() => setShowCreate(true)} className="btn-primary flex items-center gap-2">
            <Plus className="w-4 h-4" />
            مريض جديد
          </button>
        )}
      </div>

      <div className="glass p-4 rounded-2xl flex items-center mb-6">
        <div className="relative w-full max-w-md">
          <Search className="absolute right-4 top-1/2 -translate-y-1/2 w-5 h-5 text-primary-500/50" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="ابحث عن مريض بالاسم، رقم الهوية..."
            className="input-field pr-12 w-full border-transparent focus:border-primary-500 shadow-sm"
          />
        </div>
      </div>

        {isLoading ? (
          <ListSkeleton rows={6} />
        ) : patients.length === 0 ? (
          <EmptyState
            icon={<Users className="w-7 h-7" />}
            title="لا يوجد مرضى بعد"
            description="سيظهر المرضى هنا بمجرد إنشاء أول ملف مريض"
          />
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
            {patients.map((patient: any) => (
              <div key={patient.id} className="glass relative overflow-hidden rounded-3xl p-5 hover:shadow-xl hover:-translate-y-1 transition-all duration-300 group">
                <div className="absolute top-0 right-0 w-32 h-32 bg-medical-500/10 rounded-full blur-3xl -mr-16 -mt-16 pointer-events-none group-hover:bg-medical-500/20 transition-colors" />
                <div className="flex items-center gap-4 mb-4 relative z-10">
                  <div className="w-12 h-12 bg-gradient-to-br from-medical-100 to-medical-200 dark:from-medical-900/40 dark:to-medical-800/40 rounded-2xl flex items-center justify-center shadow-inner-light">
                    <Heart className="w-6 h-6 text-medical-600 dark:text-medical-400" />
                  </div>
                  <div>
                    <h3 className="font-bold text-gray-900 dark:text-white text-lg">{patient.full_name}</h3>
                    <p className="text-xs text-gray-500 dark:text-gray-400 font-medium">{patient.age} سنة • {patient.gender === 'M' ? 'ذكر' : 'أنثى'}</p>
                  </div>
                </div>
                <div className="space-y-2.5 text-sm relative z-10">
                  {patient.blood_type && (
                    <div className="flex justify-between items-center bg-gray-50/50 dark:bg-navy-800/50 px-3 py-1.5 rounded-xl">
                      <span className="text-gray-500 dark:text-gray-400">فصيلة الدم</span>
                      <span className="font-bold text-red-500">{patient.blood_type}</span>
                    </div>
                  )}
                  {patient.phone && (
                    <div className="flex justify-between items-center bg-gray-50/50 dark:bg-navy-800/50 px-3 py-1.5 rounded-xl">
                      <span className="text-gray-500 dark:text-gray-400">الهاتف</span>
                      <span className="font-medium dark:text-gray-300">{patient.phone}</span>
                    </div>
                  )}
                  {patient.chronic_conditions && (
                    <div className="mt-3 p-3 bg-gradient-to-r from-amber-50 to-orange-50 dark:from-amber-900/20 dark:to-orange-900/20 rounded-xl border border-amber-100/50 dark:border-amber-700/30 text-xs text-amber-800 dark:text-amber-400 flex gap-2">
                      <span className="text-amber-500 shrink-0">⚠️</span>
                      <span className="leading-relaxed">{patient.chronic_conditions}</span>
                    </div>
                  )}
                </div>
                <div className="mt-5 pt-4 border-t border-gray-100 dark:border-navy-700/50 flex items-center justify-between gap-2 relative z-10">
                  <span className="text-xs text-gray-400">
                    أضيف: {new Date(patient.created_at).toLocaleDateString('ar-SA')}
                  </span>
                  <button
                    onClick={() => navigate(`/patients/${patient.id}`)}
                    className="text-xs font-bold text-primary-600 dark:text-primary-400 hover:text-white hover:bg-primary-600 px-4 py-2 rounded-xl transition-all duration-300"
                  >
                    الملف الكامل ←
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}

      {showCreate && (
        <CreatePatientModal
          onSubmit={(data: any) => createMutation.mutate(data)}
          onClose={() => setShowCreate(false)}
          loading={createMutation.isPending}
        />
      )}
    </div>
  );
}

function CreatePatientModal({ onSubmit, onClose, loading }: any) {
  const [formData, setFormData] = useState({
    full_name: '',
    national_id: '',
    phone: '',
    address: '',
    date_of_birth: '',
    gender: 'M',
    blood_type: '',
    height: '',
    weight: '',
    allergies: '',
    chronic_conditions: '',
    current_medications: '',
    emergency_contact: '',
  });

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4 overflow-y-auto">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-2xl p-6 my-8 max-h-[90vh] overflow-y-auto">
        <h2 className="text-xl font-bold mb-4">إضافة مريض جديد</h2>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            onSubmit({
              ...formData,
              height: formData.height ? parseInt(formData.height) : null,
              weight: formData.weight ? parseInt(formData.weight) : null,
            });
          }}
          className="space-y-4"
        >
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">الاسم الكامل</label>
              <input
                type="text"
                value={formData.full_name}
                onChange={(e) => setFormData({ ...formData, full_name: e.target.value })}
                required
                className="input-field"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">رقم الهوية</label>
              <input
                type="text"
                value={formData.national_id}
                onChange={(e) => setFormData({ ...formData, national_id: e.target.value })}
                className="input-field"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">تاريخ الميلاد</label>
              <input
                type="date"
                value={formData.date_of_birth}
                onChange={(e) => setFormData({ ...formData, date_of_birth: e.target.value })}
                required
                className="input-field"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">الجنس</label>
              <select
                value={formData.gender}
                onChange={(e) => setFormData({ ...formData, gender: e.target.value })}
                className="input-field"
              >
                <option value="M">ذكر</option>
                <option value="F">أنثى</option>
                <option value="O">أخرى</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">الهاتف</label>
              <input
                type="text"
                value={formData.phone}
                onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                className="input-field"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">فصيلة الدم</label>
              <select
                value={formData.blood_type}
                onChange={(e) => setFormData({ ...formData, blood_type: e.target.value })}
                className="input-field"
              >
                <option value="">غير محدد</option>
                {['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-'].map(t => (
                  <option key={t} value={t}>{t}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">الطول (سم)</label>
              <input
                type="number"
                value={formData.height}
                onChange={(e) => setFormData({ ...formData, height: e.target.value })}
                className="input-field"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">الوزن (كجم)</label>
              <input
                type="number"
                value={formData.weight}
                onChange={(e) => setFormData({ ...formData, weight: e.target.value })}
                className="input-field"
              />
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">العنوان</label>
            <input
              type="text"
              value={formData.address}
              onChange={(e) => setFormData({ ...formData, address: e.target.value })}
              className="input-field"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">الحساسية</label>
            <input
              type="text"
              value={formData.allergies}
              onChange={(e) => setFormData({ ...formData, allergies: e.target.value })}
              className="input-field"
              placeholder="مثال: البنسلين، الفول السوداني"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">الأمراض المزمنة</label>
            <textarea
              value={formData.chronic_conditions}
              onChange={(e) => setFormData({ ...formData, chronic_conditions: e.target.value })}
              rows={2}
              className="input-field"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">جهة اتصال طارئة</label>
            <input
              type="text"
              value={formData.emergency_contact}
              onChange={(e) => setFormData({ ...formData, emergency_contact: e.target.value })}
              className="input-field"
            />
          </div>
          <div className="flex gap-2 pt-2">
            <button type="submit" disabled={loading} className="btn-primary flex-1">
              {loading ? 'جاري الحفظ...' : 'حفظ المريض'}
            </button>
            <button type="button" onClick={onClose} className="btn-secondary flex-1">إلغاء</button>
          </div>
        </form>
      </div>
    </div>
  );
}

