import { motion } from 'framer-motion';
import FloatingParticles from './FloatingParticles';

/**
 * AnimatedBackground — layered living background:
 *  1. Base mesh gradient (breathing hues)
 *  2. Morphing gradient blobs (organic border-radius animation)
 *  3. Subtle grid with radial mask
 *  4. Floating medical icon particles
 *
 * `variant="login"` → richer/darker cinematic look (behind the auth screens).
 * `variant="app"`   → subtle ambience for the authenticated app shell.
 */
export default function AnimatedBackground({
  variant = 'app',
  particles = 14,
}: {
  variant?: 'login' | 'app';
  particles?: number;
}) {
  const rich = variant === 'login';

  return (
    <div className="fixed inset-0 -z-10 overflow-hidden pointer-events-none" aria-hidden="true">
      {/* 1 — base gradient */}
      <div
        className={`absolute inset-0 ${
          rich
            ? 'bg-gradient-to-br from-navy-900 via-primary-950 to-medical-900 dark:from-gray-950 dark:via-navy-900 dark:to-primary-950'
            : 'bg-mesh-medical bg-[length:200%_200%] animate-gradient bg-gradient-to-br from-white via-primary-50/40 to-medical-50/60 dark:from-gray-950 dark:via-gray-950 dark:to-navy-900'
        }`}
      />

      {/* 2 — morphing blobs */}
      <motion.div
        className={`absolute blur-3xl animate-blob ${
          rich
            ? '-top-32 -right-32 w-[34rem] h-[34rem] bg-primary-600/30'
            : '-top-40 -left-32 w-[30rem] h-[30rem] bg-primary-400/20 dark:bg-primary-600/15'
        }`}
        animate={{ x: [0, 40, -20, 0], y: [0, -30, 20, 0] }}
        transition={{ duration: 18, repeat: Infinity, ease: 'easeInOut' }}
      />
      <motion.div
        className={`absolute blur-3xl animate-blob-alt ${
          rich
            ? 'top-1/3 -left-40 w-[38rem] h-[38rem] bg-medical-500/25'
            : '-bottom-40 -right-32 w-[32rem] h-[32rem] bg-medical-400/20 dark:bg-medical-600/15'
        }`}
        animate={{ x: [0, -50, 30, 0], y: [0, 40, -20, 0] }}
        transition={{ duration: 22, repeat: Infinity, ease: 'easeInOut' }}
      />
      {rich && (
        <motion.div
          className="absolute bottom-0 right-1/4 w-[26rem] h-[26rem] bg-indigo-500/20 blur-3xl animate-blob"
          animate={{ x: [0, 30, -40, 0], y: [0, -20, 30, 0] }}
          transition={{ duration: 20, repeat: Infinity, ease: 'easeInOut' }}
        />
      )}

      {/* 3 — grid with radial mask */}
      <div
        className={`absolute inset-0 ${rich ? 'bg-grid-dark' : 'bg-grid dark:bg-grid-dark'}`}
        style={{
          maskImage: 'radial-gradient(ellipse 90% 70% at 50% 40%, black 30%, transparent 75%)',
          WebkitMaskImage: 'radial-gradient(ellipse 90% 70% at 50% 40%, black 30%, transparent 75%)',
        }}
      />

      {/* 4 — floating medical particles */}
      <FloatingParticles count={particles} opacity={rich ? 0.35 : 0.3} />
    </div>
  );
}
