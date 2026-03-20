'use client';

import React from 'react';
import {
  Building2,
  Calendar,
  Brain,
  BarChart3,
  FileText,
  ChevronRight,
  Info,
} from 'lucide-react';
import { CompanySearchResult, AnalysisOptions } from '@/lib/api';

interface AnalysisConfigProps {
  company: CompanySearchResult;
  options: AnalysisOptions;
  onChange: (options: AnalysisOptions) => void;
  onStart: () => void;
  onBack: () => void;
}

const YEAR_OPTIONS = (() => {
  const currentYear = new Date().getFullYear();
  // 전년도가 기본값; 당해연도는 아직 공시 미완이므로 제외
  return Array.from({ length: 5 }, (_, i) => String(currentYear - 1 - i));
})();

const MODULE_OPTIONS = [
  {
    id: 'includeAI',
    icon: Brain,
    color: 'purple',
    label: 'AI 종합 리포트',
    desc: 'Claude AI가 3개년 재무·공시·지배구조를 종합 분석',
    badge: 'PREMIUM',
  },
  {
    id: 'includeFinancial',
    icon: BarChart3,
    color: 'blue',
    label: '재무제표 분석',
    desc: '매출·이익·부채·현금흐름 차트 및 비율 분석',
    badge: null,
  },
  {
    id: 'includeDisclosures',
    icon: FileText,
    color: 'green',
    label: '공시 동향',
    desc: '최근 6개월 공시 목록 및 유형별 분류',
    badge: null,
  },
];

const COLOR_MAP: Record<string, { bg: string; border: string; text: string; check: string }> = {
  purple: {
    bg: 'bg-purple-50',
    border: 'border-purple-300',
    text: 'text-purple-700',
    check: 'bg-purple-600',
  },
  blue: {
    bg: 'bg-blue-50',
    border: 'border-blue-300',
    text: 'text-blue-700',
    check: 'bg-blue-600',
  },
  green: {
    bg: 'bg-emerald-50',
    border: 'border-emerald-300',
    text: 'text-emerald-700',
    check: 'bg-emerald-600',
  },
};

export default function AnalysisConfig({
  company,
  options,
  onChange,
  onStart,
  onBack,
}: AnalysisConfigProps) {
  const toggle = (key: keyof AnalysisOptions) => {
    if (key === 'bsnsYear') return;
    onChange({ ...options, [key]: !options[key as keyof AnalysisOptions] });
  };

  const isValid = options.includeAI || options.includeFinancial || options.includeDisclosures;

  return (
    <div className="w-full max-w-2xl mx-auto">
      {/* 기업 카드 */}
      <div className="bg-white rounded-2xl shadow-lg border border-gray-200 p-6 mb-6">
        <div className="flex items-center gap-4">
          <div className="w-14 h-14 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-xl flex items-center justify-center flex-shrink-0">
            <Building2 className="w-7 h-7 text-white" />
          </div>
          <div className="flex-1 min-w-0">
            <h2 className="text-xl font-bold text-gray-900 truncate">{company.corp_name}</h2>
            <div className="flex items-center gap-3 mt-1 text-sm text-gray-500">
              {company.stock_code && (
                <span className="bg-gray-100 px-2 py-0.5 rounded font-mono">
                  {company.stock_code}
                </span>
              )}
              <span>기업코드: {company.corp_code}</span>
              {company.stock_code && (
                <span className="bg-blue-100 text-blue-700 px-2 py-0.5 rounded text-xs font-medium">
                  상장사
                </span>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* 기준 연도 */}
      <div className="bg-white rounded-2xl shadow-lg border border-gray-200 p-6 mb-6">
        <h3 className="text-base font-semibold text-gray-900 mb-4 flex items-center gap-2">
          <Calendar className="w-5 h-5 text-blue-600" />
          분석 기준 연도
        </h3>
        <div className="flex gap-3 flex-wrap">
          {YEAR_OPTIONS.map((yr) => (
            <button
              key={yr}
              onClick={() => onChange({ ...options, bsnsYear: yr })}
              className={`px-5 py-2.5 rounded-xl font-semibold text-sm border-2 transition-all ${
                options.bsnsYear === yr
                  ? 'bg-blue-600 border-blue-600 text-white shadow-md'
                  : 'border-gray-200 text-gray-600 hover:border-blue-300 hover:text-blue-600'
              }`}
            >
              {yr}년
            </button>
          ))}
        </div>
        <p className="mt-3 text-xs text-gray-400 flex items-center gap-1">
          <Info className="w-3.5 h-3.5" />
          AI 리포트는 선택 연도 포함 3개년 데이터를 자동 수집합니다
        </p>
      </div>

      {/* 분석 모듈 */}
      <div className="bg-white rounded-2xl shadow-lg border border-gray-200 p-6 mb-6">
        <h3 className="text-base font-semibold text-gray-900 mb-4">분석 모듈 선택</h3>
        <div className="space-y-3">
          {MODULE_OPTIONS.map(({ id, icon: Icon, color, label, desc, badge }) => {
            const active = options[id as keyof AnalysisOptions] as boolean;
            const c = COLOR_MAP[color];
            return (
              <button
                key={id}
                onClick={() => toggle(id as keyof AnalysisOptions)}
                className={`w-full text-left p-4 rounded-xl border-2 transition-all ${
                  active ? `${c.bg} ${c.border}` : 'border-gray-200 hover:border-gray-300'
                }`}
              >
                <div className="flex items-start gap-4">
                  {/* 체크박스 */}
                  <div
                    className={`w-5 h-5 rounded border-2 flex items-center justify-center flex-shrink-0 mt-0.5 transition-all ${
                      active
                        ? `${c.check} border-transparent`
                        : 'border-gray-300 bg-white'
                    }`}
                  >
                    {active && (
                      <svg className="w-3 h-3 text-white" viewBox="0 0 12 12" fill="none">
                        <path d="M2 6l3 3 5-5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                      </svg>
                    )}
                  </div>
                  {/* 아이콘 */}
                  <div className={`w-9 h-9 rounded-lg flex items-center justify-center flex-shrink-0 ${active ? c.bg : 'bg-gray-100'}`}>
                    <Icon className={`w-5 h-5 ${active ? c.text : 'text-gray-400'}`} />
                  </div>
                  {/* 텍스트 */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-0.5">
                      <span className={`font-semibold text-sm ${active ? c.text : 'text-gray-700'}`}>
                        {label}
                      </span>
                      {badge && (
                        <span className="bg-purple-100 text-purple-700 text-xs font-bold px-1.5 py-0.5 rounded">
                          {badge}
                        </span>
                      )}
                    </div>
                    <p className="text-xs text-gray-500">{desc}</p>
                  </div>
                </div>
              </button>
            );
          })}
        </div>
      </div>

      {/* 버튼 */}
      <div className="flex gap-3">
        <button
          onClick={onBack}
          className="px-5 py-3.5 rounded-xl border-2 border-gray-200 text-gray-600 font-medium hover:border-gray-300 hover:bg-gray-50 transition-all"
        >
          ← 다시 검색
        </button>
        <button
          onClick={onStart}
          disabled={!isValid}
          className={`flex-1 py-3.5 rounded-xl font-semibold text-base flex items-center justify-center gap-2 transition-all ${
            isValid
              ? 'bg-gradient-to-r from-blue-600 to-indigo-600 text-white shadow-lg hover:shadow-xl hover:-translate-y-0.5'
              : 'bg-gray-200 text-gray-400 cursor-not-allowed'
          }`}
        >
          분석 시작
          <ChevronRight className="w-5 h-5" />
        </button>
      </div>
    </div>
  );
}
