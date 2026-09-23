import React, { useEffect, useState, useMemo } from 'react';
import { useAuthStore } from '../../store/authStore';
import { useSecurityPreferencesStore } from '../../store/securityPreferencesStore';

/**
 * Dynamic Anti-Leak Watermark for the SecureMed Web Application.
 *
 * Renders a repeating, semi-transparent, rotated grid across the screen displaying:
 * `UserName (UserID) • YYYY-MM-DD HH:mm`
 *
 * Aligns with `DynamicWatermark.kt` on Android to provide forensic attribution
 * against visual eavesdropping or unauthorized smartphone photography of EHR screens.
 *
 * Completely non-interactive (`pointer-events-none`) so it never blocks clicks or touches.
 */
export default function DynamicWatermark() {
  const user = useAuthStore((state) => state.user);
  const { isWatermarkEnabled, watermarkOpacity } = useSecurityPreferencesStore();

  const [timestamp, setTimestamp] = useState(() => {
    const d = new Date();
    return d.toISOString().slice(0, 16).replace('T', ' ');
  });

  // Update clock every 30 seconds, mirroring Android's LaunchedEffect loop
  useEffect(() => {
    if (!isWatermarkEnabled || !user) return;

    const interval = setInterval(() => {
      const d = new Date();
      setTimestamp(d.toISOString().slice(0, 16).replace('T', ' '));
    }, 30_000);

    return () => clearInterval(interval);
  }, [isWatermarkEnabled, user]);

  const watermarkText = useMemo(() => {
    if (!user) return '';
    const name = user.full_name?.trim() || user.email || 'SecureMed User';
    const shortId = user.id ? user.id.slice(0, 8) : '';
    return shortId ? `${name} (${shortId}) • ${timestamp}` : `${name} • ${timestamp}`;
  }, [user, timestamp]);

  if (!isWatermarkEnabled || !user) {
    return null;
  }

  // Create an SVG pattern for crisp, high-performance rendering without DOM bloat
  const encodedText = encodeURIComponent(watermarkText);

  return (
    <div
      aria-hidden="true"
      className="fixed inset-0 pointer-events-none z-[45] select-none overflow-hidden"
      style={{
        opacity: watermarkOpacity,
        backgroundImage: `url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='380' height='200'><text x='20' y='120' transform='rotate(-25 190 100)' fill='%2364748b' font-family='sans-serif' font-weight='600' font-size='13' letter-spacing='0.5'>${encodedText}</text></svg>")`,
        backgroundRepeat: 'repeat',
      }}
    />
  );
}
