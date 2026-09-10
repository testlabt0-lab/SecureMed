import { create } from 'zustand';
import { createJSONStorage, persist } from 'zustand/middleware';
import type { Role } from '../constants/roles';

export interface User {
  id: string;
  email: string;
  full_name: string;
  /**
   * One of the eleven codes in User.Role (backend/apps/accounts/models.py).
   * Typed rather than `string` so a comparison against a code that does not
   * exist — a typo, or a role removed from the backend — fails at compile time
   * instead of quietly evaluating to false and hiding a screen from everyone.
   */
  role: Role;
  phone?: string;
  license_number?: string;
  department?: string;
  specialization?: string;
  is_biometric_enabled: boolean;
  permissions?: string[];
  groups?: string[];
}

/**
 * Token storage model:
 * - `accessToken` lives in memory ONLY — never written to sessionStorage, so an
 *   XSS payload cannot read a long-lived credential and the persisted state
 *   carries nothing usable.
 * - The refresh token is an HttpOnly cookie the server sets on login/refresh
 *   (accounts.views.set_refresh_cookie) and reads back on /auth/refresh/ and
 *   /auth/logout/. The client never sees it.
 */
interface AuthState {
  user: User | null;
  accessToken: string | null;
  setAuth: (user: User, tokens: { access: string; refresh?: string }) => void;
  setAccessToken: (token: string) => void;
  logout: () => void;
  updateUser: (user: Partial<User>) => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      accessToken: null,
      setAuth: (user, tokens) => set({ user, accessToken: tokens.access }),
      setAccessToken: (token) => set({ accessToken: token }),
      logout: () => {
        set({ user: null, accessToken: null });
        sessionStorage.removeItem('auth-storage');
      },
      updateUser: (updatedUser) =>
        set((state) => ({
          user: state.user ? { ...state.user, ...updatedUser } : null,
        })),
    }),
    {
      name: 'auth-storage',
      storage: createJSONStorage(() => sessionStorage),
      // Persist the user profile only. The access token must not survive a
      // reload in web storage; it is restored via the HttpOnly refresh cookie.
      partialize: (state) => ({ user: state.user }) as unknown as AuthState,
    }
  )
);
