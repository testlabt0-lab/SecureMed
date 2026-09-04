import React from 'react';

interface CardProps {
  children: React.ReactNode;
  className?: string;
  title?: string;
  subtitle?: string;
  action?: React.ReactNode;
  onClick?: () => void;
}

export default function Card({ children, className = '', title, subtitle, action, onClick }: CardProps) {
  return (
    <div
      onClick={onClick}
      className={`bg-white dark:bg-gray-800 rounded-2xl p-6 border border-gray-100 dark:border-gray-700/60 shadow-sm ${className}`}
    >
      {(title || action) && (
        <div className="flex items-center justify-between mb-4">
          <div>
            {title && <h3 className="font-semibold text-gray-900 dark:text-white">{title}</h3>}
            {subtitle && <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">{subtitle}</p>}
          </div>
          {action && <div>{action}</div>}
        </div>
      )}
      {children}
    </div>
  );
}
