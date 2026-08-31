import { motion } from 'framer-motion';
import type { ReactNode } from 'react';

const easing = [0.22, 1, 0.36, 1] as const;

/** Wraps page content with a smooth enter/exit transition (used inside Layout's AnimatePresence). */
export default function PageTransition({ children }: { children: ReactNode }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 18, scale: 0.995 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, y: -14, scale: 0.995 }}
      transition={{ duration: 0.38, ease: easing }}
    >
      {children}
    </motion.div>
  );
}

/** Stagger container — children with `variants={staggerItem}` fade in one after another. */
export function StaggerContainer({
  children,
  className,
  delay = 0,
}: {
  children: ReactNode;
  className?: string;
  delay?: number;
}) {
  return (
    <motion.div
      className={className}
      initial="hidden"
      animate="visible"
      variants={{
        hidden: {},
        visible: { transition: { staggerChildren: 0.08, delayChildren: delay } },
      }}
    >
      {children}
    </motion.div>
  );
}

/** Stagger child item — place inside a StaggerContainer. */
export function StaggerItem({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <motion.div
      className={className}
      variants={{
        hidden: { opacity: 0, y: 22, scale: 0.98 },
        visible: {
          opacity: 1,
          y: 0,
          scale: 1,
          transition: { duration: 0.5, ease: easing },
        },
      }}
    >
      {children}
    </motion.div>
  );
}
