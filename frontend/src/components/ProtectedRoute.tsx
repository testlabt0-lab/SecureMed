import { Navigate, useLocation } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';
import { ADMIN_ROLES, Role } from '../constants/roles';
import { ReactNode } from 'react';

/**
 * Route-level gate.
 *
 * This is a navigation aid, not a security boundary: the store it reads lives in
 * sessionStorage and the user can edit it. Every endpoint behind these screens is
 * enforced server-side by DRF permissions — this component only avoids showing a
 * screen that would come back empty or 403.
 */
interface ProtectedRouteProps {
  children: ReactNode;
  /**
   * Typed as Role[] rather than string[] so a typo ('SUPERADMIN') or a role that
   * no longer exists in the backend is a compile error instead of a guard that
   * silently rejects everyone. Pass one of the capability groups from
   * constants/roles.ts rather than an inline array.
   */
  requiredRole?: Role[];
  requiredPermission?: string;
}

export default function ProtectedRoute({ children, requiredRole, requiredPermission }: ProtectedRouteProps) {
  const { user, tokens } = useAuthStore();
  const location = useLocation();

  if (!user || !tokens) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  if (requiredRole && !requiredRole.includes(user.role)) {
    return <Navigate to="/dashboard" replace />;
  }

  // Permission gate. No route uses it yet; it is kept because the backend does
  // carry per-object permissions and a screen will eventually need it.
  //
  // Two things were wrong with it and both only bite the first caller, which is
  // why they are fixed now rather than left as a trap:
  //  - it read `user.permissions && ...`, so an account whose serializer did not
  //    include `permissions` (the field is optional) skipped the check entirely
  //    and was let through. A guard must fail closed, not open.
  //  - the admin bypass listed SUPER_ADMIN and HOSPITAL_ADMIN but not
  //    CENTER_ADMIN, which was added to the backend later. A centre admin would
  //    have been redirected off their own administrative screens. ADMIN_ROLES is
  //    the shared list, so the next role added to it applies here too.
  if (requiredPermission) {
    const granted = user.permissions?.includes(requiredPermission) ?? false;
    if (!granted && !ADMIN_ROLES.includes(user.role)) {
      return <Navigate to="/dashboard" replace />;
    }
  }

  return <>{children}</>;
}
