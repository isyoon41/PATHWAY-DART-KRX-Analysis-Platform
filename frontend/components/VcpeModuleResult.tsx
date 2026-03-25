'use client';

import React, { useState } from 'react';
import {
  TrendingUp, TrendingDown, CheckCircle2, XCircle,
  ChevronDown, ChevronUp, BarChart2, Shield, Zap,
  Target, AlertTriangle, Info,
} from 'lucide-react';
import type { VcpeModuleResultData, VcpeSignal, VcpeRiskItem, VcpeEvidenceItem, VcpeScorecardEntry } from '@/lib/api';

// ──────────────────────────────────────────────────────────────────────
// 유틸
// ──────────────────────────────────────────────────────────────────────
const ACTION_STYLES: Record<string, string> = {
  '즉시검토': 'bg-emerald-600 text-white',
  '조건부검토': 'bg-amber-500 text-white',
  '보류':   'bg-slate-400 text-white',
  '회피':   'bg-red-600 text-white',
};
const ACTION_DEFAULT = 'bg-slate-500 text-white';

// ──────────────────────────────────────────────────────────────────────
// 시그널 필터링 유틸 (Layer 4 핵심)
// ──────────────────────────────────────────────────────────────────────

/** v2 구조화 시그널인지 확인 — claim + data_point 둘 다 있어야 유효 */
function isValidSignal(s: VcpeSignal): boolean {
  if (s.claim && s.data_point && s.data_point.trim() !== '') return true;
  // 구 스키마 폴백: signal 텍스트 + evidence 둘 다 있어야 통과
  if (s.signal && s.evidence && s.evidence.trim() !== '') return true;
  return false;
}

/** 시그널에서 표시용 주요 텍스트 추출 */
function signalClaim(s: VcpeSignal): string {
  return s.claim || s.signal || '';
}
function signalEvidence(s: VcpeSignal): string {
  return s.data_point || s.evidence || '';
}
function signalSection(s: VcpeSignal): string | undefined {
  return s.source_section;
}
function signalImplication(s: VcpeSignal): string | undefined {
  return s.investment_implication;
}
function signalDelta(s: VcpeSignal): string | undefined {
  return s.delta_or_threshold;
}

// ──────────────────────────────────────────────────────────────────────
// 스코어카드 — 한글 레이블 + 근거 수치 매핑
// ──────────────────────────────────────────────────────────────────────
const SCORECARD_META: Record<string, { label: string; desc: string }> = {
  growth_quality:        { label: '성장 품질',   desc: '매출·이익 성장의 지속성 및 질적 수준' },
  profitability_quality: { label: '수익성',       desc: '영업이익률·순이익률 절대값 및 추세' },
  cash_conversion:       { label: '현금창출력',  desc: '영업현금흐름과 순이익의 전환율(OCF/NI)' },
  capital_efficiency:    { label: '자본효율성',  desc: 'ROE·ROIC·자산회전율 종합 평가' },
  governance_quality:    { label: '거버넌스',    desc: '지배구조·이사회 독립성·주주친화성' },
  execution_quality:     { label: '실행력',       desc: '비용통제·가이던스 달성·전략 실행' },
  market_signal:         { label: '시장 시그널', desc: '주가 모멘텀·밸류에이션·시장 인식' },
};

/** 스코어카드 값 정규화 — v1(숫자) / v2({score,basis}) 모두 처리 */
function normalizeScoreEntry(val: any): { score: number; basis?: string } | null {
  if (val === null || val === undefined) return null;
  if (typeof val === 'number') return { score: val };
  if (typeof val === 'object' && typeof val.score === 'number') return val as VcpeScorecardEntry;
  return null;
}

function ScoreRow({ scoreKey, entry }: { scoreKey: string; entry: { score: number; basis?: string } }) {
  const meta  = SCORECARD_META[scoreKey];
  const label = meta?.label ?? scoreKey;
  const desc  = meta?.desc ?? '';
  const score = entry.score;
  const basis = entry.basis?.trim();

  const scoreColor =
    score >= 7 ? 'bg-emerald-100 text-emerald-700 border-emerald-200' :
    score >= 5 ? 'bg-amber-100  text-amber-700  border-amber-200'  :
                 'bg-red-100    text-red-700    border-red-200';
  const barColor =
    score >= 7 ? 'bg-emerald-400' :
    score >= 5 ? 'bg-amber-400'   :
                 'bg-red-400';
  const pct = Math.min(100, Math.max(0, (score / 10) * 100));

  return (
    <div className="grid grid-cols-[6rem_2.5rem_1fr] items-center gap-3 py-1.5">
      {/* 레이블 */}
      <div>
        <p className="text-[12px] font-semibold text-[#334155]">{label}</p>
        <p className="text-[10px] text-[#94A3B8] leading-tight">{desc}</p>
      </div>
      {/* 점수 뱃지 */}
      <span className={`text-[13px] font-bold px-2 py-0.5 rounded border text-center ${scoreColor}`}>
        {score}
      </span>
      {/* 바 + 근거 */}
      <div className="space-y-1">
        <div className="h-1.5 bg-[#E2E8F0] rounded-full overflow-hidden">
          <div className={`h-full rounded-full transition-all ${barColor}`} style={{ width: `${pct}%` }} />
        </div>
        {basis && (
          <p className="text-[11px] text-[#475569] font-mono leading-tight">
            📊 {basis}
          </p>
        )}
      </div>
    </div>
  );
}

function SignalCard({ signal, positive }: { signal: VcpeSignal; positive: boolean }) {
  const claim       = signalClaim(signal);
  const evidence    = signalEvidence(signal);
  const section     = signalSection(signal);
  const delta       = signalDelta(signal);
  const implication = signalImplication(signal);

  return (
    <div className={`p-3 rounded border ${positive ? 'border-emerald-200 bg-emerald-50' : 'border-red-200 bg-red-50'}`}>
      {/* 주장 + 섹션 배지 */}
      <div className="flex items-start justify-between gap-2">
        <p className="text-[13px] font-semibold text-[#1E293B] flex-1">{claim}</p>
        {section && (
          <span className="flex-shrink-0 text-[10px] font-bold bg-slate-200 text-slate-600 px-1.5 py-0.5 rounded">
            {section}
          </span>
        )}
      </div>
      {/* 근거 수치 */}
      {evidence && (
        <p className="text-[12px] text-[#0C2340] font-mono mt-1.5 bg-white/70 px-2 py-1 rounded border border-slate-200">
          📊 {evidence}
        </p>
      )}
      {/* Layer 1: 비교 기준값 (delta_or_threshold) */}
      {delta && (
        <p className={`text-[11px] font-semibold mt-1 px-2 py-0.5 rounded inline-block ${
          positive ? 'bg-emerald-100 text-emerald-700' : 'bg-red-100 text-red-700'
        }`}>
          △ {delta}
        </p>
      )}
      {/* 투자 시사점 */}
      {implication && (
        <p className="text-[11px] text-[#64748B] mt-1.5 italic">
          → {implication}
        </p>
      )}
    </div>
  );
}

function QuestionsPanel({ questions }: { questions: string[] }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="border border-amber-200 rounded">
      <button
        onClick={() => setOpen(o => !o)}
        className="w-full flex items-center justify-between px-4 py-2.5 bg-amber-50 hover:bg-amber-100 transition-colors"
      >
        <span className="text-[12px] font-bold text-amber-700 flex items-center gap-1.5">
          <AlertTriangle className="w-3.5 h-3.5" />
          추가 검증 필요 항목 · {questions.length}개
          <span className="text-[10px] font-normal text-amber-600">(근거 불충분 시그널 포함)</span>
        </span>
        {open ? <ChevronUp className="w-4 h-4 text-amber-500" /> : <ChevronDown className="w-4 h-4 text-amber-500" />}
      </button>
      {open && (
        <ul className="divide-y divide-amber-100">
          {questions.map((q, i) => (
            <li key={i} className="px-4 py-2 flex items-start gap-2 text-[12px] text-[#475569]">
              <span className="text-amber-500 font-bold flex-shrink-0">Q{i + 1}.</span>
              {typeof q === 'string' ? q : (q as any).point || ''}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function EvidenceMap({ map }: { map: VcpeEvidenceItem[] | Record<string, string> | any }) {
  const [open, setOpen] = useState(false);

  // 배열 형식 (백엔드 v2 skeleton)인지 객체인지 판별
  const isArray = Array.isArray(map);

  // 배열 아이템 목록
  const arrayItems: VcpeEvidenceItem[] = isArray ? map : [];
  // Record 형식: 값이 문자열인 엔트리만 안전하게 추출
  const recordEntries: [string, string][] = !isArray
    ? Object.entries(map).filter(([, v]) => typeof v === 'string') as [string, string][]
    : [];

  const count = isArray ? arrayItems.length : recordEntries.length;
  if (count === 0) return null;

  return (
    <div className="border border-[#E2E8F0] rounded">
      <button
        onClick={() => setOpen(o => !o)}
        className="w-full flex items-center justify-between px-4 py-2.5 bg-[#F8FAFC] hover:bg-[#F1F5F9] transition-colors"
      >
        <span className="text-[12px] font-bold text-[#475569] uppercase tracking-wide">
          근거 맵 (Evidence Map) · {count}항목
        </span>
        {open ? <ChevronUp className="w-4 h-4 text-[#94A3B8]" /> : <ChevronDown className="w-4 h-4 text-[#94A3B8]" />}
      </button>
      {open && (
        <div className="divide-y divide-[#E2E8F0]">
          {isArray
            ? arrayItems.map((item, i) => (
                <div key={i} className="px-4 py-2.5 space-y-0.5">
                  <div className="flex items-start justify-between gap-2">
                    <p className="text-[12px] text-[#334155] flex-1">{item.point}</p>
                    {item.assessment_type && (
                      <span className="flex-shrink-0 text-[10px] font-bold bg-slate-200 text-slate-600 px-1.5 py-0.5 rounded">
                        {item.assessment_type}
                      </span>
                    )}
                  </div>
                  {item.source_sections && item.source_sections.length > 0 && (
                    <p className="text-[11px] text-[#94A3B8]">
                      출처: {item.source_sections.join(' / ')}
                    </p>
                  )}
                </div>
              ))
            : recordEntries.map(([k, v]) => (
                <div key={k} className="px-4 py-2.5 flex gap-3">
                  <span className="text-[11px] font-bold text-[#0C2340] w-28 flex-shrink-0">{k}</span>
                  <span className="text-[12px] text-[#334155]">{v}</span>
                </div>
              ))
          }
        </div>
      )}
    </div>
  );
}

// ──────────────────────────────────────────────────────────────────────
// 메인 컴포넌트
// ──────────────────────────────────────────────────────────────────────
interface Props {
  data: VcpeModuleResultData;
  moduleName?: string;
}

export default function VcpeModuleResult({ data, moduleName }: Props) {
  const [activeTab, setActiveTab] = useState<'vc' | 'pe'>('vc');

  // ── 스코어카드 정규화 (v1 숫자 / v2 {score,basis} 통합) ────────────
  const scorecardRows: { key: string; entry: { score: number; basis?: string } }[] =
    data.scorecard
      ? Object.entries(data.scorecard)
          .map(([k, v]) => ({ key: k, entry: normalizeScoreEntry(v) }))
          .filter((r): r is { key: string; entry: { score: number; basis?: string } } => r.entry !== null)
      : [];

  const avgScore = scorecardRows.length
    ? scorecardRows.reduce((s, r) => s + r.entry.score, 0) / scorecardRows.length
    : null;

  const actionStyle = data.recommended_action
    ? (ACTION_STYLES[data.recommended_action] ?? ACTION_DEFAULT)
    : ACTION_DEFAULT;

  // ── Layer 4: 시그널 필터링 ──────────────────────────────────────────
  // 1) data_point(또는 evidence) 있는 것만 통과 → 2) 최대 3개 제한
  const validPositive = (data.positive_signals ?? [])
    .filter(isValidSignal)
    .slice(0, 3);
  const validNegative = (data.negative_signals ?? [])
    .filter(isValidSignal)
    .slice(0, 3);
  // 필터링으로 걸러진 개수 (UX 힌트 표시용)
  const droppedPositive = (data.positive_signals?.length ?? 0) - validPositive.length;
  const droppedNegative = (data.negative_signals?.length ?? 0) - validNegative.length;

  return (
    <div className="space-y-5">

      {/* ── 한 줄 요약 + 액션 ── */}
      <div className="flex items-start justify-between gap-4 p-4 bg-[#F0F6FF] border border-[#BFDBFE] rounded">
        <div>
          {data.one_line_summary && (
            <p className="text-[14px] font-semibold text-[#0C2340]">{data.one_line_summary}</p>
          )}
          {(() => {
            const facts = (data.key_facts ?? [])
              .map(f => typeof f === 'string' ? f : ((f as any).claim || (f as any).data_point || ''))
              .filter(t => t.trim() !== '');
            if (facts.length === 0) return null;
            return (
              <ul className="mt-2 space-y-1">
                {facts.map((t, i) => (
                  <li key={i} className="flex items-start gap-1.5 text-[12px] text-[#334155]">
                    <Info className="w-3.5 h-3.5 mt-0.5 text-[#2E75B6] flex-shrink-0" />
                    {t}
                  </li>
                ))}
              </ul>
            );
          })()}
        </div>
        {data.recommended_action && (
          <span className={`flex-shrink-0 text-[11px] font-bold px-3 py-1 rounded-full ${actionStyle}`}>
            {data.recommended_action}
          </span>
        )}
      </div>

      {/* ── 스코어카드 ── */}
      {scorecardRows.length > 0 && (
        <div className="border border-[#E2E8F0] rounded overflow-hidden">
          {/* 헤더 */}
          <div className="flex items-center justify-between px-4 py-2.5 bg-[#F8FAFC] border-b border-[#E2E8F0]">
            <h3 className="text-[12px] font-bold text-[#475569] flex items-center gap-1.5">
              <BarChart2 className="w-3.5 h-3.5" /> 평가 항목별 점수
            </h3>
            {avgScore !== null && (
              <div className="flex items-center gap-2">
                <span className="text-[10px] text-[#94A3B8]">종합</span>
                <span className={`text-[12px] font-bold px-2 py-0.5 rounded border ${
                  avgScore >= 7 ? 'bg-emerald-100 text-emerald-700 border-emerald-200' :
                  avgScore >= 5 ? 'bg-amber-100 text-amber-700 border-amber-200' :
                                  'bg-red-100 text-red-700 border-red-200'
                }`}>
                  {avgScore.toFixed(1)} / 10
                </span>
              </div>
            )}
          </div>
          {/* 컬럼 헤더 */}
          <div className="grid grid-cols-[6rem_2.5rem_1fr] gap-3 px-4 py-1 bg-[#F1F5F9] border-b border-[#E2E8F0]">
            <span className="text-[10px] font-bold text-[#94A3B8] uppercase tracking-wider">항목</span>
            <span className="text-[10px] font-bold text-[#94A3B8] uppercase tracking-wider text-center">점수</span>
            <span className="text-[10px] font-bold text-[#94A3B8] uppercase tracking-wider">추세 · 근거 수치</span>
          </div>
          {/* 행 */}
          <div className="divide-y divide-[#F1F5F9] px-4">
            {scorecardRows.map(({ key, entry }) => (
              <ScoreRow key={key} scoreKey={key} entry={entry} />
            ))}
          </div>
          {/* 범례 */}
          <div className="flex items-center gap-4 px-4 py-2 bg-[#F8FAFC] border-t border-[#E2E8F0]">
            <span className="text-[10px] text-[#94A3B8]">점수 기준:</span>
            <span className="flex items-center gap-1 text-[10px] text-emerald-600"><span className="w-2 h-2 rounded-full bg-emerald-400 inline-block"/>7~10 양호</span>
            <span className="flex items-center gap-1 text-[10px] text-amber-600"><span className="w-2 h-2 rounded-full bg-amber-400 inline-block"/>5~6 보통</span>
            <span className="flex items-center gap-1 text-[10px] text-red-600"><span className="w-2 h-2 rounded-full bg-red-400 inline-block"/>1~4 부진</span>
          </div>
        </div>
      )}

      {/* ── 시그널 (Positive / Negative) — 필터링 적용 ── */}
      {(validPositive.length > 0 || validNegative.length > 0) && (
        <div className="grid grid-cols-2 gap-4">
          {/* Positive */}
          <div>
            <div className="flex items-center gap-1.5 mb-2">
              <h3 className="text-[12px] font-bold uppercase tracking-widest text-[#64748B] flex items-center gap-1.5">
                <TrendingUp className="w-3.5 h-3.5 text-emerald-500" /> 긍정 시그널
              </h3>
              <span className="text-[10px] text-[#94A3B8]">({validPositive.length}개)</span>
            </div>
            {validPositive.length > 0 ? (
              <div className="space-y-2">
                {validPositive.map((s, i) => (
                  <SignalCard key={i} signal={s} positive />
                ))}
                {droppedPositive > 0 && (
                  <p className="text-[10px] text-[#94A3B8] pl-1">
                    근거 불충분으로 {droppedPositive}개 생략됨 → questions_to_validate 참고
                  </p>
                )}
              </div>
            ) : (
              <p className="text-[12px] text-[#94A3B8] italic">근거 있는 긍정 시그널 없음</p>
            )}
          </div>
          {/* Negative */}
          <div>
            <div className="flex items-center gap-1.5 mb-2">
              <h3 className="text-[12px] font-bold uppercase tracking-widest text-[#64748B] flex items-center gap-1.5">
                <TrendingDown className="w-3.5 h-3.5 text-red-500" /> 부정 시그널
              </h3>
              <span className="text-[10px] text-[#94A3B8]">({validNegative.length}개)</span>
            </div>
            {validNegative.length > 0 ? (
              <div className="space-y-2">
                {validNegative.map((s, i) => (
                  <SignalCard key={i} signal={s} positive={false} />
                ))}
                {droppedNegative > 0 && (
                  <p className="text-[10px] text-[#94A3B8] pl-1">
                    근거 불충분으로 {droppedNegative}개 생략됨 → questions_to_validate 참고
                  </p>
                )}
              </div>
            ) : (
              <p className="text-[12px] text-[#94A3B8] italic">근거 있는 부정 시그널 없음</p>
            )}
          </div>
        </div>
      )}

      {/* ── VC / PE 탭 ── */}
      {(data.vc_view || data.pe_view) && (() => {
        // vc_view / pe_view 가 빈 문자열이거나 문자열로 오는 경우 방어
        const vcObj = typeof data.vc_view === 'object' && data.vc_view !== null ? data.vc_view : null;
        const vcStr = typeof data.vc_view === 'string' && (data.vc_view as string).trim() ? data.vc_view as string : null;
        const peObj = typeof data.pe_view === 'object' && data.pe_view !== null ? data.pe_view : null;
        const peStr = typeof data.pe_view === 'string' && (data.pe_view as string).trim() ? data.pe_view as string : null;
        const hasVc = !!(vcObj || vcStr);
        const hasPe = !!(peObj || peStr);
        if (!hasVc && !hasPe) return null;
        return (
          <div className="border border-[#E2E8F0] rounded overflow-hidden">
            <div className="flex border-b border-[#E2E8F0]">
              {(['vc', 'pe'] as const).map(tab => (
                <button
                  key={tab}
                  onClick={() => setActiveTab(tab)}
                  className={`flex-1 py-2 text-[12px] font-bold uppercase tracking-wider transition-colors ${
                    activeTab === tab
                      ? 'bg-[#0C2340] text-white'
                      : 'bg-[#F8FAFC] text-[#64748B] hover:bg-[#F1F5F9]'
                  }`}
                >
                  {tab === 'vc' ? '⚡ VC 관점' : '🏗️ PE 관점'}
                </button>
              ))}
            </div>
            <div className="p-4">
              {activeTab === 'vc' && (
                <div className="space-y-3">
                  {/* 문자열 폴백 */}
                  {vcStr && !vcObj && (
                    <p className="text-[13px] text-[#1E293B]">{vcStr}</p>
                  )}
                  {/* 구조화 객체 */}
                  {vcObj && (
                    <>
                      {vcObj.summary && (
                        <p className="text-[13px] text-[#1E293B]">{vcObj.summary}</p>
                      )}
                      {vcObj.upside_drivers && vcObj.upside_drivers.length > 0 && (
                        <div>
                          <p className="text-[11px] font-bold text-[#475569] mb-1.5">업사이드 드라이버</p>
                          <ul className="space-y-1">
                            {vcObj.upside_drivers.map((d: string, i: number) => (
                              <li key={i} className="flex items-start gap-2 text-[12px] text-[#334155]">
                                <Zap className="w-3.5 h-3.5 mt-0.5 text-amber-500 flex-shrink-0" />{d}
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}
                      {vcObj.key_risks && vcObj.key_risks.length > 0 && (
                        <div>
                          <p className="text-[11px] font-bold text-[#475569] mb-1.5">핵심 리스크</p>
                          <ul className="space-y-1">
                            {vcObj.key_risks.map((r: string, i: number) => (
                              <li key={i} className="flex items-start gap-2 text-[12px] text-[#334155]">
                                <AlertTriangle className="w-3.5 h-3.5 mt-0.5 text-red-400 flex-shrink-0" />{r}
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}
                      {vcObj.entry_strategy && (
                        <div className="bg-amber-50 border border-amber-200 p-3 rounded">
                          <p className="text-[11px] font-bold text-amber-700 mb-1">진입 전략</p>
                          <p className="text-[12px] text-[#334155]">{vcObj.entry_strategy}</p>
                        </div>
                      )}
                    </>
                  )}
                  {!hasVc && <p className="text-[12px] text-[#94A3B8] italic">VC 관점 분석 없음</p>}
                </div>
              )}
              {activeTab === 'pe' && (
                <div className="space-y-3">
                  {/* 문자열 폴백 */}
                  {peStr && !peObj && (
                    <p className="text-[13px] text-[#1E293B]">{peStr}</p>
                  )}
                  {/* 구조화 객체 */}
                  {peObj && (
                    <>
                      {peObj.summary && (
                        <p className="text-[13px] text-[#1E293B]">{peObj.summary}</p>
                      )}
                      {peObj.value_creation_levers && peObj.value_creation_levers.length > 0 && (
                        <div>
                          <p className="text-[11px] font-bold text-[#475569] mb-1.5">가치 창출 레버</p>
                          <ul className="space-y-1">
                            {peObj.value_creation_levers.map((l: string, i: number) => (
                              <li key={i} className="flex items-start gap-2 text-[12px] text-[#334155]">
                                <Target className="w-3.5 h-3.5 mt-0.5 text-blue-500 flex-shrink-0" />{l}
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}
                      {peObj.exit_considerations && peObj.exit_considerations.length > 0 && (
                        <div>
                          <p className="text-[11px] font-bold text-[#475569] mb-1.5">엑시트 고려사항</p>
                          <ul className="space-y-1">
                            {peObj.exit_considerations.map((e: string, i: number) => (
                              <li key={i} className="flex items-start gap-2 text-[12px] text-[#334155]">
                                <Shield className="w-3.5 h-3.5 mt-0.5 text-purple-500 flex-shrink-0" />{e}
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}
                      {peObj.ebitda_assessment && (
                        <div className="bg-blue-50 border border-blue-200 p-3 rounded">
                          <p className="text-[11px] font-bold text-blue-700 mb-1">EBITDA 평가</p>
                          <p className="text-[12px] text-[#334155]">{peObj.ebitda_assessment}</p>
                        </div>
                      )}
                    </>
                  )}
                  {!hasPe && <p className="text-[12px] text-[#94A3B8] italic">PE 관점 분석 없음</p>}
                </div>
              )}
            </div>
          </div>
        );
      })()}

      {/* ── 리스크 분류 (Layer 3: 최상위 필드 사용, 구조화 렌더링) ── */}
      {(
        (data.temporary_issues?.length ?? 0) > 0 ||
        (data.structural_risks?.length  ?? 0) > 0 ||
        (data.fatal_risks?.length       ?? 0) > 0
      ) && (
        <div className="space-y-3">
          {([
            { key: 'temporary_issues' as const,  label: '일시적 리스크',  cls: 'border-amber-200 bg-amber-50',   dot: 'bg-amber-400',  badge: 'bg-amber-100 text-amber-700' },
            { key: 'structural_risks' as const,  label: '구조적 리스크',  cls: 'border-orange-200 bg-orange-50', dot: 'bg-orange-500', badge: 'bg-orange-100 text-orange-700' },
            { key: 'fatal_risks'      as const,  label: '치명적 리스크',  cls: 'border-red-200 bg-red-50',       dot: 'bg-red-500',    badge: 'bg-red-100 text-red-700' },
          ]).map(({ key, label, cls, dot, badge }) => {
            const items = data[key] as (VcpeRiskItem | string)[] | undefined;
            if (!items || items.length === 0) return null;
            return (
              <div key={key} className={`rounded border ${cls}`}>
                <div className="flex items-center gap-2 px-3 py-2 border-b border-current/10">
                  <span className={`text-[10px] font-bold px-2 py-0.5 rounded ${badge}`}>{label}</span>
                  <span className="text-[10px] text-[#94A3B8]">{items.length}건</span>
                </div>
                <div className="divide-y divide-current/5">
                  {items.map((r, i) => {
                    // 구조화 객체 vs 구형 문자열 모두 지원
                    if (typeof r === 'string') {
                      return (
                        <div key={i} className="px-3 py-2 flex items-start gap-2">
                          <span className={`mt-1.5 w-1.5 h-1.5 rounded-full flex-shrink-0 ${dot}`} />
                          <p className="text-[12px] text-[#334155]">{r}</p>
                        </div>
                      );
                    }
                    return (
                      <div key={i} className="px-3 py-2.5 space-y-1">
                        <div className="flex items-start justify-between gap-2">
                          <p className="text-[12px] font-semibold text-[#1E293B] flex-1">{r.description}</p>
                          {r.source_section && (
                            <span className="flex-shrink-0 text-[10px] font-bold bg-slate-200 text-slate-600 px-1.5 py-0.5 rounded">
                              {r.source_section}
                            </span>
                          )}
                        </div>
                        {r.evidence && (
                          <p className="text-[11px] font-mono text-[#0C2340] bg-white/70 px-2 py-0.5 rounded border border-slate-200">
                            📊 {r.evidence}
                          </p>
                        )}
                        {r.context && (
                          <p className="text-[11px] text-[#64748B] italic">↳ {r.context}</p>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* ── 신뢰도 ── */}
      {data.confidence != null && (() => {
        // confidence가 숫자(0.0~1.0 또는 0~10)로 올 수도 있음 — 방어 처리
        const confRaw = data.confidence;
        if (typeof confRaw === 'number') {
          // 단일 숫자: 0~1 범위면 ×100, 1 초과면 ×10 으로 환산
          const pct = confRaw <= 1 ? confRaw * 100 : Math.min(100, confRaw * 10);
          const display = confRaw <= 1 ? (confRaw * 10).toFixed(1) : confRaw.toFixed(1);
          return (
            <div className="p-4 border border-[#E2E8F0] rounded">
              <h3 className="text-[12px] font-bold uppercase tracking-widest text-[#64748B] mb-3">분석 신뢰도</h3>
              <div className="flex items-center gap-3">
                <span className="text-[12px] text-[#475569] w-24 flex-shrink-0">종합 신뢰도</span>
                <div className="flex-1 bg-[#E2E8F0] rounded-full h-1.5">
                  <div className="h-1.5 rounded-full bg-[#2E75B6] transition-all" style={{ width: `${pct}%` }} />
                </div>
                <span className="text-[12px] text-[#64748B] w-6 text-right">{display}</span>
              </div>
            </div>
          );
        }
        // 객체 형식 (VcpeConfidence)
        if (typeof confRaw !== 'object' || confRaw === null) return null;
        const confObj = confRaw as Record<string, number | undefined>;
        const rows: [string, string][] = [
          ['overall',        '종합 신뢰도'],
          ['data_quality',   '데이터 품질'],
          ['analysis_depth', '분석 깊이'],
        ];
        return (
          <div className="p-4 border border-[#E2E8F0] rounded">
            <h3 className="text-[12px] font-bold uppercase tracking-widest text-[#64748B] mb-3">분석 신뢰도</h3>
            <div className="space-y-2">
              {rows.map(([k, lbl]) => {
                const v = confObj[k];
                if (v === undefined || v === null) return null;
                const pct = Math.min(100, Math.max(0, v * 10));
                return (
                  <div key={k} className="flex items-center gap-3">
                    <span className="text-[12px] text-[#475569] w-24 flex-shrink-0">{lbl}</span>
                    <div className="flex-1 bg-[#E2E8F0] rounded-full h-1.5">
                      <div className="h-1.5 rounded-full bg-[#2E75B6] transition-all" style={{ width: `${pct}%` }} />
                    </div>
                    <span className="text-[12px] text-[#64748B] w-6 text-right">{v}</span>
                  </div>
                );
              })}
            </div>
          </div>
        );
      })()}

      {/* ── 검증 질문 (근거 불충분 시그널 포함) ── */}
      {data.questions_to_validate && data.questions_to_validate.length > 0 && (
        <QuestionsPanel questions={data.questions_to_validate} />
      )}

      {/* ── 근거 맵 ── */}
      {data.evidence_map != null && (
        Array.isArray(data.evidence_map)
          ? (data.evidence_map as any[]).length > 0
          : Object.keys(data.evidence_map).length > 0
      ) && (
        <EvidenceMap map={data.evidence_map} />
      )}
    </div>
  );
}
