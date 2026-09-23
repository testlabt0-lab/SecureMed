import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export type LockReason = 'idle' | 'tab_switch' | 'manual' | null;

interface SecurityPreferencesState {
  // Preferences
  isWatermarkEnabled: boolean;
  watermarkOpacity: number;
  isTabBlurEnabled: boolean;
  isIdleLockEnabled: boolean;
  idleTimeoutMinutes: number;

  // Runtime Lock State
  isLocked: boolean;
  lockReason: LockReason;
  lastActiveTimestamp: number;

  // Actions
  setWatermarkEnabled: (enabled: boolean) => void;
  setWatermarkOpacity: (opacity: number) => void;
  setTabBlurEnabled: (enabled: boolean) => void;
  setIdleLockEnabled: (enabled: boolean) => void;
  setIdleTimeoutMinutes: (minutes: number) => void;
  lock: (reason: LockReason) => void;
  unlock: () => void;
  recordActivity: () => void;
}

export const useSecurityPreferencesStore = create<SecurityPreferencesState>()(
  persist(
    (set, get) => ({
      isWatermarkEnabled: true,
      watermarkOpacity: 0.07,
      isTabBlurEnabled: true,
      isIdleLockEnabled: true,
      idleTimeoutMinutes: 5,

      isLocked: false,
      lockReason: null,
      lastActiveTimestamp: Date.now(),

      setWatermarkEnabled: (enabled) => set({ isWatermarkEnabled: enabled }),
      setWatermarkOpacity: (opacity) => set({ watermarkOpacity: opacity }),
      setTabBlurEnabled: (enabled) => set({ isTabBlurEnabled: enabled }),
      setIdleLockEnabled: (enabled) => set({ isIdleLockEnabled: enabled }),
      setIdleTimeoutMinutes: (minutes) => set({ idleTimeoutMinutes: Math.max(1, minutes) }),

      lock: (reason) => {
        if (!get().isLocked) {
          set({ isLocked: true, lockReason: reason });
        }
      },

      unlock: () => {
        set({ isLocked: false, lockReason: null, lastActiveTimestamp: Date.now() });
      },

      recordActivity: () => {
        if (!get().isLocked) {
          set({ lastActiveTimestamp: Date.now() });
        }
      },
    }),
    {
      name: 'securemed-security-preferences',
      partialize: (state) => ({
        isWatermarkEnabled: state.isWatermarkEnabled,
        watermarkOpacity: state.watermarkOpacity,
        isTabBlurEnabled: state.isTabBlurEnabled,
        isIdleLockEnabled: state.isIdleLockEnabled,
        idleTimeoutMinutes: state.idleTimeoutMinutes,
      }),
    }
  )
);
