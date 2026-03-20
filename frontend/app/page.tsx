'use client';

import React, { useState } from 'react';
import { TrendingUp, Database, Shield, Brain, ChevronRight } from 'lucide-react';
import CompanySearch from '@/components/CompanySearch';
import AnalysisConfig from '@/components/AnalysisConfig';
import LoadingProgress from '@/components/LoadingProgress';
import AnalysisReport from '@/components/AnalysisReport';
import {
  CompanySearchResult,
  AnalysisOptions,
  ComprehensiveAnalysis,
  AIReportData,
  analysisAPI,
} from '@/lib/api';

// ──────────────────────────────────────────────────────────────────────
// 단계 정의
// ──────────────────────────────────────────────────────────────────────
type Step = 'search' | 'config' | 'loading' | 'results';

const STEP_LABELS: Record<Step, string> = {
  search: '기업 검색',
  config: '분석 조건',
  loading: '분석 중',
  results: '결과',
};

function StepIndicator({ current }: { current: Step }) {
  const steps: Step[] = ['search', 'config', 'loading', 'results'];
  const currentIdx = steps.indexOf(current);

  return (
    <div className="flex items-center justify-center gap-0 mb-8">
      {steps.map((step, idx) => {
        const isDone = idx < currentIdx;
        const isActive = idx === currentIdx;
        return (
          <React.Fragment key={step}>
            <div className="flex flex-col items-center">
              <div
                className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold transition-all ${
                  isDone
                    ? 'bg-emerald-500 text-white'
                    : isActive
                    ? 'bg-blue-600 text-white shadow-lg shadow-blue-200'
                    : 'bg-gray-200 text-gray-400'
                }`}
              >
                {isDone ? '✓' : idx + 1}
              </div>
              <span
                className={`mt-1 text-xs font-medium ${
                  isActive ? 'text-blue-600' : isDone ? 'text-emerald-600' : 'text-gray-400'
                }`}
              >
                {STEP_LABELS[step]}
              </span>
            </div>
            {idx < steps.length - 1 && (
              <div
                className={`w-16 h-0.5 mx-1 mb-5 transition-all ${
                  idx < currentIdx ? 'bg-emerald-400' : 'bg-gray-200'
                }`}
              />
            )}
          </React.Fragment>
        );
      })}
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
    bsnsYear: String(new Date().getFullYear() - 1),
    includeAI: true,
    includeFinancial: true,
    includeDisclosures: true,
  });
  const [loadingDone, setLoadingDone] = useState(false);
  const [comprehensive, setComprehensive] = useState<ComprehensiveAnalysis | null>(null);
  const [aiReport, setAIReport] = useState<AIReportData | null>(null);
  const [error, setError] = useState('');

  // ── 핸들러 ──────────────────────────────────────────────────────────

  const handleSelectCompany = (result: CompanySearchResult) => {
    setSelectedCompany(result);
    setStep('config');
  };

  const handleStartAnalysis = async () => {
    if (!selectedCompany) return;
    setStep('loading');
    setLoadingDone(false);
    setComprehensive(null);
    setAIReport(null);
    setError('');

    try {
      // 병렬 API 호출
      const promises: [
        Promise<ComprehensiveAnalysis | null>,
        Promise<AIReportData | null>,
      ] = [
        options.includeFinancial || options.includeDisclosures
          ? analysisAPI.getComprehensive(
              selectedCompany.corp_code,
              options.includeFinancial,
              options.includeDisclosures,
              true,
            )
          : Promise.resolve(null),

        options.includeAI
          ? analysisAPI.getAIReport(selectedCompany.corp_code, options.bsnsYear)
          : Promise.resolve(null),
      ];

      const [compResult, aiResult] = await Promise.allSettled(promises);

      if (compResult.status === 'fulfilled') setComprehensive(compResult.value);
      if (aiResult.status === 'fulfilled') setAIReport(aiResult.value);

      // 둘 다 실패한 경우
      if (compResult.status === 'rejected' && aiResult.status === 'rejected') {
        setError('분석 데이터를 불러오지 못했습니다. 잠시 후 다시 시도해주세요.');
      }
    } catch (e: any) {
      setError(e.message || '알 수 없는 오류가 발생했습니다.');
    } finally {
      setLoadingDone(true);
      // 짧은 딜레이 후 결과 페이지 이동 (로딩 완료 애니메이션 표시)
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

  // ── 렌더 ────────────────────────────────────────────────────────────
  return (
    <div className="min-h-screen">
      {/* 헤더 */}
      <header className="bg-white shadow-sm border-b border-gray-200 sticky top-0 z-10">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <button
              onClick={handleReset}
              className="flex items-center gap-3 hover:opacity-80 transition-opacity"
            >
              <div className="w-10 h-10 bg-gradient-to-br from-blue-600 to-indigo-600 rounded-xl flex items-center justify-center">
                <TrendingUp className="w-5 h-5 text-white" />
              </div>
              <div className="text-left">
                <h1 className="text-lg font-bold text-gray-900 leading-tight">
                  PATHWAY DART·KRX
                </h1>
                <p className="text-xs text-gray-500">기업분석 플랫폼</p>
              </div>
            </button>

            {step !== 'search' && selectedCompany && (
              <div className="hidden md:flex items-center gap-2 text-sm text-gray-600 bg-gray-100 px-4 py-2 rounded-xl">
                <span className="font-semibold text-gray-900">{selectedCompany.corp_name}</span>
                {selectedCompany.stock_code && (
                  <span className="text-gray-400">{selectedCompany.stock_code}</span>
                )}
                <span className="text-gray-400">·</span>
                <span>{options.bsnsYear}년 기준</span>
              </div>
            )}
          </div>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* ── STEP 1: 검색 ── */}
        {step === 'search' && (
          <>
            {/* 히어로 */}
            <div className="text-center mb-10">
              <div className="inline-flex items-center gap-2 bg-blue-50 border border-blue-200 text-blue-700 px-4 py-1.5 rounded-full text-sm font-medium mb-4">
                <Database className="w-4 h-4" />
                DART · KRX 공식 데이터 기반
              </div>
              <h2 className="text-4xl font-bold text-gray-900 mb-3">
                기업 분석의 새로운 기준
              </h2>
              <p className="text-lg text-gray-600 max-w-2xl mx-auto">
                금융감독원 DART와 한국거래소 KRX 데이터를 AI가 분석하여
                투자자 관점의 심층 리포트를 제공합니다
              </p>
            </div>

            {/* 특징 카드 */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-5 mb-10">
              {[
                {
                  icon: Database,
                  color: 'blue',
                  title: '3개년 + 분기 데이터',
                  desc: '연간 3개년 재무제표와 분기별 실적을 자동 수집',
                },
                {
                  icon: Shield,
                  color: 'green',
                  title: '지배구조 분석',
                  desc: '최대주주·임원·계열회사 구조를 DART 공시 기반으로 파악',
                },
                {
                  icon: Brain,
                  color: 'purple',
                  title: 'Claude AI 종합 리포트',
                  desc: '수집된 모든 데이터를 AI가 종합하여 6개 섹션 심층 분석',
                },
              ].map(({ icon: Icon, color, title, desc }) => (
                <div
                  key={title}
                  className={`bg-white rounded-2xl shadow-sm border border-gray-200 p-6 border-t-4 ${
                    color === 'blue' ? 'border-t-blue-500' : color === 'green' ? 'border-t-emerald-500' : 'border-t-purple-500'
                  }`}
                >
                  <div
                    className={`w-11 h-11 rounded-xl flex items-center justify-center mb-4 ${
                      color === 'blue' ? 'bg-blue-100' : color === 'green' ? 'bg-emerald-100' : 'bg-purple-100'
                    }`}
                  >
                    <Icon
                      className={`w-6 h-6 ${
                        color === 'blue' ? 'text-blue-600' : color === 'green' ? 'text-emerald-600' : 'text-purple-600'
                      }`}
                    />
                  </div>
                  <h3 className="font-semibold text-gray-900 mb-1">{title}</h3>
                  <p className="text-sm text-gray-500">{desc}</p>
                </div>
              ))}
            </div>

            {/* 검색창 */}
            <div className="bg-white rounded-2xl shadow-lg border border-gray-200 p-8">
              <h3 className="text-lg font-semibold text-gray-900 mb-5 flex items-center gap-2">
                <TrendingUp className="w-5 h-5 text-blue-600" />
                분석할 기업을 검색하세요
              </h3>
              <CompanySearch onSelectCompany={(code, name, result) => handleSelectCompany(result)} />
            </div>

            {/* 안내 */}
            <div className="mt-6 bg-blue-50 border border-blue-200 rounded-xl p-5 text-sm text-blue-800">
              <p className="font-semibold mb-1">사용 안내</p>
              <ul className="space-y-1 text-blue-700">
                <li>• 기업명 또는 종목코드로 검색 → 기업 선택 → 분석 조건 설정 → 리포트 확인</li>
                <li>• AI 종합 리포트는 Claude AI가 3개년 재무·공시·지배구조를 심층 분석 (약 30~60초 소요)</li>
                <li>• 본 플랫폼은 정보 제공 목적이며 투자 자문을 대체하지 않습니다</li>
              </ul>
            </div>
          </>
        )}

        {/* ── STEP 2: 분석 조건 설정 ── */}
        {step === 'config' && selectedCompany && (
          <>
            <StepIndicator current="config" />
            <AnalysisConfig
              company={selectedCompany}
              options={options}
              onChange={setOptions}
              onStart={handleStartAnalysis}
              onBack={handleReset}
            />
          </>
        )}

        {/* ── STEP 3: 로딩 ── */}
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

        {/* ── STEP 4: 결과 ── */}
        {step === 'results' && (
          <>
            {error ? (
              <div className="bg-red-50 border border-red-200 rounded-2xl p-6 text-red-700">
                <p className="font-semibold mb-1">오류 발생</p>
                <p className="text-sm">{error}</p>
                <button
                  onClick={handleReset}
                  className="mt-4 px-4 py-2 bg-red-600 text-white rounded-lg text-sm hover:bg-red-700 transition-colors"
                >
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
      <footer className="bg-slate-900 text-white mt-20">
        <div className="max-w-6xl mx-auto px-4 py-6 text-center">
          <p className="text-gray-400 text-sm">
            © 2025 PATHWAY DART·KRX 기업분석 플랫폼 — 데이터 출처: 금융감독원 DART, 한국거래소 KRX
          </p>
          <p className="text-gray-500 text-xs mt-1">
            본 플랫폼의 정보는 투자 판단의 참고 자료이며, 투자 자문을 대체할 수 없습니다.
          </p>
        </div>
      </footer>
    </div>
  );
}
