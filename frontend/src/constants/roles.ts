/**
 * Single source of truth for user roles on the client.
 *
 * Codes and Arabic labels are copied from User.Role in
 * backend/apps/accounts/models.py, so a label rendered locally always reads the
 * same as `role_display` coming back from the API.
 *
 * There were seven divergent copies of this map (Layout, Users, Profile,
 * GlobalSearch, AnalyticsDashboard, Analytics, ChannelChat). Only two listed all
 * eleven roles: the rest predated CENTER_ADMIN, ACCOUNTANT and RECEPTIONIST, so
 * those three rendered as an empty string on the user's own profile, in global
 * search results and in the analytics role breakdown. ChannelChat also carried
 * its own shorter wording, so one person showed as 'مراجع أمني' on one screen and
 * 'مراجع' on another.
 */
export const ROLES = [
  'SUPER_ADMIN',
  'HOSPITAL_ADMIN',
  'CENTER_ADMIN',
  'DOCTOR',
  'NURSE',
  'LAB_TECH',
  'PHARMACIST',
  'AUDITOR',
  'PATIENT',
  'ACCOUNTANT',
  'RECEPTIONIST',
] as const;

export type Role = (typeof ROLES)[number];

export const roleLabels: Record<Role, string> = {
  SUPER_ADMIN: 'مدير النظام',
  HOSPITAL_ADMIN: 'مدير المستشفى',
  CENTER_ADMIN: 'مدير مركز',
  DOCTOR: 'طبيب',
  NURSE: 'ممرض/ممرضة',
  LAB_TECH: 'فني مختبر',
  PHARMACIST: 'صيدلي',
  AUDITOR: 'مراجع أمني',
  PATIENT: 'مريض',
  ACCOUNTANT: 'محاسب',
  RECEPTIONIST: 'موظف استقبال',
};

/**
 * Label for a role code. Unknown codes fall back to the code itself rather than
 * an empty string: if the backend gains a role before the frontend does, the UI
 * should show something a support engineer can act on instead of a blank chip.
 */
export function roleLabel(role?: string | null): string {
  if (!role) return '';
  return roleLabels[role as Role] ?? role;
}

// ─── Route/feature groups ─────────────────────────────────────────────────────
// Named after the capability, not the screen, so a guard reads as a statement
// about who may do the thing. App.tsx used to inline these arrays at every
// <Route>, and Layout.tsx repeated them for the sidebar, which is how the two
// drifted: a role removed from a guard stayed visible in the menu and vice versa.

/** Anyone who administers an organisational scope. */
export const ADMIN_ROLES: Role[] = ['SUPER_ADMIN', 'HOSPITAL_ADMIN', 'CENTER_ADMIN'];

/** Clinical case work: channels, patients, records. */
export const CARE_TEAM_ROLES: Role[] = [...ADMIN_ROLES, 'DOCTOR', 'NURSE', 'RECEPTIONIST'];

/** Security posture and the audit trail. */
export const OVERSIGHT_ROLES: Role[] = [...ADMIN_ROLES, 'AUDITOR'];

/** Aggregate figures: analytics dashboards and report exports. */
export const REPORTING_ROLES: Role[] = [...ADMIN_ROLES, 'AUDITOR', 'DOCTOR', 'ACCOUNTANT'];

// ─── Report export tiers ──────────────────────────────────────────────────────
// These mirror REPORT_ROLES in backend/apps/reports/views.py, which is what
// actually enforces them. Keep the two in step: a role listed here but not there
// sees a download button that returns 403. The oversight tier (monthly summary,
// security report, audit trail) is OVERSIGHT_ROLES above.

/** Bulk clinical exports: patients, appointments, channels. */
export const CLINICAL_EXPORT_ROLES: Role[] = [...ADMIN_ROLES, 'DOCTOR'];

/**
 * Who may open /reports at all — the union of the two tiers above.
 *
 * Deliberately narrower than REPORTING_ROLES: an ACCOUNTANT belongs on
 * /analytics but matches no report in the catalogue (there is no financial
 * export), so guarding /reports with REPORTING_ROLES let them onto a page that
 * could only ever render an empty list.
 */
export const REPORT_EXPORT_ROLES: Role[] = [...ADMIN_ROLES, 'AUDITOR', 'DOCTOR'];

/** Medication stock and prescriptions. */
export const PHARMACY_ROLES: Role[] = [...ADMIN_ROLES, 'PHARMACIST', 'DOCTOR'];

/** Invoicing and insurance. */
export const BILLING_ROLES: Role[] = [...ADMIN_ROLES, 'AUDITOR', 'ACCOUNTANT', 'RECEPTIONIST'];

/**
 * Creating and settling invoices, as opposed to reading them.
 *
 * AUDITOR is deliberately absent: an auditor may open /billing to review, but
 * issuing or paying an invoice is not a review action. This is why the billing
 * page needs its own list rather than reusing the route guard.
 */
export const BILLING_WRITE_ROLES: Role[] = [...ADMIN_ROLES, 'ACCOUNTANT', 'RECEPTIONIST'];

/** Lab orders and results. */
export const LAB_ROLES: Role[] = [...ADMIN_ROLES, 'LAB_TECH', 'DOCTOR'];

/** Beds, rooms and admissions. */
export const WARD_ROLES: Role[] = [...ADMIN_ROLES, 'NURSE', 'DOCTOR'];

/** Video consultations. */
export const TELEMEDICINE_ROLES: Role[] = [...ADMIN_ROLES, 'DOCTOR'];

/** Whole-platform operations that are not delegated. */
export const PLATFORM_OWNER_ROLES: Role[] = ['SUPER_ADMIN'];
