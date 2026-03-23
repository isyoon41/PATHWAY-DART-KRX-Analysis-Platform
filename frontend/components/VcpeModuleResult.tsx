'use client';

import React, { useState } from 'react';
import {
  TrendingUp, TrendingDown, CheckCircle2, XCircle,
  ChevronDown, ChevronUp, BarChart2, Shield, Zap,
  Target, AlertTriangle, Info,
} from 'lucide-react';
import type { VcpeModuleResultData, VcpeSignal } from '@/lib/api';

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

function ScoreBar({ label, value }: { label: string; value: number }) {
  const pct = Math.min(100, Math.max(0, (value / 10) * 100));
  const color =
    value >= 7 ? 'bg-emerald-500' :
    value >= 5 ? 'bg-amber-400'   :
                 'bg-red-400';
  return (
    <div className="flex items-center gap-3">
      <span className="text-[12px] text-[#475569] w-20 flex-shrink-0">{label}</span>
      <div className="flex-1 bg-[#E2E8F0] rounded-full h-2">
        <div
          className={`h-2 rounded-full transition-all ${color}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="text-[12px] font-bold text-[#0C2340] w-6 text-right">{value}</span>
    </div>
  );
}

function SignalCard({ signal, positive }: { signal: VcpeSignal; positive: boolean }) {
  const claim      = signalClaim(signal);
  const evidence   = signalEvidence(signal);
  const section    = signalSection(signal);
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
      {/* 근거 수치 — 핵심 */}
      {evidence && (
        <p className="text-[12px] text-[#0C2340] font-mono mt-1.5 bg-white/70 px-2 py-1 rounded border border-slate-200">
          📊 {evidence}
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
              {q}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function EvidenceMap({ map }: { map: Record<string, string> }) {
  const [open, setOpen] = useState(false);
  const entries = Object.entries(map);
  return (
    <div className="border border-[#E2E8F0] rounded">
      <button
        onClick={() => setOpen(o => !o)}
        className="w-full flex items-center justify-between px-4 py-2.5 bg-[#F8FAFC] hover:bg-[#F1F5F9] transition-colors"
      >
        <span className="text-[12px] font-bold text-[#475569] uppercase tracking-wide">
          근거 맵 (Evidence Map) · {entries.length}항목
        </span>
        {open ? <ChevronUp className="w-4 h-4 text-[#94A3B8]" /> : <ChevronDown className="w-4 h-4 text-[#94A3B8]" />}
      </button>
      {open && (
        <div className="divide-y divide-[#E2E8F0]">
          {entries.map(([k, v]) => (
            <div key={k} className="px-4 py-2.5 flex gap-3">
              <span className="text-[11px] font-bold text-[#0C2340] w-28 flex-shrink-0">{k}</span>
              <span className="text-[12px] text-[#334155]">{v}</span>
            </div>
          ))}
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

  const scorecardEntries = data.scorecard
    ? Object.entries(data.scorecard).filter(([, v]) => typeof v === 'number') as [string, number][]
    : [];

  const avgScore = scorecardEntries.length
    ? scorecardEntries.reduce((s, [, v]) => s + v, 0) / scorecardEntries.length
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
          {data.key_facts && data.key_facts.length > 0 && (
            <ul className="mt-2 space-y-1">
              {data.key_facts.map((f, i) => (
                <li key={i} className="flex items-start gap-1.5 text-[12px] text-[#334155]">
                  <Info className="w-3.5 h-3.5 mt-0.5 text-[#2E75B6] flex-shrink-0" />
                  {f}
                </li>
              ))}
            </ul>
          )}
        </div>
        {data.recommended_action && (
          <span className={`flex-shrink-0 text-[11px] font-bold px-3 py-1 rounded-full ${actionStyle}`}>
            {data.recommended_action}
          </span>
        )}
      </div>

      {/* ── 스코어카드 ── */}
      {/* (scorecardEntries rendered below) */}
      {scorecardEntries.length > 0 && (
        <div className="p-4 border border-[#E2E8F0] rounded">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-[12px] font-bold uppercase tracking-widest text-[#64748B] flex items-center gap-1.5">
              <BarChart2 className="w-3.5 h-3.5" /> 스코어카드
            </h3>
            {avgScore !== null && (
              <span className="text-[11px] text-[#94A3B8]">
                평균 <strong className="text-[#0C2340]">{avgScore.toFixed(1)}</strong> / 10
              </span>
            )}
          </div>
          <div className="space-y-2">
            {scorecardEntries.map(([k, v]) => (
              <ScoreBar key={k} label={k} value={v} />
            ))}
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
      {(data.vc_view || data.pe_view) && (
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
            {activeTab === 'vc' && data.vc_view && (
              <div className="space-y-3">
                {data.vc_view.summary && (
                  <p className="text-[13px] text-[#1E293B]">{data.vc_view.summary}</p>
                )}
                {data.vc_view.upside_drivers && data.vc_view.upside_drivers.length > 0 && (
                  <div>
                    <p className="text-[11px] font-bold text-[#475569] mb-1.5">업사이드 드라이버</p>
                    <ul className="space-y-1">
                      {data.vc_view.upside_drivers.map((d, i) => (
                        <li key={i} className="flex items-start gap-2 text-[12px] text-[#334155]">
                          <Zap className="w-3.5 h-3.5 mt-0.5 text-amber-500 flex-shrink-0" />{d}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
                {data.vc_view.key_risks && data.vc_view.key_risks.length > 0 && (
                  <div>
                    <p className="text-[11px] font-bold text-[#475569] mb-1.5">핵심 리스크</p>
                    <ul className="space-y-1">
                      {data.vc_view.key_risks.map((r, i) => (
                        <li key={i} className="flex items-start gap-2 text-[12px] text-[#334155]">
                          <AlertTriangle className="w-3.5 h-3.5 mt-0.5 text-red-400 flex-shrink-0" />{r}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
                {data.vc_view.entry_strategy && (
                  <div className="bg-amber-50 border border-amber-200 p-3 rounded">
                    <p className="text-[11px] font-bold text-amber-700 mb-1">진입 전략</p>
                    <p className="text-[12px] text-[#334155]">{data.vc_view.entry_strategy}</p>
                  </div>
                )}
              </div>
            )}
            {activeTab === 'pe' && data.pe_view && (
              <div className="space-y-3">
                {data.pe_view.summary && (
                  <p className="text-[13px] text-[#1E293B]">{data.pe_view.summary}</p>
                )}
                {data.pe_view.value_creation_levers && data.pe_view.value_creation_levers.length > 0 && (
                  <div>
                    <p className="text-[11px] font-bold text-[#475569] mb-1.5">가치 창출 레버</p>
                    <ul className="space-y-1">
                      {data.pe_view.value_creation_levers.map((l, i) => (
                        <li key={i} className="flex items-start gap-2 text-[12px] text-[#334155]">
                          <Target className="w-3.5 h-3.5 mt-0.5 text-blue-500 flex-shrink-0" />{l}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
                {data.pe_view.exit_considerations && data.pe_view.exit_considerations.length > 0 && (
                  <div>
                    <p className="text-[11px] font-bold text-[#475569] mb-1.5">엑시트 고려사항</p>
                    <ul className="space-y-1">
                      {data.pe_view.exit_considerations.map((e, i) => (
                        <li key={i} className="flex items-start gap-2 text-[12px] text-[#334155]">
                          <Shield className="w-3.5 h-3.5 mt-0.5 text-purple-500 flex-shrink-0" />{e}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
                {data.pe_view.ebitda_assessment && (
                  <div className="bg-blue-50 border border-blue-200 p-3 rounded">
                    <p className="text-[11px] font-bold text-blue-700 mb-1">EBITDA 평가</p>
                    <p className="text-[12px] text-[#334155]">{data.pe_view.ebitda_assessment}</p>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}

      {/* ── 리스크 분류 ── */}
      {data.risks && (
        <div className="grid grid-cols-3 gap-3">
          {(['temporary', 'structural', 'fatal'] as const).map(tier => {
            const items = data.risks![tier];
            if (!items || items.length === 0) return null;
            const cfg = {
              temporary:  { label: '일시적 리스크',  cls: 'border-amber-200 bg-amber-50',   dot: 'bg-amber-400' },
              structural: { label: '구조적 리스크',  cls: 'border-orange-200 bg-orange-50', dot: 'bg-orange-500' },
              fatal:      { label: '치명적 리스크',  cls: 'border-red-200 bg-red-50',       dot: 'bg-red-600' },
            }[tier];
            return (
              <div key={tier} className={`p-3 rounded border ${cfg.cls}`}>
                <p className="text-[11px] font-bold text-[#475569] mb-1.5">{cfg.label}</p>
                <ul className="space-y-1">
                  {items.map((r, i) => (
                    <li key={i} className="flex items-start gap-1.5 text-[11px] text-[#334155]">
                      <span className={`mt-1.5 w-1.5 h-1.5 rounded-full flex-shrink-0 ${cfg.dot}`} />
                      {r}
                    </li>
                  ))}
                </ul>
              </div>
            );
          })}
        </div>
      )}

      {/* ── 신뢰도 ── */}
      {data.confidence && (
        <div className="p-4 border border-[#E2E8F0] rounded">
          <h3 className="text-[12px] font-bold uppercase tracking-widest text-[#64748B] mb-3">분석 신뢰도</h3>
          <div className="space-y-2">
            {([
              ['overall',        '종합 신뢰도'],
              ['data_quality',   '데이터 품질'],
              ['analysis_depth', '분석 깊이'],
            ] as [keyof typeof data.confidence, string][]).map(([k, lbl]) => {
              const v = data.confidence![k];
              if (v === undefined) return null;
              const pct = Math.min(100, Math.max(0, v * 10));
              return (
                <div key={k} className="flex items-center gap-3">
                  <span className="text-[12px] text-[#475569] w-24 flex-shrink-0">{lbl}</span>
                  <div className="flex-1 bg-[#E2E8F0] rounded-full h-1.5">
                    <div
                      className="h-1.5 rounded-full bg-[#2E75B6] transition-all"
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                  <span className="text-[12px] text-[#64748B] w-6 text-right">{v}</span>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* ── 검증 질문 (근거 불충분 시그널 포함) ── */}
      {data.questions_to_validate && data.questions_to_validate.length > 0 && (
        <QuestionsPanel questions={data.questions_to_validate} />
      )}

      {/* ── 근거 맵 ── */}
      {data.evidence_map && Object.keys(data.evidence_map).length > 0 && (
        <EvidenceMap map={data.evidence_map} />
      )}
    </div>
  );
}
