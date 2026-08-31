import { useMemo } from 'react';
import { motion } from 'framer-motion';
import { HeartPulse, Pill, Stethoscope, Activity, Cross, Syringe, Microscope, Heart } from 'lucide-react';

const ICONS = [HeartPulse, Pill, Stethoscope, Activity, Cross, Syringe, Microscope, Heart];

/**
 * FloatingParticles — dreamy floating medical icons drifting upward.
 * Positions/rotations are generated once (useMemo) so renders stay stable.
 */
export default function FloatingParticles({
  count = 14,
  className = '',
  opacity = 0.5,
}: {
  count?: number;
  className?: string;
  opacity?: number;
}) {
  const particles = useMemo(
    () =>
      Array.from({ length: count }, (_, i) => {
        const Icon = ICONS[i % ICONS.length];
        return {
          id: i,
          Icon,
          left: (i * 100) / count + (i % 3) * 4,
          size: 18 + ((i * 7) % 22),
          duration: 14 + ((i * 5) % 16),
          delay: -((i * 3.7) % 18),
          drift: ((i % 5) - 2) * 34,
          rotate: ((i % 2) === 0 ? 1 : -1) * (8 + (i % 5) * 4),
        };
      }),
    [count]
  );

  return (
    <div className={`pointer-events-none absolute inset-0 overflow-hidden ${className}`} aria-hidden="true">
      {particles.map(({ id, Icon, left, size, duration, delay, drift, rotate }) => (
        <motion.div
          key={id}
          className="absolute text-primary-500/60 dark:text-primary-300/50"
          style={{ left: `${left}%`, top: '108%' }}
          initial={{ y: 0, opacity: 0, rotate: 0 }}
          animate={{
            y: '-130vh',
            x: [0, drift, -drift / 2, 0],
            opacity: [0, opacity, opacity, 0],
            rotate: [0, rotate, -rotate, 0],
          }}
          transition={{
            duration,
            delay,
            repeat: Infinity,
            ease: 'linear',
            x: { duration: duration / 3, repeat: Infinity, ease: 'easeInOut' },
            rotate: { duration: duration / 2, repeat: Infinity, ease: 'easeInOut' },
          }}
        >
          <Icon size={size} strokeWidth={1.6} />
        </motion.div>
      ))}
    </div>
  );
}
