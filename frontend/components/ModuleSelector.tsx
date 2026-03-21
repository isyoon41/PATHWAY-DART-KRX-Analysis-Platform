'use client';

import React, { useState } from 'react';
import { Sparkles, FileText, Loader2, CheckCircle2, AlertCircle } from 'lucide-react';
import { CompanySearchResult } from '@/lib/api';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

// ──────────────────────────────────────────────────────────────────────
// 모듈 목록 — 백엔드 의존 없이 프론트엔드에 상수로 내장
// (백엔드 module_service.py 의 MODULES 와 동일)
// ──────────────────────────────────────────────────────────────────────

export interface AnalysisModule {
  id: string;
  name: string;
  badge: string;
  is_core: boolean;
  desc: string;
}

const STATIC_MODULES: AnalysisModule[] = [
  // ── S1+S2+S7 통합 ──────────────────────────────────────────────
  { id: 'comprehensive',     name: '종합 기업분석',          badge: 'CORE',       is_core: true,  desc: '사업·재무·지배구조·감사의견 전체 통합 (DART 원문 기반)' },
  // ── S7 재무 ────────────────────────────────────────────────────
  { id: 'key_financials',    name: '핵심 재무지표',          badge: 'FINANCIALS', is_core: true,  desc: '수익성·안정성·성장성 핵심 지표 집중 분석 (XBRL 기반)' },
  { id: 'full_financials',   name: '전체 재무제표',          badge: 'BALANCE',    is_core: false, desc: '재무상태표·손익계산서·현금흐름표 3개년 요약 1표' },
  // ── S2 사업 ────────────────────────────────────────────────────
  { id: 'business_segments', name: '사업부문별 실적',        badge: 'BUSINESS',   is_core: false, desc: '사업부문별 매출·영업이익·경쟁력 분석 (사업보고서 원문)' },
  // ── S5 주주 ────────────────────────────────────────────────────
  { id: 'shareholders',      name: '주주현황',               badge: 'OWNERSHIP',  is_core: false, desc: '주요 주주·지분 구조·오너 리스크 분석' },
  // ── S6 이사회 ──────────────────────────────────────────────────
  { id: 'board_executives',  name: '이사회/임원 분석',       badge: 'GOVERNANCE', is_core: false, desc: '이사회 구성·임원 현황·내부통제 평가' },
  // ── S11 주가 ───────────────────────────────────────────────────
  { id: 'stock_movement',    name: '주가 변동 원인',         badge: 'MARKET',     is_core: true,  desc: '주가 변동과 공시·이벤트 상관관계 분석 (KRX+DART 연계)' },
  // ── S9 유상증자/메자닌 ─────────────────────────────────────────
  { id: 'capital_increase',  name: '유상증자 / 메자닌',      badge: 'CAPITAL',    is_core: false, desc: '유상증자·CB·BW 이력 및 주주 희석 리스크 분석' },
  // ── S10 잠정실적 ───────────────────────────────────────────────
  { id: 'preliminary',       name: '잠정실적',               badge: 'EARNINGS',   is_core: false, desc: '분기별 잠정실적 공시 및 어닝 서프라이즈 분석' },
];

export interface ModuleResult {
  module_id: string;
  module_name: string;
  report: string;
  generated_at: string;
  model: string;
  corp_name: string;
  period: string;
}

type ModuleStatus = 'idle' | 'loading' | 'done' | 'error';

const BADGE_COLORS: Record<string, string> = {
  CORE:       'bg-[#0C2340] text-white',
  BUSINESS:   'bg-blue-100 text-blue-800',
  GOVERNANCE: 'bg-purple-100 text-purple-800',
  FINANCIALS: 'bg-emerald-100 text-emerald-800',
  BALANCE:    'bg-teal-100 text-teal-800',
  CAPITAL:    'bg-pink-100 text-pink-800',
  EARNINGS:   'bg-amber-100 text-amber-800',
  OWNERSHIP:  'bg-indigo-100 text-indigo-800',
  MARKET:     'bg-cyan-100 text-cyan-800',
};

// ──────────────────────────────────────────────────────────────────────
// 마크다운 렌더러 — react-markdown + remark-gfm
// ──────────────────────────────────────────────────────────────────────
function MdRenderer({ text }: { text: string }) {
  return (
    <div className="md-report">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          // 헤딩
          h1: ({ children }) => (
            <h1 className="text-[19px] font-bold text-[#0C2340] mt-8 mb-3 pb-2 border-b-2 border-[#0C2340]">
              {children}
            </h1>
          ),
          h2: ({ children }) => (
            <h2 className="text-[16px] font-bold text-[#0C2340] mt-7 mb-2.5">
              {children}
            </h2>
          ),
          h3: ({ children }) => (
            <h3 className="text-[14px] font-bold text-[#1F3864] mt-5 mb-2 flex items-center gap-2">
              <span className="inline-block w-[3px] h-[14px] bg-[#2E75B6] flex-shrink-0 rounded-sm" />
              {children}
            </h3>
          ),
          h4: ({ children }) => (
            <h4 className="text-[13px] font-semibold text-[#334155] mt-4 mb-1.5 border-l-2 border-[#94A3B8] pl-2">
              {children}
            </h4>
          ),
          // 단락
          p: ({ children }) => (
            <p className="text-[13px] leading-[1.75] text-[#1E293B] mb-2">
              {children}
            </p>
          ),
          // 강조
          strong: ({ children }) => (
            <strong className="font-semibold text-[#0C2340]">{children}</strong>
          ),
          em: ({ children }) => (
            <em className="italic text-[#475569]">{children}</em>
          ),
          // 표 (remark-gfm)
          table: ({ children }) => (
            <div className="my-4 overflow-x-auto">
              <table className="w-full border-collapse text-[12.5px]">
                {children}
              </table>
            </div>
          ),
          thead: ({ children }) => (
            <thead className="bg-[#0C2340] text-white">{children}</thead>
          ),
          tbody: ({ children }) => (
            <tbody className="divide-y divide-[#E2E8F0]">{children}</tbody>
          ),
          tr: ({ children }) => (
            <tr className="hover:bg-[#F7F9FC] transition-colors">{children}</tr>
          ),
          th: ({ children }) => (
            <th className="px-3 py-2 text-left font-semibold whitespace-nowrap">{children}</th>
          ),
          td: ({ children }) => (
            <td className="px-3 py-2 text-[#334155] align-top">{children}</td>
          ),
          // 리스트
          ul: ({ children }) => (
            <ul className="my-2 space-y-1 pl-1 list-none">{children}</ul>
          ),
          ol: ({ children }) => (
            <ol className="my-2 space-y-1 pl-5 list-decimal text-[13px] leading-[1.7] text-[#1E293B]">{children}</ol>
          ),
          li: ({ ordered, children }: any) => {
            if (ordered) {
              return (
                <li className="text-[13px] leading-[1.7] text-[#1E293B] pl-1">
                  {children}
                </li>
              );
            }
            return (
              <li className="flex items-start gap-2 text-[13px] leading-[1.7] text-[#1E293B]">
                <span className="mt-[8px] w-[5px] h-[5px] bg-[#2E75B6] rounded-full flex-shrink-0" />
                <span className="flex-1">{children}</span>
              </li>
            );
          },
          // 구분선
          hr: () => <hr className="my-5 border-[#E2E8F0]" />,
          // 코드
          code: ({ children }) => (
            <code className="bg-[#F1F5F9] text-[#0C2340] px-1.5 py-0.5 rounded text-[12px] font-mono">
              {children}
            </code>
          ),
          // 인용
          blockquote: ({ children }) => (
            <blockquote className="border-l-4 border-[#2E75B6] pl-4 my-3 text-[#475569] italic">
              {children}
            </blockquote>
          ),
        }}
      >
        {text}
      </ReactMarkdown>
    </div>
  );
}

// ──────────────────────────────────────────────────────────────────────
// 메인 컴포넌트
// ──────────────────────────────────────────────────────────────────────
interface ModuleSelectorProps {
  company: CompanySearchResult;
  endYear: string;
  onBack: () => void;
}

export default function ModuleSelector({ company, endYear, onBack }: ModuleSelectorProps) {
  // 모듈 목록은 프론트엔드 상수 사용 — 백엔드 없이도 항상 표시
  const modules = STATIC_MODULES;
  const [statuses, setStatuses]         = useState<Record<string, ModuleStatus>>({});
  const [results, setResults]           = useState<Record<string, ModuleResult>>({});
  const [activeModule, setActiveModule] = useState<string | null>(null);
  const [backendError, setBackendError] = useState('');

  const runModule = async (moduleId: string) => {
    setStatuses(s => ({ ...s, [moduleId]: 'loading' }));
    setActiveModule(moduleId);
    setBackendError('');

    try {
      // 상대경로 사용 → Next.js rewrites가 BACKEND_URL 로 프록시
      const backendBase = process.env.NEXT_PUBLIC_BACKEND_URL || '';
      const res = await fetch(
        `${backendBase}/api/analysis/${company.corp_code}/module/${moduleId}?end_year=${endYear}`,
        { method: 'POST' }
      );
      if (!res.ok) {
        const errText = await res.text();
        throw new Error(errText);
      }
      const data: ModuleResult = await res.json();
      setResults(r => ({ ...r, [moduleId]: data }));
      setStatuses(s => ({ ...s, [moduleId]: 'done' }));
    } catch (e: any) {
      setStatuses(s => ({ ...s, [moduleId]: 'error' }));
      if (e.message?.includes('fetch') || e.message?.includes('network')) {
        setBackendError('백엔드 서버(localhost:8000)에 연결할 수 없습니다. 백엔드를 시작해주세요.');
      }
    }
  };

  const activeResult = activeModule ? results[activeModule] : null;
  const activeStatus = activeModule ? (statuses[activeModule] || 'idle') : 'idle';

  return (
    <div className="flex gap-6 min-h-[600px]">

      {/* ── 좌측 모듈 목록 ── */}
      <div className="w-72 flex-shrink-0">
        {/* 헤더 */}
        <div className="bg-[#0C2340] px-4 py-3 mb-2">
          <p className="text-white font-bold text-[13px]">{company.corp_name}</p>
          <p className="text-white/50 text-[11px]">분석 기준: {endYear}년</p>
        </div>
        <p className="text-[11px] font-bold uppercase tracking-widest text-[#94A3B8] px-1 mb-2">
          템플릿 목록 · 총 {modules.length}개
        </p>

        {/* 백엔드 연결 오류 */}
        {backendError && (
          <div className="mx-1 mb-2 px-3 py-2 bg-red-50 border border-red-200 text-[11px] text-red-600">
            {backendError}
          </div>
        )}

        <div className="space-y-1">
          {modules.map(mod => {
            const status = statuses[mod.id] || 'idle';
            const isActive = activeModule === mod.id;

            return (
              <button
                key={mod.id}
                onClick={() => {
                  setActiveModule(mod.id);
                  if (!results[mod.id]) runModule(mod.id);
                }}
                className={`w-full text-left px-3 py-3 border transition-all ${
                  isActive
                    ? 'border-[#0C2340] bg-[#EBF2FA]'
                    : 'border-transparent hover:bg-[#F7F9FC] hover:border-[#E2E8F0]'
                }`}
              >
                <div className="flex items-start gap-2.5">
                  {/* 아이콘 */}
                  <div className="mt-0.5 flex-shrink-0">
                    {status === 'loading' && <Loader2 className="w-4 h-4 animate-spin text-[#2E75B6]" />}
                    {status === 'done'    && <CheckCircle2 className="w-4 h-4 text-emerald-500" />}
                    {status === 'error'   && <AlertCircle className="w-4 h-4 text-red-400" />}
                    {status === 'idle'    && (
                      mod.is_core
                        ? <Sparkles className="w-4 h-4 text-[#2E75B6]" />
                        : <FileText className="w-4 h-4 text-[#94A3B8]" />
                    )}
                  </div>

                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-1.5 flex-wrap">
                      <span className={`font-semibold text-[13px] ${isActive ? 'text-[#0C2340]' : 'text-[#1E293B]'}`}>
                        {mod.name}
                      </span>
                      <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${BADGE_COLORS[mod.badge] || 'bg-gray-100 text-gray-600'}`}>
                        {mod.badge}
                      </span>
                    </div>
                    <p className="text-[11px] text-[#64748B] mt-0.5 leading-tight">{mod.desc}</p>
                  </div>
                </div>
              </button>
            );
          })}
        </div>

        {/* 뒤로가기 */}
        <button
          onClick={onBack}
          className="mt-4 w-full text-[12px] text-[#64748B] border border-[#E2E8F0] py-2 hover:bg-[#F7F9FC] transition-colors"
        >
          ← 기업 재선택
        </button>
      </div>

      {/* ── 우측 분석 결과 ── */}
      <div className="flex-1 min-w-0 bg-white border border-[#E2E8F0]">
        {!activeModule && (
          <div className="flex flex-col items-center justify-center h-full text-center py-20">
            <Sparkles className="w-10 h-10 text-[#CBD5E1] mb-4" />
            <p className="text-[#64748B] font-semibold text-[15px] mb-2">분석 모듈을 선택하세요</p>
            <p className="text-[#94A3B8] text-[13px]">
              좌측 목록에서 원하는 분석 모듈을 클릭하면<br />해당 섹션 원문을 읽어 집중 분석합니다
            </p>
          </div>
        )}

        {activeModule && activeStatus === 'loading' && (
          <div className="flex flex-col items-center justify-center h-full py-20">
            <Loader2 className="w-8 h-8 animate-spin text-[#2E75B6] mb-4" />
            <p className="text-[#1F3864] font-semibold text-[15px] mb-1">
              {modules.find(m => m.id === activeModule)?.name} 분석 중
            </p>
            <p className="text-[#64748B] text-[13px]">
              사업보고서 원문을 읽어 AI 분석 중입니다 (30~60초)
            </p>
          </div>
        )}

        {activeModule && activeStatus === 'error' && (
          <div className="flex flex-col items-center justify-center h-full py-20">
            <AlertCircle className="w-8 h-8 text-red-400 mb-4" />
            <p className="text-red-600 font-semibold mb-2">분석 실패</p>
            <button
              onClick={() => runModule(activeModule)}
              className="text-[13px] bg-[#0C2340] text-white px-4 py-2 hover:bg-[#1F3864]"
            >
              다시 시도
            </button>
          </div>
        )}

        {activeModule && activeStatus === 'done' && activeResult && (
          <div className="p-6 overflow-auto">
            {/* 리포트 헤더 */}
            <div className="border-b-2 border-[#0C2340] pb-4 mb-6">
              <div className="flex items-center gap-2 mb-1">
                <span className={`text-[11px] font-bold px-2 py-0.5 ${BADGE_COLORS[modules.find(m=>m.id===activeModule)?.badge||''] || 'bg-gray-100'}`}>
                  {modules.find(m => m.id === activeModule)?.badge}
                </span>
                <span className="text-[11px] text-[#94A3B8]">{activeResult.period} · {new Date(activeResult.generated_at).toLocaleString('ko-KR')}</span>
              </div>
              <h2 className="text-[18px] font-bold text-[#0C2340]">
                {activeResult.corp_name} — {activeResult.module_name}
              </h2>
            </div>

            {/* 리포트 본문 */}
            <MdRenderer text={activeResult.report} />

            {/* 하단 메타 */}
            <div className="mt-8 pt-4 border-t border-[#E2E8F0] flex items-center justify-between text-[11px] text-[#94A3B8]">
              <span>분석 엔진: {activeResult.model}</span>
              <span>데이터 출처: DART 공시 원문 · KRX · 네이버 금융</span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
