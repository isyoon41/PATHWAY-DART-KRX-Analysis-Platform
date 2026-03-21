'use client';

import React, { useEffect, useState } from 'react';
import { Check, Loader2 } from 'lucide-react';
import { AnalysisOptions } from '@/lib/api';

interface Step {
  id: string;
  label: string;
  subLabel: string;
  durationMs: number; // 예상 소요 시간 (시뮬레이션용)
}

function buildSteps(options: AnalysisOptions): Step[] {
  const steps: Step[] = [
    { id: 'company', label: '기업 정보 조회', subLabel: 'DART 기업 기본정보', durationMs: 1500 },
  ];

  if (options.includeFinancial || options.includeAI) {
    steps.push({
      id: 'financial',
      label: '재무제표 수집',
      subLabel: options.includeAI ? '3개년 + 분기 데이터' : '최근 연도 재무제표',
      durationMs: 3000,
    });
  }

  if (options.includeDisclosures || options.includeAI) {
    steps.push({
      id: 'disclosures',
      label: '공시 데이터 수집',
      subLabel: '최근 6개월 공시 목록',
      durationMs: 2000,
    });
  }

  if (options.includeAI) {
    steps.push({
      id: 'governance',
      label: '지배구조 분석',
      subLabel: '최대주주 · 임원 · 계열회사',
      durationMs: 2500,
    });
    steps.push({
      id: 'ai',
      label: 'Gemini AI 분석 생성',
      subLabel: '종합 분석 리포트 작성 중...',
      durationMs: 30000, // AI는 오래 걸림
    });
  }

  return steps;
}

interface LoadingProgressProps {
  options: AnalysisOptions;
  corpName: string;
  /** 백엔드 API가 완료되면 true */
  isDone: boolean;
}

export default function LoadingProgress({ options, corpName, isDone }: LoadingProgressProps) {
  const steps = buildSteps(options);
  const [currentStep, setCurrentStep] = useState(0);
  const [completedSteps, setCompletedSteps] = useState<Set<number>>(new Set());

  // 각 스텝을 예상 시간 기반으로 순차 진행 (시뮬레이션)
  useEffect(() => {
    let elapsed = 0;
    const timers: ReturnType<typeof setTimeout>[] = [];

    steps.forEach((step, idx) => {
      const timer = setTimeout(() => {
        setCurrentStep(idx);
        // AI 스텝이 아닌 경우 짧은 딜레이 후 완료 처리
        if (step.id !== 'ai') {
          const completeTimer = setTimeout(() => {
            setCompletedSteps((prev) => new Set([...prev, idx]));
          }, 800);
          timers.push(completeTimer);
        }
      }, elapsed);
      timers.push(timer);
      elapsed += step.durationMs;
    });

    return () => timers.forEach(clearTimeout);
  }, []); // eslint-disable-line

  // API 완료 시 모든 스텝 완료로 표시
  useEffect(() => {
    if (isDone) {
      setCompletedSteps(new Set(steps.map((_, i) => i)));
    }
  }, [isDone]); // eslint-disable-line

  const totalSteps = steps.length;
  const doneCount = completedSteps.size;
  const progressPct = Math.round((doneCount / totalSteps) * 100);

  return (
    <div className="w-full max-w-lg mx-auto py-8">
      {/* 헤더 */}
      <div className="text-center mb-10">
        <div className="w-16 h-16 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-2xl flex items-center justify-center mx-auto mb-4 shadow-lg">
          <Loader2 className={`w-8 h-8 text-white ${isDone ? '' : 'animate-spin'}`} />
        </div>
        <h2 className="text-2xl font-bold text-gray-900 mb-1">{corpName} 분석 중</h2>
        <p className="text-gray-500 text-sm">
          {isDone ? '분석이 완료되었습니다!' : 'DART와 KRX에서 데이터를 수집하고 있습니다'}
        </p>
      </div>

      {/* 프로그레스 바 */}
      <div className="mb-8">
        <div className="flex justify-between text-xs text-gray-500 mb-1.5">
          <span>진행률</span>
          <span>{progressPct}%</span>
        </div>
        <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
          <div
            className="h-full bg-gradient-to-r from-blue-500 to-indigo-500 rounded-full transition-all duration-700"
            style={{ width: `${progressPct}%` }}
          />
        </div>
      </div>

      {/* 스텝 목록 */}
      <div className="space-y-3">
        {steps.map((step, idx) => {
          const isCompleted = completedSteps.has(idx);
          const isActive = currentStep === idx && !isCompleted;
          const isPending = idx > currentStep;

          return (
            <div
              key={step.id}
              className={`flex items-center gap-4 p-4 rounded-xl border-2 transition-all duration-500 ${
                isCompleted
                  ? 'border-emerald-200 bg-emerald-50'
                  : isActive
                  ? 'border-blue-300 bg-blue-50'
                  : 'border-gray-100 bg-white opacity-50'
              }`}
            >
              {/* 아이콘 */}
              <div
                className={`w-9 h-9 rounded-full flex items-center justify-center flex-shrink-0 transition-all ${
                  isCompleted
                    ? 'bg-emerald-500'
                    : isActive
                    ? 'bg-blue-600'
                    : 'bg-gray-200'
                }`}
              >
                {isCompleted ? (
                  <Check className="w-5 h-5 text-white" />
                ) : isActive ? (
                  <Loader2 className="w-5 h-5 text-white animate-spin" />
                ) : (
                  <span className="text-gray-400 text-sm font-bold">{idx + 1}</span>
                )}
              </div>

              {/* 텍스트 */}
              <div className="flex-1 min-w-0">
                <p
                  className={`font-semibold text-sm ${
                    isCompleted
                      ? 'text-emerald-700'
                      : isActive
                      ? 'text-blue-700'
                      : 'text-gray-400'
                  }`}
                >
                  {step.label}
                </p>
                <p
                  className={`text-xs mt-0.5 ${
                    isCompleted
                      ? 'text-emerald-600'
                      : isActive
                      ? 'text-blue-500'
                      : 'text-gray-400'
                  }`}
                >
                  {step.subLabel}
                </p>
              </div>

              {/* 완료 배지 */}
              {isCompleted && (
                <span className="text-xs text-emerald-600 font-medium bg-emerald-100 px-2 py-0.5 rounded-full">
                  완료
                </span>
              )}
              {isActive && (
                <span className="text-xs text-blue-600 font-medium bg-blue-100 px-2 py-0.5 rounded-full animate-pulse">
                  진행 중
                </span>
              )}
            </div>
          );
        })}
      </div>

      {/* AI 안내 문구 */}
      {options.includeAI && !isDone && (
        <p className="mt-6 text-center text-xs text-gray-400">
          Gemini AI 분석은 데이터 볼륨에 따라 30초~1분이 소요될 수 있습니다
        </p>
      )}
    </div>
  );
}
