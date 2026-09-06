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

interface AuthState {
  user: User | null;
  tokens: { access: string; refresh: string } | null;
  setAuth: (user: User, tokens: { access: string; refresh: string }) => void;
  logout: () => void;
  updateUser: (user: Partial<User>) => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      tokens: null,
      setAuth: (user, tokens) => set({ user, tokens }),
      logout: () => {
        set({ user: null, tokens: null });
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
    }
  )
);
