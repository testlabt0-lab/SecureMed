import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Plus, Search, Users, Heart } from 'lucide-react';
import { patientsAPI } from '../api/client';
import toast from 'react-hot-toast';
import { useAuthStore } from '../store/authStore';

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
        {user && ['SUPER_ADMIN', 'HOSPITAL_ADMIN', 'CENTER_ADMIN', 'DOCTOR', 'NURSE', 'RECEPTIONIST'].includes(user.role) && (
          <button onClick={() => setShowCreate(true)} className="btn-primary flex items-center gap-2">
            <Plus className="w-4 h-4" />
            مريض جديد
          </button>
        )}
      </div>

      <div className="card">
        <div className="relative mb-4">
          <Search className="absolute right-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="بحث عن مريض..."
            className="input-field pr-10"
          />
        </div>

        {isLoading ? (
          <div className="text-center py-8 text-gray-500">جاري التحميل...</div>
        ) : patients.length === 0 ? (
          <div className="text-center py-12">
            <Users className="w-12 h-12 text-gray-300 mx-auto mb-3" />
            <p className="text-gray-500">لا يوجد مرضى بعد</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {patients.map((patient: any) => (
              <div key={patient.id} className="border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow">
                <div className="flex items-center gap-3 mb-3">
                  <div className="w-10 h-10 bg-medical-100 rounded-full flex items-center justify-center">
                    <Heart className="w-5 h-5 text-medical-600" />
                  </div>
                  <div>
                    <h3 className="font-bold text-gray-900">{patient.full_name}</h3>
                    <p className="text-xs text-gray-500">{patient.age} سنة • {patient.gender === 'M' ? 'ذكر' : 'أنثى'}</p>
                  </div>
                </div>
                <div className="space-y-1 text-sm">
                  {patient.blood_type && (
                    <div className="flex justify-between">
                      <span className="text-gray-500">فصيلة الدم:</span>
                      <span className="font-medium">{patient.blood_type}</span>
                    </div>
                  )}
                  {patient.phone && (
                    <div className="flex justify-between">
                      <span className="text-gray-500">الهاتف:</span>
                      <span className="font-medium">{patient.phone}</span>
                    </div>
                  )}
                  {patient.chronic_conditions && (
                    <div className="mt-2 p-2 bg-yellow-50 rounded text-xs text-yellow-800">
                      ⚠️ {patient.chronic_conditions}
                    </div>
                  )}
                </div>
                <div className="mt-3 pt-3 border-t border-gray-100 flex items-center justify-between gap-2">
                  <span className="text-xs text-gray-400">
                    أضيف: {new Date(patient.created_at).toLocaleDateString('ar-SA')}
                  </span>
                  <button
                    onClick={() => navigate(`/patients/${patient.id}`)}
                    className="text-xs font-medium text-primary-600 hover:text-primary-700 hover:bg-primary-50 px-2.5 py-1 rounded-lg transition-colors"
                  >
                    الملف الكامل ←
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

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
