import React from 'react';
import { ShieldAlert } from 'lucide-react';

export default function Blocked() {
  return (
    <div className="flex h-screen w-full items-center justify-center bg-gray-50 dark:bg-gray-900 px-4">
      <div className="max-w-md w-full text-center space-y-6 bg-white dark:bg-gray-800 p-8 rounded-2xl shadow-xl border border-red-100 dark:border-red-900">
        <div className="mx-auto flex h-24 w-24 items-center justify-center rounded-full bg-red-100 dark:bg-red-900/30">
          <ShieldAlert className="h-12 w-12 text-red-600 dark:text-red-500" />
        </div>
        <div className="space-y-3">
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white">تم حظر الوصول</h1>
          <p className="text-gray-600 dark:text-gray-300">
            عذراً، لقد تم حظر هذا الجهاز أو عنوان الشبكة الخاص بك من الوصول إلى النظام لدواعي أمنية.
          </p>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            إذا كنت تعتقد أن هذا خطأ، يرجى التواصل مع مسؤول النظام.
          </p>
        </div>
      </div>
    </div>
  );
}
