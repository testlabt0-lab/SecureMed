from apps.patients.models import Patient
from apps.accounts.models import User
from apps.appointments.models import Appointment
from apps.pharmacy.models import Prescription
from apps.security.models import SecurityEvent

def dashboard_callback(request, context):
    context.update(
        {
            "kpi": [
                {
                    "title": "إجمالي المرضى",
                    "metric": str(Patient.objects.count()),
                    "footer": "في جميع الأقسام",
                },
                {
                    "title": "مستخدمي النظام",
                    "metric": str(User.objects.count()),
                    "footer": "أطباء وإداريين",
                },
                {
                    "title": "المواعيد المجدولة",
                    "metric": str(Appointment.objects.filter(status='SCHEDULED').count()),
                    "footer": "بانتظار المراجعة",
                },
                {
                    "title": "الوصفات الطبية",
                    "metric": str(Prescription.objects.count()),
                    "footer": "في الصيدلية",
                },
                {
                    "title": "أحداث الأمان",
                    "metric": str(SecurityEvent.objects.count()),
                    "footer": "سجلات التدقيق الأمني",
                },
            ]
        }
    )
    return context
