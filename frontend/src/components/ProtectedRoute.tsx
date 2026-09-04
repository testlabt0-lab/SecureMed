import { Navigate, useLocation } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';
import { ReactNode } from 'react';

interface ProtectedRouteProps {
  children: ReactNode;
  requiredRole?: string[];
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

  if (requiredPermission && user.permissions && !user.permissions.includes(requiredPermission)) {
    // Also let super admins through
    if (!['SUPER_ADMIN', 'HOSPITAL_ADMIN'].includes(user.role)) {
        return <Navigate to="/dashboard" replace />;
    }
  }

  return <>{children}</>;
}
