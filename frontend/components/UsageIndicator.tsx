'use client';

import { useEffect, useState, useCallback } from 'react';
import axios from 'axios';

interface ModelUsage {
  label: string;
  requests_used: number;
  requests_limit: number;
  requests_pct: number;
  input_tokens: number;
  output_tokens: number;
  total_tokens: number;
}

interface UsageData {
  date: string;
  reset_in_seconds: number;
  reset_time_kst?: string;
  reset_tz?: string;
  models: {
    flash: ModelUsage;
    flash_meta: ModelUsage;
  };
}

function formatTokens(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000)     return `${(n / 1_000).toFixed(1)}K`;
  return String(n);
}

function formatResetTime(seconds: number): string {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  if (h > 0) return `${h}시간 ${m}분 후 리셋`;
  if (m > 0) return `${m}분 후 리셋`;
  return '곧 리셋';
}

function ProgressBar({ pct, color }: { pct: number; color: string }) {
  const clamped = Math.min(100, Math.max(0, pct));
  const barColor =
    clamped >= 90 ? 'bg-red-500'
    : clamped >= 70 ? 'bg-amber-400'
    : color;
  return (
    <div className="w-full h-1.5 bg-gray-200 rounded-full overflow-hidden">
      <div
        className={`h-full rounded-full transition-all duration-700 ${barColor}`}
        style={{ width: `${clamped}%` }}
      />
    </div>
  );
}

function ModelRow({ model, colorClass }: { model: ModelUsage; colorClass: string }) {
  const pct = model.requests_pct;
  const remaining = model.requests_limit - model.requests_used;
  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between text-[11px]">
        <span className="font-medium text-gray-600 truncate max-w-[120px]" title={model.label}>
          {model.label}
        </span>
        <span className={`font-semibold ${pct >= 90 ? 'text-red-500' : pct >= 70 ? 'text-amber-500' : 'text-gray-700'}`}>
          {model.requests_used.toLocaleString()} / {model.requests_limit.toLocaleString()}
        </span>
      </div>
      <ProgressBar pct={pct} color={colorClass} />
      <div className="flex justify-between text-[10px] text-gray-400">
        <span>잔여 {remaining.toLocaleString()}회</span>
        <span>토큰 {formatTokens(model.total_tokens)}</span>
      </div>
    </div>
  );
}

export default function UsageIndicator() {
  const [data, setData]       = useState<UsageData | null>(null);
  const [open, setOpen]       = useState(false);
  const [loading, setLoading] = useState(false);

  const fetchUsage = useCallback(async () => {
    try {
      setLoading(true);
      const res = await axios.get<UsageData>('/api/analysis/usage');
      setData(res.data);
    } catch {
      // 조용히 실패 (선택적 기능)
    } finally {
      setLoading(false);
    }
  }, []);

  // 패널 열릴 때마다 갱신
  useEffect(() => {
    if (open) fetchUsage();
  }, [open, fetchUsage]);

  // 30초마다 자동 갱신 (열려있을 때만)
  useEffect(() => {
    if (!open) return;
    const id = setInterval(fetchUsage, 30_000);
    return () => clearInterval(id);
  }, [open, fetchUsage]);

  // 총 요청 수 (배지용)
  const totalUsed = data
    ? data.models.flash.requests_used + data.models.flash_meta.requests_used
    : null;

  const maxPct = data
    ? Math.max(data.models.flash.requests_pct, data.models.flash_meta.requests_pct)
    : 0;

  const badgeColor =
    maxPct >= 90 ? 'bg-red-500'
    : maxPct >= 70 ? 'bg-amber-400'
    : 'bg-emerald-500';

  return (
    <div className="relative">
      {/* 트리거 버튼 */}
      <button
        onClick={() => setOpen(v => !v)}
        className="flex items-center gap-1.5 text-[12px] text-white/60 hover:text-white transition-colors border border-white/20 hover:border-white/40 px-3 py-1.5"
        title="AI API 사용량"
      >
        <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z"/>
        </svg>
        <span className="hidden sm:inline">API 사용량</span>
        {totalUsed !== null && (
          <span className={`ml-0.5 text-[10px] px-1 py-0.5 rounded-full text-white font-bold leading-none ${badgeColor}`}>
            {totalUsed}
          </span>
        )}
      </button>

      {/* 드롭다운 패널 */}
      {open && (
        <>
          {/* 바깥 클릭 닫기 */}
          <div className="fixed inset-0 z-10" onClick={() => setOpen(false)} />

          <div className="absolute right-0 top-full mt-2 w-64 bg-white border border-gray-200 rounded-lg shadow-lg z-20 p-4 space-y-4">
            {/* 헤더 */}
            <div className="flex items-center justify-between">
              <p className="text-[12px] font-semibold text-gray-800">AI API 일일 사용량</p>
              <button
                onClick={fetchUsage}
                disabled={loading}
                className="text-gray-400 hover:text-gray-600 transition-colors"
                title="새로고침"
              >
                <svg className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M21 12a9 9 0 01-9 9m9-9a9 9 0 00-9-9m9 9H3m9 9a9 9 0 01-9-9m9 9c1.657 0 3-4.03 3-9s-1.343-9-3-9m0 18c-1.657 0-3-4.03-3-9s1.343-9 3-9"/>
                </svg>
              </button>
            </div>

            {data ? (
              <>
                {/* 일반 모듈 */}
                <ModelRow
                  model={data.models.flash}
                  colorClass="bg-blue-500"
                />

                <div className="border-t border-gray-100" />

                {/* 심화 분석 */}
                <ModelRow
                  model={data.models.flash_meta}
                  colorClass="bg-purple-500"
                />

                {/* 리셋 안내 */}
                <div className="flex items-center gap-1 text-[10px] text-gray-400 pt-1 border-t border-gray-100">
                  <svg className="w-3 h-3 flex-shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/>
                  </svg>
                  <span>
                    {formatResetTime(data.reset_in_seconds)}
                    {data.reset_time_kst
                      ? ` (KST ${data.reset_time_kst} · ${data.reset_tz ?? 'PT'} 자정)`
                      : ' (PT 자정)'}
                  </span>
                </div>
              </>
            ) : (
              <div className="text-center text-[12px] text-gray-400 py-4">
                {loading ? '불러오는 중...' : '데이터 없음'}
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}
