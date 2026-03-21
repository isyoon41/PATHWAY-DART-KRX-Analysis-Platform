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
  { id: 'ai',          icon: Brain,    label: 'AI 리포트' },
  { id: 'financial',   icon: BarChart3, label: '재무 분석' },
  { id: 'disclosures', icon: FileText,  label: '공시 동향' },
  { id: 'company',     icon: Building2, label: '기업 정보' },
] as const;

type TabId = (typeof TABS)[number]['id'];

// ──────────────────────────────────────────────────────────────────────
// McKinsey 마크다운 렌더러
// ──────────────────────────────────────────────────────────────────────
function renderInline(text: string) {
  return text
    .replace(/\*\*(.+?)\*\*/g, '<strong class="font-semibold text-[#0F172A]">$1</strong>')
    .replace(/\*(.+?)\*/g, '<em>$1</em>')
    .replace(/`(.+?)`/g, '<code class="bg-[#F1F5F9] px-1.5 py-0.5 rounded text-[12px] font-mono text-[#334155]">$1</code>');
}

function MarkdownRenderer({ text }: { text: string }) {
  const lines = text.split('\n');

  return (
    <div className="text-[#334155] leading-[1.75] text-[14px]">
      {lines.map((line, i) => {
        /* ── 문서 제목 ## ── */
        if (/^## (.+)/.test(line)) {
          const m = line.match(/^## (.+)/);
          const title = m![1].replace(/\*\*/g, '');
          return (
            <div key={i} className="mb-8 pb-4 border-b-2 border-[#0C2340]">
              <h1 className="text-[22px] font-bold text-[#0C2340] leading-snug tracking-tight">
                {title}
              </h1>
            </div>
          );
        }

        /* ── 섹션 ### ── */
        if (/^### (.+)/.test(line)) {
          const m = line.match(/^### (.+)/);
          const heading = m![1].replace(/\*\*/g, '');
          return (
            <div key={i} className="mt-8 mb-3 flex items-baseline gap-3">
              <div className="w-1 h-5 bg-[#0C2340] flex-shrink-0 self-stretch rounded-sm" />
              <h2 className="text-[16px] font-bold text-[#0C2340] leading-tight">
                {heading}
              </h2>
            </div>
          );
        }

        /* ── 소제목 #### ── */
        if (/^#### (.+)/.test(line)) {
          const m = line.match(/^#### (.+)/);
          const heading = m![1].replace(/\*\*/g, '');
          return (
            <h3 key={i} className="mt-5 mb-2 text-[13px] font-semibold text-[#2E75B6] uppercase tracking-wide">
              {heading}
            </h3>
          );
        }

        /* ── 테이블 행 ── */
        if (/^\|/.test(line) && /\|$/.test(line)) {
          const cells = line.split('|').filter((c) => c.trim() !== '');
          const isSeparator = cells.every((c) => /^[-:= ]+$/.test(c));
          if (isSeparator) return null;

          // 다음 행이 구분자면 헤더 행
          const nextLine = lines[i + 1] ?? '';
          const isHeader =
            /^\|/.test(nextLine) &&
            nextLine
              .split('|')
              .filter((c) => c.trim())
              .every((c) => /^[-:= ]+$/.test(c));

          return (
            <div
              key={i}
              className="grid"
              style={{ gridTemplateColumns: `repeat(${cells.length}, 1fr)` }}
            >
              {cells.map((cell, ci) => (
                <div
                  key={ci}
                  className={`px-3 py-2 text-[12px] border border-[#E2E8F0] ${
                    isHeader
                      ? 'bg-[#0C2340] text-white font-semibold'
                      : ci === 0
                      ? 'bg-[#F7F9FC] font-medium text-[#0F172A]'
                      : 'bg-white text-[#334155]'
                  }`}
                >
                  <span
                    dangerouslySetInnerHTML={{
                      __html: renderInline(cell.trim()),
                    }}
                  />
                </div>
              ))}
            </div>
          );
        }

        /* ── 불릿 리스트 ── */
        if (/^\s*[-*] (.+)/.test(line)) {
          const m = line.match(/^(\s*)[-*] (.+)/);
          const indent = m![1].length;
          return (
            <div key={i} className="flex gap-2.5 items-start py-0.5" style={{ paddingLeft: indent * 12 }}>
              <span className="w-1.5 h-1.5 bg-[#2E75B6] flex-shrink-0 mt-[7px]" />
              <span
                className="flex-1 text-[14px]"
                dangerouslySetInnerHTML={{ __html: renderInline(m![2]) }}
              />
            </div>
          );
        }

        /* ── 숫자 리스트 ── */
        if (/^\d+\. (.+)/.test(line)) {
          const m = line.match(/^(\d+)\. (.+)/);
          return (
            <div key={i} className="flex gap-3 items-start py-0.5 pl-1">
              <span className="w-5 h-5 bg-[#0C2340] text-white text-[10px] font-bold flex items-center justify-center flex-shrink-0 mt-0.5 rounded-sm">
                {m![1]}
              </span>
              <span
                className="flex-1 text-[14px]"
                dangerouslySetInnerHTML={{ __html: renderInline(m![2]) }}
              />
            </div>
          );
        }

        /* ── 수평선 --- ── */
        if (/^---+$/.test(line.trim())) {
          return <hr key={i} className="my-5 border-[#E2E8F0]" />;
        }

        /* ── ### 이 없는 분석 메모 (볼드로 시작) ── */
        if (/^\*\*(.+?)\*\*:/.test(line)) {
          return (
            <p
              key={i}
              className="text-[14px] leading-[1.75]"
              dangerouslySetInnerHTML={{ __html: renderInline(line) }}
            />
          );
        }

        /* ── 빈 줄 ── */
        if (line.trim() === '') return <div key={i} className="h-3" />;

        /* ── 일반 텍스트 ── */
        return (
          <p
            key={i}
            className="text-[14px] leading-[1.75]"
            dangerouslySetInnerHTML={{ __html: renderInline(line) }}
          />
        );
      })}
    </div>
  );
}

// ──────────────────────────────────────────────────────────────────────
// 재무 지표 카드
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
      ? '—'
      : unit === '%'
      ? `${value.toFixed(1)}%`
      : unit === '배'
      ? `${value.toFixed(2)}배`
      : (() => {
          const 억 = Math.round(value / 100_000_000);
          return 억 >= 10_000
            ? `${(억 / 10_000).toFixed(1)}조원`
            : `${억.toLocaleString()}억원`;
        })();

  const isUp = growth != null && growth > 0;
  const isDown = growth != null && growth < 0;
  const GrowthIcon = growth == null ? Minus : isUp ? TrendingUp : isDown ? TrendingDown : Minus;
  const growthColor = isUp ? 'text-[#0C2340]' : isDown ? 'text-[#64748B]' : 'text-[#94A3B8]';

  return (
    <div className="bg-white border border-[#E2E8F0] border-l-4 border-l-[#1F3864] p-4 rounded-r-lg">
      <p className="text-[11px] font-semibold text-[#64748B] uppercase tracking-wider mb-2">{label}</p>
      <p className="text-[22px] font-bold text-[#0F172A] leading-none">{formatted}</p>
      {growth != null && (
        <div className={`flex items-center gap-1 mt-2 text-[11px] font-medium ${growthColor}`}>
          <GrowthIcon className="w-3 h-3" />
          <span>전년 대비 {growth > 0 ? '+' : ''}{growth.toFixed(1)}%</span>
        </div>
      )}
    </div>
  );
}

// ──────────────────────────────────────────────────────────────────────
// 차트 섹션 래퍼
// ──────────────────────────────────────────────────────────────────────
function ChartCard({ title, unit, children }: { title: string; unit: string; children: React.ReactNode }) {
  return (
    <div className="bg-white border border-[#E2E8F0] p-6">
      <div className="flex items-baseline gap-2 mb-5">
        <h3 className="text-[11px] font-semibold text-[#0C2340] uppercase tracking-widest">{title}</h3>
        <span className="text-[10px] text-[#94A3B8]">({unit})</span>
      </div>
      {children}
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
    if (t.id === 'ai')          return options.includeAI && aiReport;
    if (t.id === 'financial')   return options.includeFinancial && financial;
    if (t.id === 'disclosures') return options.includeDisclosures && disclosures;
    return true;
  });

  return (
    <div className="w-full">

      {/* ── 헤더 (Deep Navy) ── */}
      <div className="bg-[#0C2340] text-white rounded-xl shadow-md p-7 mb-1">
        <div className="flex items-start gap-5">
          <div className="w-14 h-14 bg-white/10 border border-white/20 rounded flex items-center justify-center flex-shrink-0">
            <Building2 className="w-7 h-7 text-white/80" />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-[11px] font-semibold text-white/50 uppercase tracking-widest mb-1">
              기업 분석 리포트
            </p>
            <h1 className="text-[28px] font-bold text-white leading-tight truncate">
              {companyInfo?.corp_name || aiReport?.corp_name}
            </h1>
            {companyInfo?.corp_name_eng && (
              <p className="text-white/50 text-[13px] mt-0.5 font-medium tracking-wide">
                {companyInfo.corp_name_eng}
              </p>
            )}
            <div className="flex flex-wrap gap-2 mt-4">
              {companyInfo?.stock_code && (
                <span className="bg-white/10 border border-white/20 px-2.5 py-0.5 rounded text-[12px] text-white/80">
                  {companyInfo.stock_code}
                </span>
              )}
              {companyInfo?.ceo_nm && (
                <span className="bg-white/10 border border-white/20 px-2.5 py-0.5 rounded text-[12px] text-white/80">
                  대표이사: {companyInfo.ceo_nm}
                </span>
              )}
              <span className="bg-white/10 border border-white/20 px-2.5 py-0.5 rounded text-[12px] text-white/80">
                {aiReport?.base_year || options.endYear}년 기준
              </span>
              {aiReport && (
                <span className="bg-[#2E75B6]/60 border border-[#2E75B6] px-2.5 py-0.5 rounded text-[12px] text-white font-medium">
                  AI 분석 포함
                </span>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* ── 탭 네비게이션 (언더라인 스타일) ── */}
      <div className="flex items-center gap-0 mb-6 border-b border-[#E2E8F0] bg-white px-1">
        {visibleTabs.map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 px-5 py-3.5 text-[13px] font-medium border-b-2 transition-all whitespace-nowrap -mb-px ${
                isActive
                  ? 'border-[#0C2340] text-[#0C2340]'
                  : 'border-transparent text-[#64748B] hover:text-[#334155] hover:border-[#CBD5E1]'
              }`}
            >
              <Icon className={`w-3.5 h-3.5 ${isActive ? 'text-[#0C2340]' : 'text-[#94A3B8]'}`} />
              {tab.label}
            </button>
          );
        })}
        <button
          onClick={onBack}
          className="ml-auto px-4 py-3.5 text-[12px] text-[#94A3B8] hover:text-[#334155] transition-all whitespace-nowrap"
        >
          ← 새 분석
        </button>
      </div>

      {/* ── Tab: AI 리포트 ── */}
      {activeTab === 'ai' && aiReport && (
        <div className="bg-white border border-[#E2E8F0] rounded-xl overflow-hidden">
          {/* 리포트 헤더 바 */}
          <div className="bg-[#F7F9FC] border-b border-[#E2E8F0] px-8 py-4 flex items-center justify-between">
            <div>
              <p className="text-[11px] font-semibold text-[#64748B] uppercase tracking-widest">
                AI 종합 분석 리포트
              </p>
              <p className="text-[12px] text-[#94A3B8] mt-0.5">
                {aiReport.model?.includes('gemini') ? 'Google Gemini' : aiReport.model}
                {' · '}
                {new Date(aiReport.generated_at).toLocaleDateString('ko-KR', {
                  year: 'numeric', month: 'long', day: 'numeric'
                })}
              </p>
            </div>
            <div className="hidden md:flex items-center gap-6 text-[11px] text-[#94A3B8]">
              <div className="text-center">
                <p className="font-semibold text-[#334155] text-[13px]">
                  {aiReport.data_coverage.annual_years?.length || 0}
                </p>
                <p>개년 데이터</p>
              </div>
              <div className="w-px h-8 bg-[#E2E8F0]" />
              <div className="text-center">
                <p className="font-semibold text-[#334155] text-[13px]">
                  {aiReport.data_coverage.disclosure_count}
                </p>
                <p>건 공시</p>
              </div>
              <div className="w-px h-8 bg-[#E2E8F0]" />
              <div className="text-center">
                <p className="font-semibold text-[#334155] text-[13px]">
                  {aiReport.data_coverage.quarterly_periods?.length || 0}
                </p>
                <p>개 분기</p>
              </div>
            </div>
          </div>

          {/* 리포트 본문 */}
          <div className="px-10 py-8 max-w-4xl">
            <MarkdownRenderer text={aiReport.report} />
          </div>

          {/* 출처 푸터 */}
          <div className="bg-[#F7F9FC] border-t border-[#E2E8F0] px-8 py-4">
            <SourceBadge
              provider={aiReport._source.provider}
              retrievedAt={aiReport._source.generated_at}
            />
          </div>
        </div>
      )}

      {/* ── Tab: 재무 분석 ── */}
      {activeTab === 'financial' && financial && (
        <div className="space-y-5">

          {/* KPI 카드 행 1 */}
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

          {/* KPI 카드 행 2 */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <MetricCard label="부채비율"  value={financial.ratios?.debt_ratio_pct}  unit="%" />
            <MetricCard label="유동비율"  value={financial.ratios?.current_ratio}    unit="배" />
            <MetricCard label="ROE"       value={financial.ratios?.roe_pct}          unit="%" />
            <MetricCard label="ROA"       value={financial.ratios?.roa_pct}          unit="%" />
          </div>

          {/* 차트 2×2 */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <ChartCard title="매출 · 이익 추이" unit="억원">
              <RevenueChart financial={financial} />
            </ChartCard>
            <ChartCard title="이익률 추이" unit="%">
              <MarginChart financial={financial} />
            </ChartCard>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <ChartCard title="재무상태" unit="억원">
              <BalanceChart financial={financial} />
            </ChartCard>
            <ChartCard title="현금흐름" unit="억원">
              <CashFlowChart financial={financial} />
            </ChartCard>
          </div>

          {/* 차트 범례 설명 */}
          <div className="flex items-center gap-6 px-1">
            {[
              { color: '#1F3864', label: '주 계열' },
              { color: '#2E75B6', label: '보조 계열' },
              { color: '#8FAADC', label: '제3 계열' },
            ].map(({ color, label }) => (
              <div key={label} className="flex items-center gap-1.5">
                <span className="w-3 h-2 rounded-sm" style={{ background: color }} />
                <span className="text-[11px] text-[#94A3B8]">{label}</span>
              </div>
            ))}
          </div>

          {financial._source && (
            <div className="bg-[#F7F9FC] border border-[#E2E8F0] rounded p-4">
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
        <div className="bg-white border border-[#E2E8F0] rounded-xl overflow-hidden">
          {/* 헤더 */}
          <div className="bg-[#F7F9FC] border-b border-[#E2E8F0] px-6 py-4 flex items-center justify-between">
            <div>
              <p className="text-[11px] font-semibold text-[#64748B] uppercase tracking-widest">공시 동향</p>
              <p className="text-[12px] text-[#94A3B8] mt-0.5">최근 6개월 DART 공시 목록</p>
            </div>
            <span className="text-[12px] font-semibold text-[#0C2340] bg-[#DAE3F3] px-3 py-1 rounded">
              총 {disclosures.list?.length || 0}건
            </span>
          </div>

          {/* 리스트 */}
          <div className="divide-y divide-[#F1F5F9]">
            {(disclosureExpanded
              ? disclosures.list
              : disclosures.list?.slice(0, 8)
            )?.map((d, idx) => (
              <div
                key={d.rcept_no}
                className="flex items-center justify-between gap-4 px-6 py-4 hover:bg-[#F7F9FC] transition-colors"
              >
                <div className="flex items-start gap-3 flex-1 min-w-0">
                  <span className="text-[11px] font-semibold text-[#94A3B8] w-5 flex-shrink-0 mt-0.5">
                    {idx + 1}
                  </span>
                  <div className="min-w-0 flex-1">
                    <p className="text-[13px] font-medium text-[#0F172A] leading-snug truncate">
                      {d.report_nm}
                    </p>
                    <div className="flex items-center gap-3 mt-1 text-[11px] text-[#94A3B8]">
                      <span className="flex items-center gap-1">
                        <Calendar className="w-3 h-3" />
                        {d.rcept_dt}
                      </span>
                      <span>{d.flr_nm}</span>
                      {d.rm && (
                        <span className="bg-[#FEF3C7] text-[#92400E] px-1.5 py-0.5 rounded text-[10px] font-medium">
                          {d.rm}
                        </span>
                      )}
                    </div>
                  </div>
                </div>
                <a
                  href={d._source_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-1 px-3 py-1.5 text-[11px] font-medium text-[#2E75B6] border border-[#2E75B6] rounded hover:bg-[#2E75B6] hover:text-white transition-all flex-shrink-0"
                >
                  공시 보기
                  <ExternalLink className="w-3 h-3" />
                </a>
              </div>
            ))}
          </div>

          {(disclosures.list?.length || 0) > 8 && (
            <div className="border-t border-[#E2E8F0]">
              <button
                onClick={() => setDisclosureExpanded(!disclosureExpanded)}
                className="w-full py-3 text-[12px] text-[#64748B] hover:text-[#0C2340] hover:bg-[#F7F9FC] flex items-center justify-center gap-1.5 transition-all"
              >
                {disclosureExpanded ? (
                  <>접기 <ChevronUp className="w-3.5 h-3.5" /></>
                ) : (
                  <>나머지 {(disclosures.list?.length || 0) - 8}건 더 보기 <ChevronDown className="w-3.5 h-3.5" /></>
                )}
              </button>
            </div>
          )}

          {disclosures._source && (
            <div className="bg-[#F7F9FC] border-t border-[#E2E8F0] px-6 py-4">
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
        <div className="bg-white border border-[#E2E8F0] rounded-xl overflow-hidden">
          <div className="bg-[#F7F9FC] border-b border-[#E2E8F0] px-6 py-4">
            <p className="text-[11px] font-semibold text-[#64748B] uppercase tracking-widest">기업 기본 정보</p>
            <p className="text-[12px] text-[#94A3B8] mt-0.5">DART 공시 기준 법인 정보</p>
          </div>

          <div className="p-6 grid grid-cols-1 md:grid-cols-2 gap-3">
            {[
              { icon: Building2, label: '기업코드',  value: companyInfo.corp_code },
              { icon: Calendar,  label: '설립일',    value: companyInfo.est_dt },
              { icon: Calendar,  label: '상장일',    value: companyInfo.listing_dt },
              { icon: Calendar,  label: '결산월',    value: companyInfo.acc_mt ? `${companyInfo.acc_mt}월` : undefined },
              { icon: Globe,     label: '홈페이지',  value: companyInfo.hm_url, href: companyInfo.hm_url },
              { icon: Phone,     label: '전화번호',  value: companyInfo.phn_no },
              { icon: MapPin,    label: '주소',      value: companyInfo.adres, wide: true },
            ]
              .filter((f) => f.value)
              .map(({ icon: Icon, label, value, href, wide }) => (
                <div
                  key={label}
                  className={`flex items-start gap-3 p-4 border border-[#E2E8F0] ${wide ? 'md:col-span-2' : ''}`}
                >
                  <div className="w-7 h-7 bg-[#F7F9FC] border border-[#E2E8F0] flex items-center justify-center flex-shrink-0">
                    <Icon className="w-3.5 h-3.5 text-[#64748B]" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="text-[10px] font-semibold text-[#94A3B8] uppercase tracking-wider mb-0.5">{label}</p>
                    {href ? (
                      <a href={href} target="_blank" rel="noopener noreferrer"
                        className="text-[#2E75B6] hover:underline text-[13px] font-medium truncate block">
                        {value}
                      </a>
                    ) : (
                      <p className="text-[13px] font-medium text-[#0F172A]">{value}</p>
                    )}
                  </div>
                </div>
              ))}
          </div>

          <div className="bg-[#F7F9FC] border-t border-[#E2E8F0] px-6 py-4">
            <SourceBadge
              provider={companyInfo._source.provider}
              url={companyInfo._source.url}
              retrievedAt={companyInfo._source.retrieved_at}
            />
          </div>
        </div>
      )}

      {/* 데이터 없음 */}
      {!comprehensive && !aiReport && (
        <div className="bg-[#FEF2F2] border border-[#FECACA] rounded-xl p-6 flex items-start gap-3">
          <AlertCircle className="w-4 h-4 text-[#DC2626] flex-shrink-0 mt-0.5" />
          <div>
            <h3 className="font-semibold text-[#991B1B] text-[13px] mb-1">분석 데이터를 불러오지 못했습니다</h3>
            <p className="text-[12px] text-[#DC2626]">잠시 후 다시 시도해주세요.</p>
          </div>
        </div>
      )}
    </div>
  );
}
