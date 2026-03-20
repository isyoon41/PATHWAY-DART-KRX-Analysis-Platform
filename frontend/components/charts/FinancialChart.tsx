'use client';

import React from 'react';
import {
  BarChart,
  Bar,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  ReferenceLine,
} from 'recharts';
import { FinancialData } from '@/lib/api';

// ──────────────────────────────────────────
// 유틸
// ──────────────────────────────────────────
function toHundredMillion(val?: number): number | null {
  if (val == null) return null;
  return Math.round(val / 100); // 백만원 → 억원
}

function pct(val?: number): number | null {
  if (val == null) return null;
  return Math.round(val * 10) / 10;
}

function fmt억(v: number) {
  if (Math.abs(v) >= 10000) return `${(v / 10000).toFixed(1)}조`;
  return `${v.toLocaleString()}억`;
}

const CustomTooltip = ({
  active,
  payload,
  label,
  unit = '억원',
}: {
  active?: boolean;
  payload?: any[];
  label?: string;
  unit?: string;
}) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-white border border-gray-200 rounded-xl shadow-lg p-3 text-sm">
      <p className="font-semibold text-gray-700 mb-2">{label}</p>
      {payload.map((p: any) => (
        <div key={p.dataKey} className="flex items-center gap-2 mb-0.5">
          <span className="w-3 h-3 rounded-full" style={{ background: p.fill || p.stroke }} />
          <span className="text-gray-600">{p.name}:</span>
          <span className="font-medium text-gray-900">
            {p.value != null ? `${p.value.toLocaleString()}${unit}` : 'N/A'}
          </span>
        </div>
      ))}
    </div>
  );
};

// ──────────────────────────────────────────
// 매출 / 영업이익 / 순이익 Bar Chart
// ──────────────────────────────────────────
export function RevenueChart({ financial }: { financial: FinancialData }) {
  const current = financial.income_statement?.current;
  const previous = financial.income_statement?.previous;
  const periods = financial.periods || [];

  const data = [
    {
      name: periods[1] || '전년도',
      매출액: toHundredMillion(previous?.revenue),
      영업이익: toHundredMillion(previous?.operating_profit),
      순이익: toHundredMillion(previous?.net_income),
    },
    {
      name: periods[0] || '당기',
      매출액: toHundredMillion(current?.revenue),
      영업이익: toHundredMillion(current?.operating_profit),
      순이익: toHundredMillion(current?.net_income),
    },
  ].filter((d) => d.매출액 != null || d.영업이익 != null);

  if (!data.length) return <EmptyChart label="재무 데이터 없음" />;

  return (
    <ResponsiveContainer width="100%" height={280}>
      <BarChart data={data} margin={{ top: 5, right: 20, left: 10, bottom: 5 }} barGap={4}>
        <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
        <XAxis dataKey="name" tick={{ fontSize: 13 }} />
        <YAxis
          tickFormatter={(v) => fmt억(v)}
          tick={{ fontSize: 11 }}
          width={60}
        />
        <Tooltip content={<CustomTooltip unit="억원" />} />
        <Legend wrapperStyle={{ fontSize: 13 }} />
        <Bar dataKey="매출액" fill="#3B82F6" radius={[4, 4, 0, 0]} />
        <Bar dataKey="영업이익" fill="#6366F1" radius={[4, 4, 0, 0]} />
        <Bar dataKey="순이익" fill="#8B5CF6" radius={[4, 4, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}

// ──────────────────────────────────────────
// 이익률 Line Chart
// ──────────────────────────────────────────
export function MarginChart({ financial }: { financial: FinancialData }) {
  const ratios = financial.ratios;
  const periods = financial.periods || [];

  // 전년도 ratios는 직접 계산
  const prevIS = financial.income_statement?.previous;
  const prevRev = prevIS?.revenue;
  const prevOpProfit = prevIS?.operating_profit;
  const prevNet = prevIS?.net_income;
  const prevOpMargin = prevRev && prevOpProfit != null ? (prevOpProfit / prevRev) * 100 : null;
  const prevNetMargin = prevRev && prevNet != null ? (prevNet / prevRev) * 100 : null;

  const data = [
    {
      name: periods[1] || '전년도',
      영업이익률: pct(prevOpMargin ?? undefined),
      순이익률: pct(prevNetMargin ?? undefined),
    },
    {
      name: periods[0] || '당기',
      영업이익률: pct(ratios?.operating_margin_pct),
      순이익률: pct(ratios?.net_margin_pct),
    },
  ].filter((d) => d.영업이익률 != null || d.순이익률 != null);

  if (!data.length) return <EmptyChart label="이익률 데이터 없음" />;

  return (
    <ResponsiveContainer width="100%" height={280}>
      <LineChart data={data} margin={{ top: 5, right: 20, left: 10, bottom: 5 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
        <XAxis dataKey="name" tick={{ fontSize: 13 }} />
        <YAxis tickFormatter={(v) => `${v}%`} tick={{ fontSize: 11 }} width={44} />
        <Tooltip content={<CustomTooltip unit="%" />} />
        <Legend wrapperStyle={{ fontSize: 13 }} />
        <ReferenceLine y={0} stroke="#e5e7eb" />
        <Line
          type="monotone"
          dataKey="영업이익률"
          stroke="#6366F1"
          strokeWidth={2.5}
          dot={{ r: 5, fill: '#6366F1' }}
          activeDot={{ r: 7 }}
        />
        <Line
          type="monotone"
          dataKey="순이익률"
          stroke="#8B5CF6"
          strokeWidth={2.5}
          dot={{ r: 5, fill: '#8B5CF6' }}
          activeDot={{ r: 7 }}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}

// ──────────────────────────────────────────
// 재무상태 Bar Chart (자산 / 부채 / 자본)
// ──────────────────────────────────────────
export function BalanceChart({ financial }: { financial: FinancialData }) {
  const current = financial.balance_sheet?.current;
  const previous = financial.balance_sheet?.previous;
  const periods = financial.periods || [];

  const data = [
    {
      name: periods[1] || '전년도',
      자산: toHundredMillion(previous?.total_assets),
      부채: toHundredMillion(previous?.total_liabilities),
      자본: toHundredMillion(previous?.total_equity),
    },
    {
      name: periods[0] || '당기',
      자산: toHundredMillion(current?.total_assets),
      부채: toHundredMillion(current?.total_liabilities),
      자본: toHundredMillion(current?.total_equity),
    },
  ].filter((d) => d.자산 != null);

  if (!data.length) return <EmptyChart label="재무상태 데이터 없음" />;

  return (
    <ResponsiveContainer width="100%" height={280}>
      <BarChart data={data} margin={{ top: 5, right: 20, left: 10, bottom: 5 }} barGap={4}>
        <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
        <XAxis dataKey="name" tick={{ fontSize: 13 }} />
        <YAxis
          tickFormatter={(v) => fmt억(v)}
          tick={{ fontSize: 11 }}
          width={64}
        />
        <Tooltip content={<CustomTooltip unit="억원" />} />
        <Legend wrapperStyle={{ fontSize: 13 }} />
        <Bar dataKey="자산" fill="#10B981" radius={[4, 4, 0, 0]} />
        <Bar dataKey="부채" fill="#F59E0B" radius={[4, 4, 0, 0]} />
        <Bar dataKey="자본" fill="#3B82F6" radius={[4, 4, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}

// ──────────────────────────────────────────
// 현금흐름 Bar Chart
// ──────────────────────────────────────────
export function CashFlowChart({ financial }: { financial: FinancialData }) {
  const current = financial.cash_flow?.current;
  const previous = financial.cash_flow?.previous;
  const periods = financial.periods || [];

  const data = [
    {
      name: periods[1] || '전년도',
      영업: toHundredMillion(previous?.operating),
      투자: toHundredMillion(previous?.investing),
      재무: toHundredMillion(previous?.financing),
    },
    {
      name: periods[0] || '당기',
      영업: toHundredMillion(current?.operating),
      투자: toHundredMillion(current?.investing),
      재무: toHundredMillion(current?.financing),
    },
  ].filter((d) => d.영업 != null || d.투자 != null);

  if (!data.length) return <EmptyChart label="현금흐름 데이터 없음" />;

  return (
    <ResponsiveContainer width="100%" height={280}>
      <BarChart data={data} margin={{ top: 5, right: 20, left: 10, bottom: 5 }} barGap={4}>
        <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
        <XAxis dataKey="name" tick={{ fontSize: 13 }} />
        <YAxis
          tickFormatter={(v) => fmt억(v)}
          tick={{ fontSize: 11 }}
          width={64}
        />
        <Tooltip content={<CustomTooltip unit="억원" />} />
        <Legend wrapperStyle={{ fontSize: 13 }} />
        <ReferenceLine y={0} stroke="#9ca3af" />
        <Bar dataKey="영업" fill="#10B981" radius={[4, 4, 0, 0]} />
        <Bar dataKey="투자" fill="#EF4444" radius={[4, 4, 0, 0]} />
        <Bar dataKey="재무" fill="#F59E0B" radius={[4, 4, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}

// ──────────────────────────────────────────
// 빈 차트
// ──────────────────────────────────────────
function EmptyChart({ label }: { label: string }) {
  return (
    <div className="h-[280px] flex items-center justify-center bg-gray-50 rounded-xl border-2 border-dashed border-gray-200">
      <p className="text-gray-400 text-sm">{label}</p>
    </div>
  );
}
