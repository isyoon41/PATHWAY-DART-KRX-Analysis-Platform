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
// McKinsey 모노크로매틱 팔레트
// ──────────────────────────────────────────
const C = {
  navy:      '#1F3864',   // 주 계열 (가장 진함)
  blue:      '#2E75B6',   // 보조 계열
  steel:     '#4472C4',   // 중간
  light:     '#8FAADC',   // 밝은 계열
  pale:      '#C9D8EC',   // 가장 밝음
  grid:      '#E8EDF2',   // 격자선
  zero:      '#94A3B8',   // 기준선(0)
};

// ──────────────────────────────────────────
// 유틸
// ──────────────────────────────────────────
function toHundredMillion(val?: number): number | null {
  if (val == null) return null;
  return Math.round(val / 100_000_000);
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
    <div className="bg-white border border-[#E2E8F0] rounded shadow-md p-3 text-sm min-w-[160px]">
      <p className="text-[11px] font-semibold text-[#64748B] uppercase tracking-wider mb-2">{label}</p>
      {payload.map((p: any) => (
        <div key={p.dataKey} className="flex items-center justify-between gap-4 mb-1">
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-sm flex-shrink-0" style={{ background: p.fill || p.stroke }} />
            <span className="text-[#64748B] text-xs">{p.name}</span>
          </div>
          <span className="font-semibold text-[#0F172A] text-xs tabular-nums">
            {p.value != null ? `${p.value.toLocaleString()}${unit}` : 'N/A'}
          </span>
        </div>
      ))}
    </div>
  );
};

// ──────────────────────────────────────────
// 공통 축 스타일
// ──────────────────────────────────────────
const axisStyle = { fontSize: 11, fill: '#64748B', fontFamily: 'inherit' };

// ──────────────────────────────────────────
// 매출 / 영업이익 / 순이익 Bar Chart
// ──────────────────────────────────────────
export function RevenueChart({ financial }: { financial: FinancialData }) {
  const current    = financial.income_statement?.current;
  const previous   = financial.income_statement?.previous;
  const twoYearsAgo = financial.income_statement?.two_years_ago;
  const periods    = financial.periods;

  const data = [
    twoYearsAgo && {
      name: periods?.two_years_ago || '전전기',
      매출액:   toHundredMillion(twoYearsAgo?.revenue),
      영업이익: toHundredMillion(twoYearsAgo?.operating_profit),
      순이익:   toHundredMillion(twoYearsAgo?.net_income),
    },
    {
      name: periods?.previous || '전기',
      매출액:   toHundredMillion(previous?.revenue),
      영업이익: toHundredMillion(previous?.operating_profit),
      순이익:   toHundredMillion(previous?.net_income),
    },
    {
      name: periods?.current || '당기',
      매출액:   toHundredMillion(current?.revenue),
      영업이익: toHundredMillion(current?.operating_profit),
      순이익:   toHundredMillion(current?.net_income),
    },
  ].filter(Boolean).filter((d: any) => d.매출액 != null || d.영업이익 != null) as any[];

  if (!data.length) return <EmptyChart label="재무 데이터 없음" />;

  return (
    <ResponsiveContainer width="100%" height={260}>
      <BarChart data={data} margin={{ top: 4, right: 16, left: 4, bottom: 4 }} barGap={3} barCategoryGap="30%">
        <CartesianGrid strokeDasharray="0" stroke={C.grid} vertical={false} />
        <XAxis dataKey="name" tick={axisStyle} axisLine={false} tickLine={false} />
        <YAxis tickFormatter={fmt억} tick={axisStyle} width={56} axisLine={false} tickLine={false} />
        <Tooltip content={<CustomTooltip unit="억원" />} cursor={{ fill: '#F1F5F9' }} />
        <Legend wrapperStyle={{ fontSize: 11, color: '#64748B' }} iconType="square" iconSize={10} />
        <Bar dataKey="매출액"   fill={C.navy}  radius={[2, 2, 0, 0]} />
        <Bar dataKey="영업이익" fill={C.blue}  radius={[2, 2, 0, 0]} />
        <Bar dataKey="순이익"   fill={C.light} radius={[2, 2, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}

// ──────────────────────────────────────────
// 이익률 Line Chart
// ──────────────────────────────────────────
export function MarginChart({ financial }: { financial: FinancialData }) {
  const ratios  = financial.ratios;
  const periods = financial.periods;

  const prevIS       = financial.income_statement?.previous;
  const prevRev      = prevIS?.revenue;
  const prevOpMargin = prevRev && prevIS?.operating_profit != null
    ? (prevIS.operating_profit! / prevRev) * 100 : null;
  const prevNetMargin = prevRev && prevIS?.net_income != null
    ? (prevIS.net_income! / prevRev) * 100 : null;

  const twoIS        = financial.income_statement?.two_years_ago;
  const twoRev       = twoIS?.revenue;
  const twoOpMargin  = twoRev && twoIS?.operating_profit != null
    ? (twoIS.operating_profit! / twoRev) * 100 : null;
  const twoNetMargin = twoRev && twoIS?.net_income != null
    ? (twoIS.net_income! / twoRev) * 100 : null;

  const data = [
    twoIS && {
      name: periods?.two_years_ago || '전전기',
      영업이익률: pct(twoOpMargin ?? undefined),
      순이익률:   pct(twoNetMargin ?? undefined),
    },
    {
      name: periods?.previous || '전기',
      영업이익률: pct(prevOpMargin ?? undefined),
      순이익률:   pct(prevNetMargin ?? undefined),
    },
    {
      name: periods?.current || '당기',
      영업이익률: pct(ratios?.operating_margin_pct),
      순이익률:   pct(ratios?.net_margin_pct),
    },
  ].filter(Boolean).filter((d: any) => d.영업이익률 != null || d.순이익률 != null) as any[];

  if (!data.length) return <EmptyChart label="이익률 데이터 없음" />;

  return (
    <ResponsiveContainer width="100%" height={260}>
      <LineChart data={data} margin={{ top: 4, right: 16, left: 4, bottom: 4 }}>
        <CartesianGrid strokeDasharray="0" stroke={C.grid} vertical={false} />
        <XAxis dataKey="name" tick={axisStyle} axisLine={false} tickLine={false} />
        <YAxis tickFormatter={(v) => `${v}%`} tick={axisStyle} width={40} axisLine={false} tickLine={false} />
        <Tooltip content={<CustomTooltip unit="%" />} cursor={{ stroke: C.grid, strokeWidth: 1 }} />
        <Legend wrapperStyle={{ fontSize: 11, color: '#64748B' }} iconType="plainline" />
        <ReferenceLine y={0} stroke={C.zero} strokeDasharray="4 2" />
        <Line
          type="linear"
          dataKey="영업이익률"
          stroke={C.navy}
          strokeWidth={2}
          dot={{ r: 4, fill: C.navy, strokeWidth: 0 }}
          activeDot={{ r: 5, fill: C.navy }}
        />
        <Line
          type="linear"
          dataKey="순이익률"
          stroke={C.light}
          strokeWidth={2}
          strokeDasharray="5 3"
          dot={{ r: 4, fill: C.light, strokeWidth: 0 }}
          activeDot={{ r: 5, fill: C.light }}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}

// ──────────────────────────────────────────
// 재무상태 Bar Chart (자산 / 부채 / 자본)
// ──────────────────────────────────────────
export function BalanceChart({ financial }: { financial: FinancialData }) {
  const current  = financial.balance_sheet?.current;
  const previous = financial.balance_sheet?.previous;
  const periods  = financial.periods;

  const data = [
    {
      name: periods?.previous || '전기',
      자산: toHundredMillion(previous?.total_assets),
      부채: toHundredMillion(previous?.total_liabilities),
      자본: toHundredMillion(previous?.total_equity),
    },
    {
      name: periods?.current || '당기',
      자산: toHundredMillion(current?.total_assets),
      부채: toHundredMillion(current?.total_liabilities),
      자본: toHundredMillion(current?.total_equity),
    },
  ].filter((d) => d.자산 != null);

  if (!data.length) return <EmptyChart label="재무상태 데이터 없음" />;

  return (
    <ResponsiveContainer width="100%" height={260}>
      <BarChart data={data} margin={{ top: 4, right: 16, left: 4, bottom: 4 }} barGap={3} barCategoryGap="35%">
        <CartesianGrid strokeDasharray="0" stroke={C.grid} vertical={false} />
        <XAxis dataKey="name" tick={axisStyle} axisLine={false} tickLine={false} />
        <YAxis tickFormatter={fmt억} tick={axisStyle} width={60} axisLine={false} tickLine={false} />
        <Tooltip content={<CustomTooltip unit="억원" />} cursor={{ fill: '#F1F5F9' }} />
        <Legend wrapperStyle={{ fontSize: 11, color: '#64748B' }} iconType="square" iconSize={10} />
        <Bar dataKey="자산" fill={C.navy}  radius={[2, 2, 0, 0]} />
        <Bar dataKey="부채" fill={C.steel} radius={[2, 2, 0, 0]} />
        <Bar dataKey="자본" fill={C.light} radius={[2, 2, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}

// ──────────────────────────────────────────
// 현금흐름 Bar Chart
// ──────────────────────────────────────────
export function CashFlowChart({ financial }: { financial: FinancialData }) {
  const current  = financial.cash_flow?.current;
  const previous = financial.cash_flow?.previous;
  const periods  = financial.periods;

  const data = [
    {
      name: periods?.previous || '전기',
      영업: toHundredMillion(previous?.operating),
      투자: toHundredMillion(previous?.investing),
      재무: toHundredMillion(previous?.financing),
    },
    {
      name: periods?.current || '당기',
      영업: toHundredMillion(current?.operating),
      투자: toHundredMillion(current?.investing),
      재무: toHundredMillion(current?.financing),
    },
  ].filter((d) => d.영업 != null || d.투자 != null);

  if (!data.length) return <EmptyChart label="현금흐름 데이터 없음" />;

  return (
    <ResponsiveContainer width="100%" height={260}>
      <BarChart data={data} margin={{ top: 4, right: 16, left: 4, bottom: 4 }} barGap={3} barCategoryGap="35%">
        <CartesianGrid strokeDasharray="0" stroke={C.grid} vertical={false} />
        <XAxis dataKey="name" tick={axisStyle} axisLine={false} tickLine={false} />
        <YAxis tickFormatter={fmt억} tick={axisStyle} width={60} axisLine={false} tickLine={false} />
        <Tooltip content={<CustomTooltip unit="억원" />} cursor={{ fill: '#F1F5F9' }} />
        <Legend wrapperStyle={{ fontSize: 11, color: '#64748B' }} iconType="square" iconSize={10} />
        <ReferenceLine y={0} stroke={C.zero} strokeDasharray="4 2" />
        <Bar dataKey="영업" fill={C.navy}  radius={[2, 2, 0, 0]} />
        <Bar dataKey="투자" fill={C.steel} radius={[2, 2, 0, 0]} />
        <Bar dataKey="재무" fill={C.light} radius={[2, 2, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}

// ──────────────────────────────────────────
// 빈 차트
// ──────────────────────────────────────────
function EmptyChart({ label }: { label: string }) {
  return (
    <div className="h-[260px] flex items-center justify-center bg-[#F7F9FC] rounded border border-dashed border-[#CBD5E1]">
      <p className="text-[#94A3B8] text-xs tracking-wide uppercase">{label}</p>
    </div>
  );
}
