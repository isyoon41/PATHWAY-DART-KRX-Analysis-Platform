'use client';

import React from 'react';
import { ExternalLink, Database } from 'lucide-react';

interface SourceBadgeProps {
  provider: string;
  url: string;
  retrievedAt?: string;
  compact?: boolean;
}

/**
 * 데이터 출처를 표시하는 배지 컴포넌트
 * 모든 데이터에 출처와 근거를 명시하여 신뢰도 확보
 */
export default function SourceBadge({
  provider,
  url,
  retrievedAt,
  compact = false
}: SourceBadgeProps) {
  if (compact) {
    return (
      <a
        href={url}
        target="_blank"
        rel="noopener noreferrer"
        className="inline-flex items-center gap-1 text-xs text-blue-600 hover:text-blue-800 hover:underline"
        title={`출처: ${provider}${retrievedAt ? ` (${new Date(retrievedAt).toLocaleString('ko-KR')})` : ''}`}
      >
        <Database className="w-3 h-3" />
        <span>{provider}</span>
        <ExternalLink className="w-3 h-3" />
      </a>
    );
  }

  return (
    <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 mt-2">
      <div className="flex items-start gap-2">
        <Database className="w-4 h-4 text-blue-600 mt-0.5 flex-shrink-0" />
        <div className="flex-1 min-w-0">
          <div className="text-xs font-semibold text-blue-900 mb-1">
            📊 데이터 출처
          </div>
          <div className="text-xs text-blue-700">
            <span className="font-medium">{provider}</span>
          </div>
          {retrievedAt && (
            <div className="text-xs text-blue-600 mt-1">
              조회 시각: {new Date(retrievedAt).toLocaleString('ko-KR')}
            </div>
          )}
          <a
            href={url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1 text-xs text-blue-600 hover:text-blue-800 hover:underline mt-1"
          >
            <span>원본 데이터 확인</span>
            <ExternalLink className="w-3 h-3" />
          </a>
        </div>
      </div>
    </div>
  );
}
