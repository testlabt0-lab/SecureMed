import React, { Component, ErrorInfo, ReactNode } from 'react';
import { AlertTriangle, RefreshCcw } from 'lucide-react';

interface Props {
  children?: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('Uncaught error:', error, errorInfo);
  }

  public render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <div className="flex h-full min-h-[400px] w-full flex-col items-center justify-center rounded-xl border border-red-100 bg-red-50 p-8 text-center dark:border-red-900/30 dark:bg-red-900/10">
          <div className="mb-4 rounded-full bg-red-100 p-3 text-red-600 dark:bg-red-900/50 dark:text-red-400">
            <AlertTriangle className="h-8 w-8" />
          </div>
          <h2 className="mb-2 text-xl font-bold text-gray-900 dark:text-white">
            عذراً، حدث خطأ غير متوقع
          </h2>
          <p className="mb-6 max-w-md text-sm text-gray-500 dark:text-gray-400">
            {this.state.error?.message || 'يبدو أن هناك مشكلة في تحميل هذا المكون. يرجى المحاولة مرة أخرى.'}
          </p>
          <button
            onClick={() => {
              this.setState({ hasError: false, error: null });
              window.location.reload();
            }}
            className="flex items-center gap-2 rounded-lg bg-red-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-red-700"
          >
            <RefreshCcw className="h-4 w-4" />
            إعادة تحميل الصفحة
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;
