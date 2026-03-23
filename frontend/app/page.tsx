'use client';

import React, { useState } from 'react';
import {
  TrendingUp, Database, Shield, Brain,
  Calendar, BarChart3, FileText, Info, ChevronRight, X, Layers,
} from 'lucide-react';
import CompanySearch from '@/components/CompanySearch';
import LoadingProgress from '@/components/LoadingProgress';
import AnalysisReport from '@/components/AnalysisReport';
import ModuleSelector from '@/components/ModuleSelector';
import {
  CompanySearchResult,
  AnalysisOptions,
  ComprehensiveAnalysis,
  AIReportData,
  analysisAPI,
} from '@/lib/api';

// ──────────────────────────────────────────────────────────────────────
// 상수
// ──────────────────────────────────────────────────────────────────────
type Step = 'search' | 'modules' | 'loading' | 'results';

const currentYear = new Date().getFullYear();
const YEAR_OPTIONS = Array.from({ length: 10 }, (_, i) => String(currentYear - i));
const QTR_OPTIONS = [
  { value: 1, label: 'Q1', full: 'Q1 (1~3월)' },
  { value: 2, label: 'Q2', full: 'Q2 / 반기 (1~6월)' },
  { value: 3, label: 'Q3', full: 'Q3 (1~9월)' },
  { value: 4, label: 'Q4', full: 'Q4 / 연간 (1~12월)' },
];

function calcPeriodSummary(sy: string, sq: number, ey: string, eq: number) {
  const s = Number(sy), e = Number(ey);
  if (s > e || (s === e && sq > eq)) return { years: 0, quarters: 0, valid: false };
  const years = e - s + 1;
  let quarters = 0;
  for (let y = s; y <= e; y++) {
    const minQ = y === s ? sq : 1;
    const maxQ = y === e ? eq : 4;
    quarters += maxQ - minQ + 1;
  }
  return { years, quarters, valid: true };
}

// ──────────────────────────────────────────────────────────────────────
// 단계 표시
// ──────────────────────────────────────────────────────────────────────
const STEP_LABELS: Record<Step, string> = {
  search:  '기업 검색 · 기간 설정',
  modules: '모듈별 분석',
  loading: '분석 중',
  results: '결과',
};

function StepIndicator({ current }: { current: Step }) {
  const steps: Step[] = ['search', 'loading', 'results'];
  const currentIdx = steps.indexOf(current);
  return (
    <div className="flex items-center justify-center gap-0 mb-8">
      {steps.map((step, idx) => {
        const isDone = idx < currentIdx;
        const isActive = idx === currentIdx;
        return (
          <React.Fragment key={step}>
            <div className="flex flex-col items-center">
              <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold transition-all ${
                isDone ? 'bg-emerald-500 text-white'
                  : isActive ? 'bg-[#0C2340] text-white shadow-lg'
                  : 'bg-gray-200 text-gray-400'
              }`}>
                {isDone ? '✓' : idx + 1}
              </div>
              <span className={`mt-1 text-xs font-medium ${
                isActive ? 'text-[#0C2340]' : isDone ? 'text-emerald-600' : 'text-gray-400'
              }`}>
                {STEP_LABELS[step]}
              </span>
            </div>
            {idx < steps.length - 1 && (
              <div className={`w-16 h-0.5 mx-1 mb-5 transition-all ${idx < currentIdx ? 'bg-emerald-400' : 'bg-gray-200'}`} />
            )}
          </React.Fragment>
        );
      })}
    </div>
  );
}

// ──────────────────────────────────────────────────────────────────────
// 기간 + 모듈 인라인 패널 (기업 선택 후 메인화면에서 바로 표시)
// ──────────────────────────────────────────────────────────────────────
function PeriodPanel({
  company,
  options,
  onChange,
  onStart,
  onModules,
  onClear,
}: {
  company: CompanySearchResult;
  options: AnalysisOptions;
  onChange: (o: AnalysisOptions) => void;
  onStart: () => void;
  onModules: () => void;
  onClear: () => void;
}) {
  const summary = calcPeriodSummary(options.startYear, options.startQtr, options.endYear, options.endQtr);
  const isValid = summary.valid;

  const MODULE_OPTIONS = [
    { id: 'includeAI',          icon: Brain,    label: 'AI 리포트',  color: 'navy' },
    { id: 'includeFinancial',   icon: BarChart3, label: '재무 분석', color: 'blue' },
    { id: 'includeDisclosures', icon: FileText,  label: '공시 동향', color: 'slate' },
  ] as const;

  const activeStyle = (color: string) =>
    color === 'navy'  ? 'bg-[#0C2340] text-white border-[#0C2340]' :
    color === 'blue'  ? 'bg-[#2E75B6] text-white border-[#2E75B6]' :
                        'bg-[#475569] text-white border-[#475569]';

  const select = 'border border-[#CBD5E1] bg-white text-[#0C2340] text-[13px] font-semibold px-3 py-2 focus:border-[#2E75B6] focus:outline-none';

  return (
    <div className="mt-4 bg-white border border-[#E2E8F0] border-t-4 border-t-[#0C2340] p-6 animate-in fade-in slide-in-from-top-2 duration-300">

      {/* 선택된 기업 헤더 */}
      <div className="flex items-center justify-between mb-5 pb-4 border-b border-[#E2E8F0]">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 bg-[#0C2340] flex items-center justify-center flex-shrink-0">
            <TrendingUp className="w-4 h-4 text-white" />
          </div>
          <div>
            <p className="font-bold text-[#0C2340] text-[15px]">{company.corp_name}</p>
            <p className="text-[11px] text-[#94A3B8] tracking-wide">
              기업코드 {company.corp_code}
              {company.stock_code && <> · 종목코드 {company.stock_code}</>}
            </p>
          </div>
        </div>
        <button onClick={onClear} className="text-[#94A3B8] hover:text-[#475569] transition-colors" title="선택 취소">
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* 분석 기간 */}
      <div className="mb-5">
        <p className="text-[11px] font-bold uppercase tracking-widest text-[#64748B] mb-3 flex items-center gap-1.5">
          <Calendar className="w-3.5 h-3.5" /> 분석 기간
        </p>

        <div className="flex flex-wrap items-end gap-2">
          {/* 시작 */}
          <div>
            <p className="text-[10px] text-[#94A3B8] mb-1 uppercase tracking-widest">시작</p>
            <div className="flex gap-1.5">
              <select value={options.startYear} onChange={e => onChange({ ...options, startYear: e.target.value })} className={select}>
                {YEAR_OPTIONS.map(y => <option key={y} value={y}>{y}년</option>)}
              </select>
              <select value={options.startQtr} onChange={e => onChange({ ...options, startQtr: Number(e.target.value) })} className={select}>
                {QTR_OPTIONS.map(q => <option key={q.value} value={q.value}>{q.full}</option>)}
              </select>
            </div>
          </div>

          <span className="text-[#94A3B8] font-bold pb-2">~</span>

          {/* 종료 */}
          <div>
            <p className="text-[10px] text-[#94A3B8] mb-1 uppercase tracking-widest">종료</p>
            <div className="flex gap-1.5">
              <select value={options.endYear} onChange={e => onChange({ ...options, endYear: e.target.value })} className={select}>
                {YEAR_OPTIONS.map(y => <option key={y} value={y}>{y}년</option>)}
              </select>
              <select value={options.endQtr} onChange={e => onChange({ ...options, endQtr: Number(e.target.value) })} className={select}>
                {QTR_OPTIONS.map(q => <option key={q.value} value={q.value}>{q.full}</option>)}
              </select>
            </div>
          </div>

          {/* 요약 뱃지 */}
          {summary.valid && (
            <div className="flex items-center gap-1.5 text-[11px] bg-[#EBF2FA] text-[#1F3864] px-3 py-2 border border-[#C9D8EC] mb-0.5">
              <Info className="w-3 h-3 flex-shrink-0" />
              <span>
                <strong>{summary.years}개년</strong> · <strong>{summary.quarters}분기</strong>
                &nbsp;({options.startYear}/{QTR_OPTIONS.find(q=>q.value===options.startQtr)?.label}
                &nbsp;~&nbsp;
                {options.endYear}/{QTR_OPTIONS.find(q=>q.value===options.endQtr)?.label})
              </span>
            </div>
          )}
          {!summary.valid && (
            <p className="text-[11px] text-red-500 pb-2">종료 시점이 시작보다 앞에 있습니다</p>
          )}
        </div>
      </div>

      {/* 분석 방식 선택 버튼 */}
      <div className="grid grid-cols-2 gap-3">
        {/* 모듈 분석 (추천) */}
        <button
          onClick={onModules}
          disabled={!isValid}
          className={`py-4 text-[13px] font-bold flex flex-col items-center gap-1.5 border-2 transition-all ${
            isValid
              ? 'border-[#0C2340] bg-[#0C2340] text-white hover:bg-[#1F3864]'
              : 'border-[#E2E8F0] text-[#94A3B8] cursor-not-allowed bg-[#F7F9FC]'
          }`}
        >
          <Layers className="w-5 h-5" />
          <span>모듈별 분석</span>
          <span className="text-[10px] font-normal opacity-75">10개 섹션 · 선택 실행 ★추천</span>
        </button>

        {/* 종합 분석 */}
        <button
          onClick={onStart}
          disabled={!isValid}
          className={`py-4 text-[13px] font-bold flex flex-col items-center gap-1.5 border-2 transition-all ${
            isValid
              ? 'border-[#2E75B6] text-[#2E75B6] hover:bg-[#EBF2FA]'
              : 'border-[#E2E8F0] text-[#94A3B8] cursor-not-allowed bg-[#F7F9FC]'
          }`}
        >
          <Brain className="w-5 h-5" />
          <span>종합 분석</span>
          <span className="text-[10px] font-normal opacity-75">전체 통합 · 1회 실행</span>
        </button>
      </div>
    </div>
  );
}

// ──────────────────────────────────────────────────────────────────────
// 메인 페이지
// ──────────────────────────────────────────────────────────────────────
export default function Home() {
  const [step, setStep] = useState<Step>('search');
  const [selectedCompany, setSelectedCompany] = useState<CompanySearchResult | null>(null);
  const [options, setOptions] = useState<AnalysisOptions>({
    startYear: String(currentYear - 3),
    startQtr: 1,
    endYear: String(currentYear - 1),
    endQtr: 4,
    includeAI: true,
    includeFinancial: true,
    includeDisclosures: true,
  });
  const [loadingDone, setLoadingDone] = useState(false);
  const [comprehensive, setComprehensive] = useState<ComprehensiveAnalysis | null>(null);
  const [aiReport, setAIReport] = useState<AIReportData | null>(null);
  const [error, setError] = useState('');

  const handleSelectCompany = (result: CompanySearchResult) => {
    setSelectedCompany(result);
    // step은 그대로 'search' 유지 — 기간 패널이 검색 화면 내에서 펼쳐짐
  };

  const handleClearCompany = () => setSelectedCompany(null);

  const handleGoModules = () => {
    if (!selectedCompany) return;
    setStep('modules');
  };

  const handleStartAnalysis = async () => {
    if (!selectedCompany) return;
    setStep('loading');
    setLoadingDone(false);
    setComprehensive(null);
    setAIReport(null);
    setError('');

    try {
      if (options.includeFinancial || options.includeDisclosures) {
        try {
          const comp = await analysisAPI.getComprehensive(
            selectedCompany.corp_code,
            options.includeFinancial,
            options.includeDisclosures,
            true,
            options.endYear,
          );
          setComprehensive(comp);
        } catch {
          // comprehensive 실패 — 개별 섹션 에러는 UI에서 처리
        }
      }
      if (options.includeAI) {
        try {
          const ai = await analysisAPI.getAIReport(selectedCompany.corp_code, {
            startYear: options.startYear,
            startQtr:  options.startQtr,
            endYear:   options.endYear,
            endQtr:    options.endQtr,
          });
          setAIReport(ai);
        } catch {
          // AI 리포트 실패 — 결과 화면에서 없음으로 표시
        }
      }
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : '알 수 없는 오류가 발생했습니다.';
      setError(msg);
    } finally {
      setLoadingDone(true);
      setTimeout(() => setStep('results'), 800);
    }
  };

  const handleReset = () => {
    setStep('search');
    setSelectedCompany(null);
    setComprehensive(null);
    setAIReport(null);
    setLoadingDone(false);
    setError('');
  };

  return (
    <div className="min-h-screen">
      {/* 헤더 */}
      <header className="bg-[#0C2340] border-b border-[#1F3864] sticky top-0 z-10">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-3.5">
          <div className="flex items-center justify-between">
            <button onClick={handleReset} className="flex items-center gap-3 hover:opacity-80 transition-opacity">
              <img src="/pathway-logo.png" alt="PATHWAY Partners" className="h-8 w-auto brightness-0 invert opacity-90" />
              <div className="w-px h-7 bg-white/20" />
              <div className="text-left">
                <h1 className="text-[14px] font-bold text-white leading-tight tracking-tight">패스웨이 기업분석 플랫폼</h1>
                <p className="text-[10px] text-white/50 font-medium tracking-widest">DART·KRX Analysis Platform</p>
              </div>
            </button>
            {selectedCompany && step === 'search' && (
              <div className="hidden md:flex items-center gap-2 text-[12px] text-white/70 bg-white/10 border border-white/20 px-3 py-1.5">
                <span className="font-semibold text-white">{selectedCompany.corp_name}</span>
                {selectedCompany.stock_code && <span className="text-white/40">{selectedCompany.stock_code}</span>}
                <span className="text-white/30">|</span>
                <span>
                  {options.startYear}/{QTR_OPTIONS.find(q=>q.value===options.startQtr)?.label}
                  &nbsp;~&nbsp;
                  {options.endYear}/{QTR_OPTIONS.find(q=>q.value===options.endQtr)?.label}
                </span>
              </div>
            )}
          </div>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8">

        {/* ── STEP 1: 검색 + 기간 설정 ── */}
        {step === 'search' && (
          <>
            {/* 히어로 (기업 미선택 시만 표시) */}
            {!selectedCompany && (
              <>
                <div className="mb-10">
                  <div className="inline-flex items-center gap-2 bg-[#F7F9FC] border border-[#DAE3F3] text-[#1F3864] px-3 py-1 text-[12px] font-semibold uppercase tracking-wider mb-5">
                    <Database className="w-3.5 h-3.5" />
                    DART · KRX 공식 데이터 기반
                  </div>
                  <h2 className="text-[36px] font-bold text-[#0C2340] mb-3 leading-tight tracking-tight">
                    기업 분석의 새로운 기준
                  </h2>
                  <p className="text-[15px] text-[#475569] max-w-2xl leading-relaxed">
                    금융감독원 DART와 한국거래소 KRX 데이터를 AI가 분석하여
                    투자자 관점의 심층 리포트를 제공합니다
                  </p>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-10">
                  {[
                    { icon: Database, num: '01', title: '연·분기 기간 설정', desc: '분석 시작/종료 연도와 분기를 자유롭게 설정하여 원하는 기간만 수집' },
                    { icon: Shield,   num: '02', title: '지배구조 분석',     desc: '최대주주·임원·계열회사 구조를 DART 공시 기반으로 파악' },
                    { icon: Brain,    num: '03', title: 'AI 종합 리포트',   desc: '수집된 모든 데이터를 AI가 종합하여 6개 섹션 심층 분석' },
                  ].map(({ icon: Icon, num, title, desc }) => (
                    <div key={title} className="bg-white border border-[#E2E8F0] border-t-2 border-t-[#0C2340] p-6">
                      <div className="flex items-start justify-between mb-4">
                        <div className="w-10 h-10 bg-[#F7F9FC] border border-[#E2E8F0] flex items-center justify-center">
                          <Icon className="w-5 h-5 text-[#1F3864]" />
                        </div>
                        <span className="text-[11px] font-bold text-[#CBD5E1] tracking-widest">{num}</span>
                      </div>
                      <h3 className="font-semibold text-[#0F172A] text-[14px] mb-1.5">{title}</h3>
                      <p className="text-[13px] text-[#64748B] leading-relaxed">{desc}</p>
                    </div>
                  ))}
                </div>
              </>
            )}

            {/* 검색창 */}
            <div className="bg-white border border-[#E2E8F0] p-8">
              <h3 className="text-[13px] font-semibold text-[#64748B] uppercase tracking-widest mb-5 flex items-center gap-2">
                <TrendingUp className="w-4 h-4 text-[#1F3864]" />
                {selectedCompany ? '다른 기업 검색' : '분석할 기업을 검색하세요'}
              </h3>
              <CompanySearch onSelectCompany={(code, name, result) => handleSelectCompany(result)} />

              {/* 기간 + 모듈 패널 — 기업 선택 후 인라인 표시 */}
              {selectedCompany && (
                <PeriodPanel
                  company={selectedCompany}
                  options={options}
                  onChange={setOptions}
                  onStart={handleStartAnalysis}
                  onModules={handleGoModules}
                  onClear={handleClearCompany}
                />
              )}
            </div>

            {/* 사용 안내 (기업 미선택 시만) */}
            {!selectedCompany && (
              <div className="mt-5 bg-[#F7F9FC] border border-[#E2E8F0] p-5 text-[13px]">
                <p className="font-semibold text-[#334155] mb-2 uppercase tracking-wide text-[11px]">사용 안내</p>
                <ul className="space-y-1.5 text-[#64748B]">
                  <li className="flex items-start gap-2">
                    <span className="w-1.5 h-1.5 bg-[#1F3864] flex-shrink-0 mt-[6px]" />
                    기업명 또는 종목코드로 검색 → 기업 선택 → 분석 기간·모듈 설정 → 분석 시작
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="w-1.5 h-1.5 bg-[#1F3864] flex-shrink-0 mt-[6px]" />
                    AI 종합 리포트는 사업보고서 원문·재무·공시·지배구조를 심층 분석합니다 (약 30~90초 소요)
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="w-1.5 h-1.5 bg-[#1F3864] flex-shrink-0 mt-[6px]" />
                    본 플랫폼은 정보 제공 목적이며 투자 자문을 대체하지 않습니다
                  </li>
                </ul>
              </div>
            )}
          </>
        )}

        {/* ── STEP 모듈: 모듈별 분석 ── */}
        {step === 'modules' && selectedCompany && (
          <ModuleSelector
            company={selectedCompany}
            endYear={options.endYear}
            onBack={handleReset}
          />
        )}

        {/* ── STEP 2: 종합 분석 로딩 ── */}
        {step === 'loading' && selectedCompany && (
          <>
            <StepIndicator current="loading" />
            <LoadingProgress
              options={options}
              corpName={selectedCompany.corp_name}
              isDone={loadingDone}
            />
          </>
        )}

        {/* ── STEP 3: 결과 ── */}
        {step === 'results' && (
          <>
            {error ? (
              <div className="bg-red-50 border border-red-200 p-6 text-red-700">
                <p className="font-semibold mb-1">오류 발생</p>
                <p className="text-sm">{error}</p>
                <button onClick={handleReset} className="mt-4 px-4 py-2 bg-[#0C2340] text-white text-sm hover:bg-[#1F3864] transition-colors">
                  처음부터 다시
                </button>
              </div>
            ) : (
              <AnalysisReport
                options={options}
                comprehensive={comprehensive}
                aiReport={aiReport}
                onBack={handleReset}
              />
            )}
          </>
        )}
      </main>

      {/* 푸터 */}
      <footer className="bg-[#0C2340] border-t border-[#1F3864] mt-20">
        <div className="max-w-6xl mx-auto px-4 py-5 flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-4">
            <img src="/pathway-logo.png" alt="PATHWAY Partners" className="h-7 w-auto opacity-80 brightness-0 invert" />
            <span className="w-px h-5 bg-white/20" />
            <p className="text-[11px] text-white/50">Copyright ⓒ PATHWAY Partners, co, Ltd. All rights reserved.</p>
          </div>
          <div className="flex items-center gap-4 text-[11px] text-white/30">
            <span>데이터 출처: 금융감독원 DART · 한국거래소 KRX · 네이버 금융</span>
            <span className="w-px h-3 bg-white/20" />
            <span>투자 자문을 대체하지 않습니다</span>
          </div>
        </div>
      </footer>
    </div>
  );
}
