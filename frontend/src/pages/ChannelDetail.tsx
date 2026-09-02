import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  ArrowRight, Users, Shield, Plus, MoreVertical,
  UserPlus, Edit2, Trash2, Ban, X, Clock, Activity, Upload, FileText, Download, Paperclip,
  MessagesSquare, SendHorizonal, FileDown
} from 'lucide-react';
import { useState, useRef, useEffect } from 'react';
import { channelsAPI, patientsAPI, usersAPI } from '../api/client';
import { chatApi, reportsApi, downloadBlobResponse } from '../api/extendedApis';
import { useAuthStore } from '../store/authStore';
import toast from 'react-hot-toast';
import ChannelChat from '../components/ChannelChat';

const roleLabels: Record<string, string> = {
  OWNER: 'مالك القناة',
  MODERATOR: 'مشرف',
  EDITOR: 'محرر',
  CONTRIBUTOR: 'مساهم',
  VIEWER: 'مشاهد',
};

const roleColors: Record<string, string> = {
  OWNER: 'badge-info',
  MODERATOR: 'badge-success',
  EDITOR: 'badge-warning',
  CONTRIBUTOR: 'badge-info',
  VIEWER: 'badge-success',
};

export default function ChannelDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { user } = useAuthStore();
  const queryClient = useQueryClient();
  const [showAddMember, setShowAddMember] = useState(false);
  const [showActions, setShowActions] = useState<string | null>(null);
  const [downloadingReport, setDownloadingReport] = useState(false);

  const handleDownloadReport = async () => {
    setDownloadingReport(true);
    const toastId = toast.loading('جاري توليد تقرير PDF...');
    try {
      const response = await reportsApi.channelPdf(id!);
      downloadBlobResponse(response, `SecureMed_Channel_Report.pdf`);
      toast.success('تم تنزيل التقرير', { id: toastId });
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'فشل توليد التقرير', { id: toastId });
    } finally {
      setDownloadingReport(false);
    }
  };

  const { data: channelData, isLoading } = useQuery({
    queryKey: ['channel', id],
    queryFn: () => channelsAPI.get(id!),
    enabled: !!id,
  });

  const { data: membersData } = useQuery({
    queryKey: ['channel-members', id],
    queryFn: () => channelsAPI.members(id!),
    enabled: !!id,
  });

  const { data: recordsData } = useQuery({
    queryKey: ['channel-records', id],
    queryFn: () => patientsAPI.records({ channel: id }),
    enabled: !!id,
  });

  const { data: usersData } = useQuery({
    queryKey: ['users-medical'],
    queryFn: () => usersAPI.list(),
  });

  const grantMutation = useMutation({
    mutationFn: (data: any) => channelsAPI.grantPermission(id!, data),
    onSuccess: () => {
      toast.success('تم منح الصلاحية بنجاح');
      queryClient.invalidateQueries({ queryKey: ['channel-members', id] });
      setShowAddMember(false);
    },
    onError: (err: any) => toast.error(err.response?.data?.detail || 'فشل'),
  });

  const modifyMutation = useMutation({
    mutationFn: (data: any) => channelsAPI.modifyPermission(id!, data),
    onSuccess: () => {
      toast.success('تم تعديل الصلاحية');
      queryClient.invalidateQueries({ queryKey: ['channel-members', id] });
      setShowActions(null);
    },
  });

  const revokeMutation = useMutation({
    mutationFn: (data: any) => channelsAPI.revokePermission(id!, data),
    onSuccess: () => {
      toast.success('تم سحب الصلاحية');
      queryClient.invalidateQueries({ queryKey: ['channel-members', id] });
      setShowActions(null);
    },
  });

  const removeMutation = useMutation({
    mutationFn: (data: any) => channelsAPI.removeMember(id!, data),
    onSuccess: () => {
      toast.success('تم إلغاء العضوية');
      queryClient.invalidateQueries({ queryKey: ['channel-members', id] });
      setShowActions(null);
    },
  });

  // File upload
  const { data: filesData } = useQuery({
    queryKey: ['channel-files', id],
    queryFn: () => patientsAPI.filesByChannel(id!),
    enabled: !!id,
  });

  const uploadFileMutation = useMutation({
    mutationFn: (data: FormData) => patientsAPI.uploadFile(data),
    onSuccess: () => {
      toast.success('تم رفع الملف بنجاح');
      queryClient.invalidateQueries({ queryKey: ['channel-files', id] });
    },
    onError: (err: any) => {
      toast.error(err.response?.data?.detail || err.response?.data?.file?.[0] || 'فشل رفع الملف');
    },
  });

  const fileInputRef = useRef<HTMLInputElement>(null);
  const files = filesData?.data || [];

  if (isLoading) {
    return <div className="text-center py-8 text-gray-500">جاري التحميل...</div>;
  }

  const channel = channelData?.data;
  const members = membersData?.data || [];
  const records = recordsData?.data?.results || recordsData?.data || [];
  const allUsers = usersData?.data?.results || usersData?.data || [];
  const nonMembers = allUsers.filter((u: any) =>
    !members.find((m: any) => m.user.id === u.id)
  );

  const isOwner = channel?.current_user_role === 'OWNER' ||
    user?.role === 'SUPER_ADMIN' || user?.role === 'HOSPITAL_ADMIN';

  return (
    <div className="space-y-6">
      <button
        onClick={() => navigate('/channels')}
        className="flex items-center gap-2 text-gray-600 hover:text-primary-600"
      >
        <ArrowRight className="w-4 h-4" />
        العودة للقنوات
      </button>

      <div className="card">
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">{channel?.name}</h1>
            <p className="text-gray-600 mt-1">{channel?.description}</p>
            <div className="flex flex-wrap gap-2 mt-3">
              <span className="badge badge-info">{channel?.channel_type_display}</span>
              <span className={`badge ${
                channel?.status === 'ACTIVE' ? 'badge-success' : 'badge-warning'
              }`}>
                {channel?.status_display}
              </span>
              <span className={`badge ${
                channel?.priority === 'URGENT' ? 'badge-danger' : 'badge-warning'
              }`}>
                أولوية: {channel?.priority}
              </span>
              <span className="badge badge-success">
                دورك: {roleLabels[channel?.current_user_role] || 'لا يوجد'}
              </span>
            </div>
          </div>
          <div className="flex flex-col gap-2 flex-shrink-0">
            <button
              onClick={handleDownloadReport}
              disabled={downloadingReport}
              className="btn-primary text-sm flex items-center gap-2"
            >
              <FileDown className="w-4 h-4" />
              {downloadingReport ? 'جاري التوليد...' : 'تقرير PDF'}
            </button>
            {channel?.patient && (
              <button
                onClick={() => navigate(`/patients/${typeof channel.patient === 'string' ? channel.patient : channel.patient?.id || channel.patient}`)}
                className="btn-secondary text-sm flex items-center gap-2"
              >
                <Activity className="w-4 h-4" />
                ملف المريض
              </button>
            )}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          <div className="card">
            <div className="flex items-center justify-between mb-4">
              <h2 className="font-bold text-gray-900 flex items-center gap-2">
                <Activity className="w-5 h-5 text-primary-600" />
                السجلات الطبية
              </h2>
              <button className="btn-secondary text-sm flex items-center gap-2">
                <Plus className="w-4 h-4" />
                إضافة سجل
              </button>
            </div>
            <div className="space-y-3">
              {records.length === 0 ? (
                <p className="text-center text-gray-500 py-4">لا توجد سجلات بعد</p>
              ) : (
                records.map((record: any) => (
                  <div key={record.id} className="p-4 border border-gray-200 rounded-lg hover:bg-gray-50">
                    <div className="flex items-start justify-between">
                      <div>
                        <div className="flex items-center gap-2">
                          <h3 className="font-medium text-gray-900">{record.title}</h3>
                          <span className="badge badge-info">
                            {record.record_type_display}
                          </span>
                          {record.is_critical && (
                            <span className="badge badge-danger">حرج</span>
                          )}
                        </div>
                        <p className="text-sm text-gray-600 mt-1 line-clamp-2">
                          {record.content}
                        </p>
                        <p className="text-xs text-gray-400 mt-2">
                          بواسطة {record.created_by_name} •{' '}
                          {new Date(record.created_at).toLocaleString('ar-SA')}
                        </p>
                      </div>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* In-channel secure chat */}
          <ChannelChat channelId={id!} />
        </div>

        <div className="space-y-6">
          <div className="card">
            <div className="flex items-center justify-between mb-4">
              <h2 className="font-bold text-gray-900 flex items-center gap-2">
                <Users className="w-5 h-5 text-primary-600" />
                الأعضاء ({members.length})
              </h2>
              {isOwner && (
                <button
                  onClick={() => setShowAddMember(true)}
                  className="btn-secondary text-sm flex items-center gap-2"
                >
                  <UserPlus className="w-4 h-4" />
                  إضافة
                </button>
              )}
            </div>
            <div className="space-y-2">
              {members.map((member: any) => (
                <div
                  key={member.id}
                  className="flex items-center justify-between p-3 border border-gray-200 rounded-lg hover:bg-gray-50"
                >
                  <div className="flex items-center gap-3">
                    <div className="w-9 h-9 bg-primary-100 rounded-full flex items-center justify-center">
                      <span className="text-primary-700 text-sm font-medium">
                        {member.user.full_name.charAt(0)}
                      </span>
                    </div>
                    <div>
                      <p className="text-sm font-medium text-gray-900">
                        {member.user.full_name}
                      </p>
                      <p className="text-xs text-gray-500">{member.user.email}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className={`badge ${roleColors[member.role]}`}>
                      {roleLabels[member.role]}
                    </span>
                    {isOwner && member.role !== 'OWNER' && (
                      <div className="relative">
                        <button
                          onClick={() => setShowActions(
                            showActions === member.id ? null : member.id
                          )}
                          className="p-1 hover:bg-gray-200 rounded"
                        >
                          <MoreVertical className="w-4 h-4" />
                        </button>
                        {showActions === member.id && (
                          <div className="absolute left-0 top-full mt-1 w-48 bg-white border border-gray-200 rounded-lg shadow-lg z-10">
                            <button
                              onClick={() => {
                                const newRole = prompt('الدور الجديد (MODERATOR/EDITOR/CONTRIBUTOR/VIEWER):');
                                if (newRole) {
                                  modifyMutation.mutate({
                                    membership_id: member.id,
                                    role: newRole.toUpperCase(),
                                  });
                                }
                              }}
                              className="w-full flex items-center gap-2 px-3 py-2 text-sm hover:bg-gray-50 text-right"
                            >
                              <Edit2 className="w-4 h-4" />
                              تعديل الصلاحية
                            </button>
                            <button
                              onClick={() => revokeMutation.mutate({ membership_id: member.id })}
                              className="w-full flex items-center gap-2 px-3 py-2 text-sm hover:bg-gray-50 text-right text-orange-600"
                            >
                              <Ban className="w-4 h-4" />
                              سحب الصلاحية
                            </button>
                            <button
                              onClick={() => {
                                if (confirm('هل أنت متأكد من إزالة هذا العضو؟')) {
                                  removeMutation.mutate({ membership_id: member.id });
                                }
                              }}
                              className="w-full flex items-center gap-2 px-3 py-2 text-sm hover:bg-gray-50 text-right text-red-600"
                            >
                              <Trash2 className="w-4 h-4" />
                              إلغاء العضوية
                            </button>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="card">
            <h2 className="font-bold text-gray-900 dark:text-white flex items-center gap-2 mb-4">
              <Shield className="w-5 h-5 text-medical-600" />
              معلومات الأمان
            </h2>
            <div className="space-y-2 text-sm">
              <div className="flex items-center justify-between">
                <span className="text-gray-600 dark:text-gray-400">DV (مجموعة واحدة):</span>
                <span className="font-medium text-green-600 dark:text-green-400">✓ مفعلة</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-gray-600 dark:text-gray-400">تشفير المحتوى:</span>
                <span className="font-medium text-green-600 dark:text-green-400">✓ AES-256</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-gray-600 dark:text-gray-400">سجل التدقيق:</span>
                <span className="font-medium text-green-600 dark:text-green-400">✓ نشط</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-gray-600 dark:text-gray-400">WAF Protection:</span>
                <span className="font-medium text-green-600 dark:text-green-400">✓ نشط</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-gray-600 dark:text-gray-400">أنشئ في:</span>
                <span className="font-medium text-gray-900 dark:text-white">
                  {new Date(channel?.created_at).toLocaleDateString('ar-SA')}
                </span>
              </div>
            </div>
          </div>

          {/* Medical Files */}
          <div className="card">
            <div className="flex items-center justify-between mb-4">
              <h2 className="font-bold text-gray-900 dark:text-white flex items-center gap-2">
                <Paperclip className="w-5 h-5 text-primary-600" />
                الملفات الطبية ({files.length})
              </h2>
              {isOwner && (
                <button
                  onClick={() => fileInputRef.current?.click()}
                  className="btn-secondary text-sm flex items-center gap-2"
                >
                  <Upload className="w-4 h-4" />
                  رفع ملف
                </button>
              )}
              <input
                ref={fileInputRef}
                type="file"
                className="hidden"
                accept=".jpg,.jpeg,.png,.gif,.bmp,.pdf,.doc,.docx,.dcm"
                onChange={async (e) => {
                  const file = e.target.files?.[0];
                  if (!file) return;
                  const formData = new FormData();
                  formData.append('channel', id!);
                  formData.append('file', file);
                  formData.append('file_type', 'DOCUMENT');
                  formData.append('original_filename', file.name);
                  uploadFileMutation.mutate(formData);
                  e.target.value = '';
                }}
              />
            </div>
            <div className="space-y-2 max-h-64 overflow-y-auto">
              {files.length === 0 ? (
                <p className="text-center text-gray-500 dark:text-gray-400 py-4 text-sm">
                  لا توجد ملفات
                </p>
              ) : (
                files.map((file: any) => (
                  <div
                    key={file.id}
                    className="flex items-center justify-between p-3 border border-gray-200 dark:border-gray-700 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700/30"
                  >
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 bg-primary-100 dark:bg-primary-900/30 rounded-lg flex items-center justify-center">
                        <FileText className="w-4 h-4 text-primary-600 dark:text-primary-400" />
                      </div>
                      <div>
                        <p className="text-sm font-medium text-gray-900 dark:text-white">
                          {file.original_filename}
                        </p>
                        <p className="text-xs text-gray-500 dark:text-gray-400">
                          {file.file_type_display} • {file.file_size_display} • {file.uploaded_by_name}
                        </p>
                      </div>
                    </div>
                    <button
                      onClick={() => {
                        patientsAPI.downloadFile(file.id).then((response) => {
                          const url = window.URL.createObjectURL(new Blob([response.data]));
                          const link = document.createElement('a');
                          link.href = url;
                          link.setAttribute('download', file.original_filename);
                          document.body.appendChild(link);
                          link.click();
                          link.remove();
                        });
                      }}
                      className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg cursor-pointer"
                    >
                      <Download className="w-4 h-4 text-gray-600 dark:text-gray-300" />
                    </button>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      </div>

      {showAddMember && (
        <AddMemberModal
          users={nonMembers}
          onSubmit={(data: any) => grantMutation.mutate(data)}
          onClose={() => setShowAddMember(false)}
          loading={grantMutation.isPending}
        />
      )}
    </div>
  );
}

function AddMemberModal({ users, onSubmit, onClose, loading }: any) {
  const [formData, setFormData] = useState({
    user_email: '',
    role: 'VIEWER',
    notes: '',
  });

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-md p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-bold">إضافة عضو للقناة</h2>
          <button onClick={onClose} className="p-1 hover:bg-gray-100 rounded">
            <X className="w-5 h-5" />
          </button>
        </div>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            onSubmit(formData);
          }}
          className="space-y-4"
        >
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              المستخدم
            </label>
            <select
              value={formData.user_email}
              onChange={(e) => setFormData({ ...formData, user_email: e.target.value })}
              required
              className="input-field"
            >
              <option value="">اختر مستخدم</option>
              {users.map((u: any) => (
                <option key={u.id} value={u.email}>
                  {u.full_name} ({u.email})
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              الدور (DV: دور واحد فقط)
            </label>
            <select
              value={formData.role}
              onChange={(e) => setFormData({ ...formData, role: e.target.value })}
              className="input-field"
            >
              <option value="MODERATOR">مشرف</option>
              <option value="EDITOR">محرر</option>
              <option value="CONTRIBUTOR">مساهم</option>
              <option value="VIEWER">مشاهد</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              ملاحظات (اختياري)
            </label>
            <textarea
              value={formData.notes}
              onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
              rows={2}
              className="input-field"
            />
          </div>
          <div className="flex gap-2 pt-2">
            <button type="submit" disabled={loading} className="btn-primary flex-1">
              {loading ? 'جاري الإضافة...' : 'إضافة العضو'}
            </button>
            <button type="button" onClick={onClose} className="btn-secondary flex-1">
              إلغاء
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
