'use client';

import React, { Component, type ReactNode } from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';

interface Props {
  children: ReactNode;
  /** 에러 발생 시 대체 UI 텍스트 */
  fallbackMessage?: string;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

/**
 * 클라이언트 사이드 에러 바운더리
 *
 * 하위 컴포넌트에서 렌더링 중 발생하는 예외를 잡아
 * 앱 전체 크래시를 방지하고, 사용자에게 복구 옵션을 제공합니다.
 */
export default class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    // 프로덕션에서는 Sentry 등 에러 리포팅 서비스로 전송 가능
    if (process.env.NODE_ENV === 'development') {
      console.error('[ErrorBoundary]', error, info.componentStack);
    }
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null });
  };

  render() {
    if (this.state.hasError) {
      return (
        <div className="flex flex-col items-center justify-center p-8 rounded-lg border border-red-200 bg-red-50 text-center space-y-3">
          <AlertTriangle className="w-8 h-8 text-red-400" />
          <p className="text-[14px] font-semibold text-red-700">
            {this.props.fallbackMessage || '화면 렌더링 중 오류가 발생했습니다.'}
          </p>
          {process.env.NODE_ENV === 'development' && this.state.error && (
            <pre className="text-[11px] text-red-500 bg-red-100 p-2 rounded max-w-full overflow-auto">
              {this.state.error.message}
            </pre>
          )}
          <button
            onClick={this.handleReset}
            className="flex items-center gap-1.5 px-4 py-2 text-[12px] font-bold text-white bg-red-500 hover:bg-red-600 rounded transition-colors"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            다시 시도
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}
