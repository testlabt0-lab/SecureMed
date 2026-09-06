import React from 'react';
import { motion, type Variants } from 'framer-motion';

// Typed as Variants so the easing strings are checked against framer-motion's
// Easing union: an untyped literal widens `ease` to `string`, which the library
// rejects and `tsc` reported as a build failure.
const pageVariants: Variants = {
  initial: { opacity: 0, y: 20 },
  animate: { opacity: 1, y: 0, transition: { duration: 0.4, ease: 'easeOut' } },
  exit: { opacity: 0, y: -20, transition: { duration: 0.3, ease: 'easeIn' } },
};

export function AnimatedPage({ children, className = '' }: { children: React.ReactNode; className?: string }) {
  return (
    <motion.div
      initial="initial"
      animate="animate"
      exit="exit"
      variants={pageVariants}
      className={className}
    >
      {children}
    </motion.div>
  );
}
