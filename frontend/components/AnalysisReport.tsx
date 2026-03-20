'use client';

import React, { useState } from 'react';
import {
  Brain,
  BarChart3,
  FileText,
  Building2,
  ExternalLink,
  AlertCircle,
  TrendingUp,
  TrendingDown,
  Minus,
  Calendar,
  Globe,
  Phone,
  MapPin,
  ChevronDown,
  ChevronUp,
} from 'lucide-react';
import {
  ComprehensiveAnalysis,
  AIReportData,
  AnalysisOptions,
  FinancialData,
} from '@/lib/api';
import SourceBadge from './SourceBadge';
import {
  RevenueChart,
  MarginChart,
  BalanceChart,
  CashFlowChart,
} from './charts/FinancialChart';

// ──────────────────────────────────────────────────────────────────────
// 탭 정의
// ──────────────────────────────────────────────────────────────────────
const TABS = [
  { id: 'ai', icon: Brain, label: 'AI 리포트', color: 'purple' },
  { id: 'financial', icon: BarChart3, label: '재무 분석', color: 'blue' },
  { id: 'disclosures', icon: FileText, label: '공시 동향', color: 'green' },
  { id: 'company', icon: Building2, label: '기업 정보', color: 'gray' },
] as const;

type TabId = (typeof TABS)[number]['id'];

// ──────────────────────────────────────────────────────────────────────
// 마크다운 간이 렌더러
// ──────────────────────────────────────────────────────────────────────
function MarkdownRenderer({ text }: { text: string }) {
  const lines = text.split('\n');

  return (
    <div className="space-y-0.5 text-gray-800 leading-relaxed text-[15px]">
      {lines.map((line, i) => {
        // H2
        if (/^## (.+)/.test(line)) {
          const m = line.match(/^## (.+)/);
          return (
            <h2 key={i} className="text-xl font-bold text-gray-900 mt-6 mb-2 pb-1 border-b border-gray-200">
              {m![1].replace(/\*\*/g, '')}
            </h2>
          );
        }
        // H3
        if (/^### (.+)/.test(line)) {
          const m = line.match(/^### (.+)/);
          return (
            <h3 key={i} className="text-base font-semibold text-indigo-700 mt-5 mb-1.5">
              {m![1].replace(/\*\*/g, '')}
            </h3>
          );
        }
        // H4
        if (/^#### (.+)/.test(line)) {
          const m = line.match(/^#### (.+)/);
          return (
            <h4 key={i} className="text-sm font-semibold text-gray-700 mt-3 mb-1">
              {m![1].replace(/\*\*/g, '')}
            </h4>
          );
        }
        // 테이블 행
        if (/^\|/.test(line) && /\|$/.test(line)) {
          const cells = line.split('|').filter((c) => c.trim() !== '');
          const isSeparator = cells.every((c) => /^[-: ]+$/.test(c));
          if (isSeparator) return null;
          return (
            <div key={i} className="grid gap-px" style={{ gridTemplateColumns: `repeat(${cells.length}, 1fr)` }}>
              {cells.map((cell, ci) => (
                <div
                  key={ci}
                  className={`px-3 py-1.5 text-sm border border-gray-200 ${
                    ci === 0 ? 'bg-gray-50 font-medium' : 'bg-white'
                  }`}
                >
                  {cell.trim().replace(/\*\*/g, '')}
                </div>
              ))}
            </div>
          );
        }
        // 불릿
        if (/^- (.+)/.test(line)) {
          const m = line.match(/^- (.+)/);
          return (
            <div key={i} className="flex gap-2 items-start pl-2 py-0.5">
              <span className="w-1.5 h-1.5 rounded-full bg-indigo-400 mt-2 flex-shrink-0" />
              <span
                className="flex-1"
                dangerouslySetInnerHTML={{
                  __html: m![1]
                    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
                    .replace(/`(.+?)`/g, '<code class="bg-gray-100 px-1 rounded text-sm font-mono">$1</code>'),
                }}
              />
            </div>
          );
        }
        // 숫자 리스트
        if (/^\d+\. (.+)/.test(line)) {
          const m = line.match(/^(\d+)\. (.+)/);
          return (
            <div key={i} className="flex gap-3 items-start pl-2 py-0.5">
              <span className="w-5 h-5 rounded-full bg-indigo-100 text-indigo-700 text-xs font-bold flex items-center justify-center flex-shrink-0 mt-0.5">
                {m![1]}
              </span>
              <span
                className="flex-1"
                dangerouslySetInnerHTML={{
                  __html: m![2]
                    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
                    .replace(/`(.+?)`/g, '<code class="bg-gray-100 px-1 rounded text-sm font-mono">$1</code>'),
                }}
              />
            </div>
          );
        }
        // 빈 줄
        if (line.trim() === '') return <div key={i} className="h-2" />;
        // 일반 텍스트
        return (
          <p
            key={i}
            className="leading-relaxed"
            dangerouslySetInnerHTML={{
              __html: line
                .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
                .replace(/`(.+?)`/g, '<code class="bg-gray-100 px-1 rounded text-sm font-mono">$1</code>'),
            }}
          />
        );
      })}
    </div>
  );
}

// ──────────────────────────────────────────────────────────────────────
// 재무 요약 카드
// ──────────────────────────────────────────────────────────────────────
function MetricCard({
  label,
  value,
  unit,
  growth,
}: {
  label: string;
  value?: number | null;
  unit: string;
  growth?: number | null;
}) {
  const formatted =
    value == null
      ? 'N/A'
      : unit === '%'
      ? `${value.toFixed(1)}%`
      : unit === '배'
      ? `${value.toFixed(2)}배`
      : `${Math.round(value / 100).toLocaleString()}억`;

  const growthColor =
    growth == null ? 'text-gray-400' : growth > 0 ? 'text-emerald-600' : growth < 0 ? 'text-red-500' : 'text-gray-500';

  const GrowthIcon = growth == null ? Minus : growth > 0 ? TrendingUp : growth < 0 ? TrendingDown : Minus;

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-4">
      <p className="text-xs text-gray-500 mb-1">{label}</p>
      <p className="text-2xl font-bold text-gray-900">{formatted}</p>
      {growth != null && (
        <div className={`flex items-center gap-1 mt-1.5 text-xs font-medium ${growthColor}`}>
          <GrowthIcon className="w-3.5 h-3.5" />
          <span>전년 대비 {growth > 0 ? '+' : ''}{growth.toFixed(1)}%</span>
        </div>
      )}
    </div>
  );
}

// ──────────────────────────────────────────────────────────────────────
// 메인 컴포넌트
// ──────────────────────────────────────────────────────────────────────
interface AnalysisReportProps {
  options: AnalysisOptions;
  comprehensive: ComprehensiveAnalysis | null;
  aiReport: AIReportData | null;
  onBack: () => void;
}

export default function AnalysisReport({
  options,
  comprehensive,
  aiReport,
  onBack,
}: AnalysisReportProps) {
  const defaultTab: TabId =
    options.includeAI && aiReport ? 'ai' : options.includeFinancial ? 'financial' : 'disclosures';
  const [activeTab, setActiveTab] = useState<TabId>(defaultTab);
  const [disclosureExpanded, setDisclosureExpanded] = useState(false);

  const companyInfo = comprehensive?.company_info;
  const financial: FinancialData | undefined = comprehensive?.financial_statement;
  const disclosures = comprehensive?.recent_disclosures;

  const visibleTabs = TABS.filter((t) => {
    if (t.id === 'ai') return options.includeAI && aiReport;
    if (t.id === 'financial') return options.includeFinancial && financial;
    if (t.id === 'disclosures') return options.includeDisclosures && disclosures;
    return true; // company tab always visible
  });

  const tabColors: Record<string, string> = {
    purple: 'border-purple-500 text-purple-700 bg-purple-50',
    blue: 'border-blue-500 text-blue-700 bg-blue-50',
    green: 'border-emerald-500 text-emerald-700 bg-emerald-50',
    gray: 'border-gray-400 text-gray-700 bg-gray-50',
  };

  return (
    <div className="w-full">
      {/* 헤더 */}
      <div className="bg-gradient-to-r from-slate-800 to-indigo-900 text-white rounded-2xl shadow-xl p-7 mb-6">
        <div className="flex items-start gap-5">
          <div className="w-16 h-16 bg-white/15 rounded-xl flex items-center justify-center flex-shrink-0">
            <Building2 className="w-9 h-9" />
          </div>
          <div className="flex-1 min-w-0">
            <h1 className="text-3xl font-bold truncate">{companyInfo?.corp_name || aiReport?.corp_name}</h1>
            {companyInfo?.corp_name_eng && (
              <p className="text-slate-300 text-base mt-0.5">{companyInfo.corp_name_eng}</p>
            )}
            <div className="flex flex-wrap gap-2 mt-3">
              {companyInfo?.stock_code && (
                <span className="bg-white/15 px-3 py-1 rounded-full text-sm">
                  종목코드: {companyInfo.stock_code}
                </span>
              )}
              {companyInfo?.ceo_nm && (
                <span className="bg-white/15 px-3 py-1 rounded-full text-sm">
                  대표이사: {companyInfo.ceo_nm}
                </span>
              )}
              <span className="bg-white/15 px-3 py-1 rounded-full text-sm">
                기준연도: {aiReport?.base_year || options.bsnsYear}년
              </span>
              {aiReport?.data_coverage.has_governance && (
                <span className="bg-purple-500/40 px-3 py-1 rounded-full text-sm">
                  AI 분석 포함
                </span>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* 탭 네비게이션 */}
      <div className="flex gap-2 mb-6 overflow-x-auto pb-1">
        {visibleTabs.map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-semibold border-2 transition-all whitespace-nowrap ${
                isActive
                  ? tabColors[tab.color]
                  : 'border-gray-200 text-gray-500 hover:border-gray-300'
              }`}
            >
              <Icon className="w-4 h-4" />
              {tab.label}
            </button>
          );
        })}

        {/* 뒤로 */}
        <button
          onClick={onBack}
          className="ml-auto px-4 py-2.5 rounded-xl text-sm text-gray-500 hover:bg-gray-100 transition-all whitespace-nowrap"
        >
          ← 새 분석
        </button>
      </div>

      {/* ── Tab: AI 리포트 ── */}
      {activeTab === 'ai' && aiReport && (
        <div className="bg-white rounded-2xl shadow-lg border border-gray-200 p-8">
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 bg-purple-100 rounded-xl flex items-center justify-center">
                <Brain className="w-5 h-5 text-purple-600" />
              </div>
              <div>
                <h2 className="text-xl font-bold text-gray-900">AI 종합 분석 리포트</h2>
                <p className="text-xs text-gray-400 mt-0.5">
                  {aiReport.model} · {new Date(aiReport.generated_at).toLocaleString('ko-KR')}
                </p>
              </div>
            </div>
            <div className="hidden md:flex items-center gap-4 text-xs text-gray-400">
              <span>수집 연도: {aiReport.data_coverage.annual_years?.join(', ')}</span>
              <span>공시: {aiReport.data_coverage.disclosure_count}건</span>
            </div>
          </div>

          <div className="border-t border-gray-100 pt-6">
            <MarkdownRenderer text={aiReport.report} />
          </div>

          <div className="mt-8 pt-4 border-t border-gray-100">
            <SourceBadge
              provider={aiReport._source.provider}
              retrievedAt={aiReport._source.generated_at}
            />
          </div>
        </div>
      )}

      {/* ── Tab: 재무 분석 ── */}
      {activeTab === 'financial' && financial && (
        <div className="space-y-6">
          {/* 요약 지표 */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <MetricCard
              label="매출액"
              value={financial.income_statement?.current?.revenue}
              unit="억원"
              growth={financial.growth?.revenue_yoy_pct}
            />
            <MetricCard
              label="영업이익"
              value={financial.income_statement?.current?.operating_profit}
              unit="억원"
              growth={financial.growth?.operating_profit_yoy_pct}
            />
            <MetricCard
              label="당기순이익"
              value={financial.income_statement?.current?.net_income}
              unit="억원"
              growth={financial.growth?.net_income_yoy_pct}
            />
            <MetricCard
              label="영업이익률"
              value={financial.ratios?.operating_margin_pct}
              unit="%"
            />
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <MetricCard label="부채비율" value={financial.ratios?.debt_ratio_pct} unit="%" />
            <MetricCard label="유동비율" value={financial.ratios?.current_ratio} unit="배" />
            <MetricCard label="ROE" value={financial.ratios?.roe_pct} unit="%" />
            <MetricCard label="ROA" value={financial.ratios?.roa_pct} unit="%" />
          </div>

          {/* 차트 */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="bg-white rounded-2xl shadow-lg border border-gray-200 p-6">
              <h3 className="text-sm font-semibold text-gray-700 mb-4">매출 · 이익 추이 (억원)</h3>
              <RevenueChart financial={financial} />
            </div>
            <div className="bg-white rounded-2xl shadow-lg border border-gray-200 p-6">
              <h3 className="text-sm font-semibold text-gray-700 mb-4">이익률 추이 (%)</h3>
              <MarginChart financial={financial} />
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="bg-white rounded-2xl shadow-lg border border-gray-200 p-6">
              <h3 className="text-sm font-semibold text-gray-700 mb-4">재무상태 (억원)</h3>
              <BalanceChart financial={financial} />
            </div>
            <div className="bg-white rounded-2xl shadow-lg border border-gray-200 p-6">
              <h3 className="text-sm font-semibold text-gray-700 mb-4">현금흐름 (억원)</h3>
              <CashFlowChart financial={financial} />
            </div>
          </div>

          {financial._source && (
            <div className="bg-gray-50 rounded-xl p-4 border border-gray-200">
              <SourceBadge
                provider={financial._source.provider}
                retrievedAt={financial._source.retrieved_at}
              />
            </div>
          )}
        </div>
      )}

      {/* ── Tab: 공시 동향 ── */}
      {activeTab === 'disclosures' && disclosures && (
        <div className="bg-white rounded-2xl shadow-lg border border-gray-200 p-6">
          <div className="flex items-center justify-between mb-5">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 bg-emerald-100 rounded-xl flex items-center justify-center">
                <FileText className="w-5 h-5 text-emerald-600" />
              </div>
              <h2 className="text-xl font-bold text-gray-900">공시 동향</h2>
            </div>
            <span className="text-sm text-gray-500 bg-gray-100 px-3 py-1 rounded-full">
              {disclosures.list?.length || 0}건
            </span>
          </div>

          <div className="space-y-3">
            {(disclosureExpanded
              ? disclosures.list
              : disclosures.list?.slice(0, 8)
            )?.map((d) => (
              <div
                key={d.rcept_no}
                className="flex items-start justify-between gap-4 p-4 rounded-xl border border-gray-200 hover:border-emerald-200 hover:bg-emerald-50 transition-all group"
              >
                <div className="flex-1 min-w-0">
                  <p className="font-medium text-gray-900 text-sm mb-1 group-hover:text-emerald-700 transition-colors">
                    {d.report_nm}
                  </p>
                  <div className="flex items-center gap-3 text-xs text-gray-400">
                    <span className="flex items-center gap-1">
                      <Calendar className="w-3 h-3" />
                      {d.rcept_dt}
                    </span>
                    <span>제출: {d.flr_nm}</span>
                    {d.rm && (
                      <span className="bg-amber-100 text-amber-700 px-1.5 py-0.5 rounded">
                        {d.rm}
                      </span>
                    )}
                  </div>
                </div>
                <a
                  href={d._source_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-1 px-3 py-1.5 bg-white border border-gray-200 text-gray-600 rounded-lg hover:bg-emerald-600 hover:text-white hover:border-emerald-600 transition-all text-xs font-medium flex-shrink-0"
                >
                  공시 보기
                  <ExternalLink className="w-3 h-3" />
                </a>
              </div>
            ))}
          </div>

          {(disclosures.list?.length || 0) > 8 && (
            <button
              onClick={() => setDisclosureExpanded(!disclosureExpanded)}
              className="w-full mt-4 py-3 text-sm text-gray-500 hover:text-gray-700 hover:bg-gray-50 rounded-xl border border-gray-200 flex items-center justify-center gap-2 transition-all"
            >
              {disclosureExpanded ? (
                <>접기 <ChevronUp className="w-4 h-4" /></>
              ) : (
                <>나머지 {(disclosures.list?.length || 0) - 8}건 더 보기 <ChevronDown className="w-4 h-4" /></>
              )}
            </button>
          )}

          {disclosures._source && (
            <div className="mt-4 pt-4 border-t border-gray-100">
              <SourceBadge
                provider={disclosures._source.provider}
                retrievedAt={disclosures._source.retrieved_at}
              />
            </div>
          )}
        </div>
      )}

      {/* ── Tab: 기업 정보 ── */}
      {activeTab === 'company' && companyInfo && (
        <div className="bg-white rounded-2xl shadow-lg border border-gray-200 p-6">
          <div className="flex items-center gap-3 mb-5">
            <div className="w-9 h-9 bg-gray-100 rounded-xl flex items-center justify-center">
              <Building2 className="w-5 h-5 text-gray-600" />
            </div>
            <h2 className="text-xl font-bold text-gray-900">기업 기본 정보</h2>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {[
              { icon: Building2, label: '기업코드', value: companyInfo.corp_code },
              { icon: Calendar, label: '설립일', value: companyInfo.est_dt },
              { icon: Calendar, label: '상장일', value: companyInfo.listing_dt },
              { icon: Calendar, label: '결산월', value: companyInfo.acc_mt ? `${companyInfo.acc_mt}월` : undefined },
              { icon: Globe, label: '홈페이지', value: companyInfo.hm_url, href: companyInfo.hm_url },
              { icon: Phone, label: '전화번호', value: companyInfo.phn_no },
              { icon: MapPin, label: '주소', value: companyInfo.adres, wide: true },
            ]
              .filter((f) => f.value)
              .map(({ icon: Icon, label, value, href, wide }) => (
                <div
                  key={label}
                  className={`flex items-start gap-3 p-4 bg-gray-50 rounded-xl border border-gray-100 ${wide ? 'md:col-span-2' : ''}`}
                >
                  <div className="w-8 h-8 bg-white rounded-lg flex items-center justify-center flex-shrink-0 shadow-sm">
                    <Icon className="w-4 h-4 text-gray-500" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="text-xs text-gray-400 mb-0.5">{label}</p>
                    {href ? (
                      <a href={href} target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline text-sm font-medium truncate block">
                        {value}
                      </a>
                    ) : (
                      <p className="text-sm font-medium text-gray-900">{value}</p>
                    )}
                  </div>
                </div>
              ))}
          </div>

          <div className="mt-6 pt-4 border-t border-gray-100">
            <SourceBadge
              provider={companyInfo._source.provider}
              url={companyInfo._source.url}
              retrievedAt={companyInfo._source.retrieved_at}
            />
          </div>
        </div>
      )}

      {/* 에러 상태 */}
      {!comprehensive && !aiReport && (
        <div className="bg-red-50 border border-red-200 rounded-2xl p-6 flex items-start gap-3">
          <AlertCircle className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" />
          <div>
            <h3 className="font-semibold text-red-800 mb-1">분석 데이터 없음</h3>
            <p className="text-sm text-red-600">데이터를 불러오지 못했습니다. 다시 시도해주세요.</p>
          </div>
        </div>
      )}
    </div>
  );
}
