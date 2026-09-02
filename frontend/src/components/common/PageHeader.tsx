import React from 'react';

interface PageHeaderProps {
  title: string;
  description?: string;
  subtitle?: string;
  icon?: React.ReactNode;
  children?: React.ReactNode;
}

export default function PageHeader({ title, description, subtitle, icon, children }: PageHeaderProps) {
  const text = description || subtitle;
  return (
    <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
      <div className="flex items-center gap-3">
        {icon && <div className="p-2.5 bg-primary-50 dark:bg-primary-900/20 rounded-2xl">{icon}</div>}
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">{title}</h1>
          {text && <p className="text-sm text-gray-500 dark:text-gray-400 mt-0.5">{text}</p>}
        </div>
      </div>
      {children && <div className="flex items-center gap-2">{children}</div>}
    </div>
  );
}
