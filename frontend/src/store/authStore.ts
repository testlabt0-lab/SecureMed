import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export interface User {
  id: string;
  email: string;
  full_name: string;
  role: string;
  phone?: string;
  license_number?: string;
  department?: string;
  specialization?: string;
  is_biometric_enabled: boolean;
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
        localStorage.removeItem('auth-storage');
      },
      updateUser: (updatedUser) =>
        set((state) => ({
          user: state.user ? { ...state.user, ...updatedUser } : null,
        })),
    }),
    {
      name: 'auth-storage',
    }
  )
);
