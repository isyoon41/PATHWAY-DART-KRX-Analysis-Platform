'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import {
  ChevronDown, ChevronUp, Database, Brain, BarChart3,
  FileText, Shield, TrendingUp, AlertCircle, Clock,
  Layers, Search, ArrowLeft,
} from 'lucide-react';

// ──────────────────────────────────────────────────────────────────────
// 타입
// ──────────────────────────────────────────────────────────────────────
interface FaqItem {
  q: string;
  a: React.ReactNode;
}

interface FaqSection {
  icon: React.ElementType;
  title: string;
  items: FaqItem[];
}

// ──────────────────────────────────────────────────────────────────────
// FAQ 데이터
// ──────────────────────────────────────────────────────────────────────
const FAQ_SECTIONS: FaqSection[] = [
  {
    icon: Database,
    title: '플랫폼 개요',
    items: [
      {
        q: '이 플랫폼은 무엇을 하는 곳인가요?',
        a: (
          <div className="space-y-2">
            <p>
              PATHWAY 기업분석 플랫폼은 금융감독원 DART(전자공시시스템)와 한국거래소 KRX의 공식 데이터를
              자동으로 수집·분해하여, AI(Gemini)가 투자자 관점에서 심층 분석한 보고서를 제공하는 내부 분석 도구입니다.
            </p>
            <p>
              기업이 제출한 사업보고서 원문을 11개 분석 섹션으로 자동 분해하고, 9개의 전문 분석 모듈이
              VC(벤처캐피탈) 및 PE(사모펀드) 투자 관점에서 각 영역을 심층 분석합니다.
            </p>
          </div>
        ),
      },
      {
        q: '어떤 기업을 분석할 수 있나요?',
        a: (
          <p>
            DART에 사업보고서를 제출하는 모든 국내 상장법인 및 외감 대상 법인을 분석할 수 있습니다.
            기업명 또는 종목코드로 검색하면 됩니다. 단, 사업보고서가 DART에 없는 비상장 중소기업이나
            공시 면제 기업은 분석이 제한될 수 있습니다.
          </p>
        ),
      },
      {
        q: '데이터는 어디서 가져오나요?',
        a: (
          <div className="space-y-3">
            <p>세 가지 공식 출처에서 자동 수집합니다.</p>
            <div className="space-y-2">
              <div className="flex items-start gap-3 bg-[#F7F9FC] border border-[#E2E8F0] p-3">
                <span className="w-1.5 h-1.5 bg-[#0C2340] flex-shrink-0 mt-1.5" />
                <div>
                  <p className="font-semibold text-[#0C2340] text-[13px]">금융감독원 DART</p>
                  <p className="text-[12px] text-[#64748B]">사업보고서, 분기보고서, 반기보고서, 각종 공시 (주주현황, 유상증자, CB 등)</p>
                </div>
              </div>
              <div className="flex items-start gap-3 bg-[#F7F9FC] border border-[#E2E8F0] p-3">
                <span className="w-1.5 h-1.5 bg-[#0C2340] flex-shrink-0 mt-1.5" />
                <div>
                  <p className="font-semibold text-[#0C2340] text-[13px]">한국거래소 KRX</p>
                  <p className="text-[12px] text-[#64748B]">주가 데이터, 거래량, 시가총액, 지수 대비 수익률</p>
                </div>
              </div>
              <div className="flex items-start gap-3 bg-[#F7F9FC] border border-[#E2E8F0] p-3">
                <span className="w-1.5 h-1.5 bg-[#0C2340] flex-shrink-0 mt-1.5" />
                <div>
                  <p className="font-semibold text-[#0C2340] text-[13px]">DART API (구조화 데이터)</p>
                  <p className="text-[12px] text-[#64748B]">XBRL 재무제표, 주주현황 API, 잠정실적 공시 등</p>
                </div>
              </div>
            </div>
          </div>
        ),
      },
    ],
  },
  {
    icon: Layers,
    title: '분석 구조 이해',
    items: [
      {
        q: '사업보고서가 어떻게 분석 데이터로 변환되나요?',
        a: (
          <div className="space-y-3">
            <p>3단계 파이프라인을 통해 처리됩니다.</p>
            <div className="space-y-2">
              <div className="bg-[#F7F9FC] border border-[#E2E8F0] p-4">
                <p className="text-[11px] font-bold text-[#64748B] uppercase tracking-widest mb-2">1단계 — DART HTML 수집 및 12개 섹션 분해</p>
                <p className="text-[13px] text-[#334155]">
                  금감원 공시 규정상 사업보고서는 목차가 법정 양식으로 표준화되어 있습니다.
                  플랫폼은 이를 이용해 HTML 원문을 자동으로 감지하고
                  회사개요·사업내용·위험요인·재무·감사의견·이사회·주주현황·임원·계열회사·이해관계자거래·기타
                  등 12개 섹션으로 분해합니다.
                </p>
              </div>
              <div className="bg-[#F7F9FC] border border-[#E2E8F0] p-4">
                <p className="text-[11px] font-bold text-[#64748B] uppercase tracking-widest mb-2">2단계 — S1~S11 분석 섹션으로 재구성</p>
                <p className="text-[13px] text-[#334155]">
                  12개 원본 섹션을 S1(기업개요)~S11(시장데이터) 분석 섹션으로 재매핑합니다.
                  S9~S11은 DART 공시 검색·API·KRX 주가 데이터 등 외부 소스에서 별도 수집됩니다.
                </p>
              </div>
              <div className="bg-[#F7F9FC] border border-[#E2E8F0] p-4">
                <p className="text-[11px] font-bold text-[#64748B] uppercase tracking-widest mb-2">3단계 — 9개 모듈이 필요한 섹션만 선택하여 AI 분석</p>
                <p className="text-[13px] text-[#334155]">
                  각 모듈은 자신이 필요한 섹션만 가져가서 Gemini AI에 전달합니다.
                  예) 주주현황 모듈은 S5만, 주가변동 모듈은 S11+S10을 사용합니다.
                </p>
              </div>
            </div>
          </div>
        ),
      },
      {
        q: 'S1~S11 섹션은 각각 어떤 내용인가요?',
        a: (
          <div className="overflow-x-auto">
            <table className="w-full text-[13px] border-collapse">
              <thead>
                <tr className="bg-[#0C2340] text-white">
                  <th className="px-3 py-2 text-left font-semibold w-16">섹션</th>
                  <th className="px-3 py-2 text-left font-semibold">내용</th>
                  <th className="px-3 py-2 text-left font-semibold">출처</th>
                </tr>
              </thead>
              <tbody>
                {[
                  ['S1', '기업 개요', 'DART 사업보고서'],
                  ['S2', '사업의 내용', 'DART 사업보고서'],
                  ['S3', '사업부문 상세 정보', 'DART 사업보고서'],
                  ['S4', '위험요인', 'DART 사업보고서'],
                  ['S5', '주주구조', 'DART API'],
                  ['S6', '이사회·임원 현황', 'DART 사업보고서'],
                  ['S7', '재무제표', 'DART XBRL + 사업보고서'],
                  ['S8', '감사의견·재무주석', 'DART 감사보고서'],
                  ['S9', '자본조달 이벤트 (유상증자·CB·BW 등)', 'DART 공시 검색'],
                  ['S10', '잠정실적·이벤트 공시', 'DART API'],
                  ['S11', '주가·시장 데이터', 'KRX'],
                ].map(([id, name, src], i) => (
                  <tr key={id} className={i % 2 === 0 ? 'bg-white' : 'bg-[#F7F9FC]'}>
                    <td className="px-3 py-2 font-bold text-[#0C2340]">{id}</td>
                    <td className="px-3 py-2 text-[#334155]">{name}</td>
                    <td className="px-3 py-2 text-[#64748B]">{src}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ),
      },
    ],
  },
  {
    icon: Brain,
    title: '3가지 분석 유형',
    items: [
      {
        q: '기업 개요 확인 / 모듈별 분석 / 투자심의용 심화 분석의 차이는 무엇인가요?',
        a: (
          <div className="space-y-4">
            <div className="border border-[#E2E8F0] border-t-4 border-t-[#2E75B6] p-4">
              <p className="font-bold text-[#0C2340] text-[14px] mb-1">① 기업 개요 확인</p>
              <p className="text-[12px] text-[#64748B] mb-2">기업 선택 후 &apos;기업 개요 확인&apos; 클릭</p>
              <p className="text-[13px] text-[#334155]">
                재무 데이터·공시 동향·AI 리포트를 한 번에 모아서 보는 <strong>기업 현황 대시보드</strong>입니다.
                DART에서 수집된 재무제표와 공시 내역을 구조화하여 표시하며,
                AI가 전체를 통합 요약한 6개 섹션 리포트를 함께 제공합니다.
                빠른 기업 파악이 목적일 때 사용합니다.
              </p>
            </div>
            <div className="border border-[#E2E8F0] border-t-4 border-t-[#0C2340] p-4">
              <p className="font-bold text-[#0C2340] text-[14px] mb-1">② 모듈별 분석 (추천)</p>
              <p className="text-[12px] text-[#64748B] mb-2">9개 모듈을 각각 선택하여 실행</p>
              <p className="text-[13px] text-[#334155]">
                사업보고서·재무·주주·이사회·주가·자본조달·잠정실적 등 각 영역을
                <strong>VC/PE 투자 관점의 전문 프롬프트</strong>로 심층 분석합니다.
                필요한 모듈만 선택하여 실행할 수 있으며,
                분석 결과는 스코어카드·시그널·리스크·증거 맵 형태로 구조화됩니다.
                투자 검토의 핵심 도구입니다.
              </p>
            </div>
            <div className="border border-[#E2E8F0] border-t-4 border-t-[#7C3AED] p-4">
              <p className="font-bold text-[#0C2340] text-[14px] mb-1">③ 투자심의용 심화 분석</p>
              <p className="text-[12px] text-[#64748B] mb-2">9개 모듈 전체 완료 후에만 실행 가능</p>
              <p className="text-[13px] text-[#334155]">
                9개 모듈의 분석 결과물 전체를 입력으로 받아,
                AI가 <strong>모듈 간 교차 검증·상충 신호 감지·종합 투자 판단</strong>을 수행합니다.
                VC 관점 결론과 PE 관점 결론을 각각 도출하고,
                최종 액션(즉시검토 / 심화분석 / 보류 등)을 권고합니다.
                투자심의 자료 작성에 직접 활용할 수 있습니다.
              </p>
            </div>
          </div>
        ),
      },
      {
        q: '9개 분석 모듈은 각각 무엇을 분석하나요?',
        a: (
          <div className="overflow-x-auto">
            <table className="w-full text-[13px] border-collapse">
              <thead>
                <tr className="bg-[#0C2340] text-white">
                  <th className="px-3 py-2 text-left font-semibold">#</th>
                  <th className="px-3 py-2 text-left font-semibold">모듈명</th>
                  <th className="px-3 py-2 text-left font-semibold">주요 분석 내용</th>
                  <th className="px-3 py-2 text-left font-semibold">사용 섹션</th>
                </tr>
              </thead>
              <tbody>
                {[
                  ['1', '사업보고서 종합 분석', '사업구조·경쟁력·리스크·재무 통합 분석', 'S1·S2·S4·S7·S8'],
                  ['2', '핵심 재무 지표', 'KPI·성장성·수익성·안정성 비율 분석', 'S7·S8'],
                  ['3', '재무제표 완전 분석', '재무제표 전체 심층 분석 + 이상 징후 탐지', 'S7·S8'],
                  ['4', '사업부문 성과', '부문별 매출·마진·성장률 분석', 'S2·S3·S7'],
                  ['5', '주주 구조 분석', '최대주주·지분 변동·오버행 리스크', 'S5·S9'],
                  ['6', '이사회·임원 분석', '지배구조·경영진 역량·ESG 리스크', 'S6'],
                  ['7', '주가 변동 원인 분석', '주가 패턴·이벤트 연계·기술적 신호', 'S10·S11'],
                  ['8', '자본조달 이벤트', '유상증자·CB·BW 구조 및 영향 분석', 'S9·S5'],
                  ['9', '잠정실적 분석', '잠정실적·어닝서프라이즈·가이던스 분석', 'S10·S7'],
                ].map(([num, name, desc, sections], i) => (
                  <tr key={num} className={i % 2 === 0 ? 'bg-white' : 'bg-[#F7F9FC]'}>
                    <td className="px-3 py-2 font-bold text-[#0C2340]">{num}</td>
                    <td className="px-3 py-2 font-semibold text-[#334155]">{name}</td>
                    <td className="px-3 py-2 text-[#64748B]">{desc}</td>
                    <td className="px-3 py-2 text-[#94A3B8] font-mono text-[11px]">{sections}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ),
      },
    ],
  },
  {
    icon: TrendingUp,
    title: 'VC vs PE 관점',
    items: [
      {
        q: 'VC 관점과 PE 관점의 차이는 무엇인가요?',
        a: (
          <div className="space-y-4">
            <p className="text-[13px] text-[#334155]">
              둘 다 기업에 투자하지만 투자 단계와 수익 전략이 근본적으로 다릅니다.
              같은 기업 데이터를 봐도 질문 자체가 다릅니다.
            </p>
            <div className="overflow-x-auto">
              <table className="w-full text-[13px] border-collapse">
                <thead>
                  <tr className="bg-[#0C2340] text-white">
                    <th className="px-3 py-2 text-left font-semibold w-40">항목</th>
                    <th className="px-3 py-2 text-left font-semibold">VC (벤처캐피탈)</th>
                    <th className="px-3 py-2 text-left font-semibold">PE (사모펀드)</th>
                  </tr>
                </thead>
                <tbody>
                  {[
                    ['투자 대상', '초기~성장 단계 기업', '성숙~저평가 기업'],
                    ['핵심 질문', '얼마나 크게 성장할 수 있나?', '가치를 높여서 팔 수 있나?'],
                    ['수익 원천', '매출 폭발 성장 → 기업가치 상승', '비용 절감·EBITDA 증가 → Exit'],
                    ['적자 허용', '적자도 OK (성장률이 핵심)', '현금흐름 안정성 중시'],
                    ['Exit 방식', 'IPO, M&A', '매각, 배당 회수, 2차 매각'],
                    ['보고 포인트', 'Upside Drivers·기술 차별화', 'Value Creation Levers·EBITDA'],
                  ].map(([item, vc, pe], i) => (
                    <tr key={item} className={i % 2 === 0 ? 'bg-white' : 'bg-[#F7F9FC]'}>
                      <td className="px-3 py-2 font-semibold text-[#0C2340]">{item}</td>
                      <td className="px-3 py-2 text-[#334155]">{vc}</td>
                      <td className="px-3 py-2 text-[#334155]">{pe}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="bg-[#EBF2FA] border border-[#C9D8EC] p-4">
              <p className="text-[12px] font-semibold text-[#1F3864] mb-1">예시: 수술 로봇 기업 분석 시</p>
              <p className="text-[13px] text-[#334155]">
                <strong>VC 관점:</strong> &ldquo;수술 로봇 시장 연 30% 성장 → 탑라인 폭발 가능성. 기술 진입장벽은?&rdquo;<br />
                <strong>PE 관점:</strong> &ldquo;EBITDA 마진 개선 가능성은? 3~5년 후 어떤 Buyer에게 어떤 Valuation으로 Exit 가능한가?&rdquo;
              </p>
            </div>
          </div>
        ),
      },
      {
        q: '투자심의용 심화 분석의 최종 액션 권고란 무엇인가요?',
        a: (
          <div className="space-y-2">
            <p className="text-[13px] text-[#334155]">
              9개 모듈 결과를 교차 검증한 후 AI가 아래 중 하나를 권고합니다.
            </p>
            <div className="space-y-2">
              {[
                { label: '즉시 검토', color: 'bg-emerald-50 border-emerald-200 text-emerald-800', desc: '투자 논거가 명확하고 리스크가 관리 가능한 수준. 즉각적인 실사(DD) 진행 권고.' },
                { label: '심화 분석 필요', color: 'bg-amber-50 border-amber-200 text-amber-800', desc: '유망하나 핵심 불확실성이 존재. 추가 데이터 수집 또는 경영진 미팅 후 재검토.' },
                { label: '보류', color: 'bg-slate-50 border-slate-200 text-slate-700', desc: '현재 시점에서 투자 논거 불충분. 트리거 이벤트 발생 시 재검토.' },
                { label: '부정적 검토', color: 'bg-red-50 border-red-200 text-red-800', desc: '복수의 중대 리스크 요인 확인. 투자 진행 비권고.' },
              ].map(({ label, color, desc }) => (
                <div key={label} className={`border p-3 ${color}`}>
                  <p className="font-semibold text-[13px] mb-0.5">{label}</p>
                  <p className="text-[12px]">{desc}</p>
                </div>
              ))}
            </div>
          </div>
        ),
      },
    ],
  },
  {
    icon: Clock,
    title: '소요 시간 및 캐시',
    items: [
      {
        q: '분석에 얼마나 시간이 걸리나요?',
        a: (
          <div className="overflow-x-auto">
            <table className="w-full text-[13px] border-collapse">
              <thead>
                <tr className="bg-[#0C2340] text-white">
                  <th className="px-3 py-2 text-left font-semibold">분석 유형</th>
                  <th className="px-3 py-2 text-left font-semibold">예상 소요 시간</th>
                  <th className="px-3 py-2 text-left font-semibold">비고</th>
                </tr>
              </thead>
              <tbody>
                {[
                  ['기업 개요 확인', '20~60초', 'AI 리포트 포함 시 최대 90초'],
                  ['개별 모듈 분석 (1개)', '15~45초', '캐시 적중 시 즉시'],
                  ['전체 9개 모듈', '3~8분', '모듈별 순차 실행 시'],
                  ['투자심의용 심화 분석', '1~3분', '9개 모듈 결과 전체 입력'],
                ].map(([type, time, note], i) => (
                  <tr key={type} className={i % 2 === 0 ? 'bg-white' : 'bg-[#F7F9FC]'}>
                    <td className="px-3 py-2 font-semibold text-[#334155]">{type}</td>
                    <td className="px-3 py-2 text-[#0C2340] font-bold">{time}</td>
                    <td className="px-3 py-2 text-[#64748B]">{note}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ),
      },
      {
        q: '같은 기업을 다시 분석하면 더 빠른가요?',
        a: (
          <p>
            네. DART에서 수집한 원문 데이터와 AI 분석 결과는 <strong>24시간 캐시</strong>로 저장됩니다.
            동일 기업·동일 연도를 24시간 이내에 재실행하면 DART 재수집 없이 캐시에서 즉시 응답합니다.
            단, AI 분석 결과의 캐시는 모듈·기업·연도 조합이 동일한 경우에만 적중합니다.
          </p>
        ),
      },
    ],
  },
  {
    icon: AlertCircle,
    title: '오류 및 문제 해결',
    items: [
      {
        q: '분석 결과가 JSON 형태로 깨져서 표시됩니다.',
        a: (
          <div className="space-y-2">
            <p>
              AI가 구조화된 JSON 대신 자연어 응답을 반환했을 때 발생하는 현상입니다.
              이 경우 해당 모듈 우측 상단의 <strong>&apos;재분석&apos; 버튼</strong>을 클릭하면
              동일 모듈을 다시 실행합니다. 대부분 재실행으로 해결됩니다.
            </p>
            <p className="text-[12px] text-[#64748B]">
              반복 발생 시 다른 분석 기간(예: 2023년 → 2022년)으로 변경 후 재시도해 보세요.
            </p>
          </div>
        ),
      },
      {
        q: '특정 모듈이 계속 실패합니다.',
        a: (
          <div className="space-y-2">
            <p>아래 순서로 확인하세요.</p>
            <ol className="space-y-1 list-decimal list-inside text-[13px] text-[#334155]">
              <li>해당 기업의 선택 연도 사업보고서가 DART에 제출되어 있는지 확인</li>
              <li>분석 기간 종료 연도를 최신 사업보고서 제출 연도로 변경</li>
              <li>잠정실적 모듈: 해당 연도 잠정실적 공시가 없는 기업은 분석 불가</li>
              <li>자본조달 모듈: 유상증자·CB·BW 이력이 없는 기업은 결과가 제한적일 수 있음</li>
            </ol>
          </div>
        ),
      },
      {
        q: '투자심의용 심화 분석 버튼이 비활성화되어 있습니다.',
        a: (
          <p>
            투자심의용 심화 분석은 <strong>9개 모듈을 모두 완료한 후에만 실행</strong>됩니다.
            버튼 아래에 &ldquo;N개 모듈 완료&rdquo;가 표시되며,
            미완료 모듈이 있는 상태에서 버튼을 클릭하면
            어떤 모듈을 추가로 실행해야 하는지 안내 메시지가 나타납니다.
          </p>
        ),
      },
      {
        q: '기업 검색이 되지 않습니다.',
        a: (
          <div className="space-y-2">
            <p>다음을 확인해 보세요.</p>
            <ul className="space-y-1 text-[13px] text-[#334155]">
              <li className="flex items-start gap-2">
                <span className="w-1.5 h-1.5 bg-[#0C2340] flex-shrink-0 mt-1.5" />
                <span>기업명 전체 또는 일부(2자 이상)로 검색</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="w-1.5 h-1.5 bg-[#0C2340] flex-shrink-0 mt-1.5" />
                <span>6자리 종목코드로 검색 (예: 005930)</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="w-1.5 h-1.5 bg-[#0C2340] flex-shrink-0 mt-1.5" />
                <span>DART에 등록되지 않은 기업은 검색 결과에 나타나지 않습니다</span>
              </li>
            </ul>
          </div>
        ),
      },
    ],
  },
  {
    icon: Shield,
    title: '유의사항',
    items: [
      {
        q: '이 플랫폼의 분석 결과를 투자 결정에 직접 사용해도 되나요?',
        a: (
          <div className="bg-amber-50 border border-amber-200 p-4 space-y-2">
            <p className="font-semibold text-amber-900 text-[14px]">⚠ 투자 자문을 대체하지 않습니다</p>
            <p className="text-[13px] text-amber-800">
              본 플랫폼의 분석 결과는 <strong>정보 제공 목적</strong>으로만 활용해야 하며,
              투자 결정의 최종 판단은 반드시 별도의 실사(Due Diligence)와 전문가 검토를 거쳐야 합니다.
            </p>
            <p className="text-[13px] text-amber-800">
              AI 분석은 공시 데이터를 기반으로 하며, 공시에 포함되지 않은 정보·비공개 정보·
              경영진 인터뷰 결과 등은 반영되지 않습니다.
            </p>
          </div>
        ),
      },
      {
        q: '데이터의 최신성은 어떻게 되나요?',
        a: (
          <p>
            분석 기준 데이터는 DART에 공시된 가장 최근 사업보고서/분기보고서를 사용합니다.
            사업보고서는 통상 결산 후 3개월 이내(3월 말), 분기보고서는 45일 이내 제출됩니다.
            KRX 주가 데이터는 실시간이 아닌 일별 데이터 기준입니다.
            <br /><br />
            단, 분석 결과는 최대 24시간 캐시되므로 당일 신규 공시가 반영되지 않을 수 있습니다.
          </p>
        ),
      },
    ],
  },
];

// ──────────────────────────────────────────────────────────────────────
// FAQ 아코디언 아이템
// ──────────────────────────────────────────────────────────────────────
function FaqAccordionItem({ item, idx }: { item: FaqItem; idx: number }) {
  const [open, setOpen] = useState(false);

  return (
    <div className="border border-[#E2E8F0] bg-white">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-start justify-between gap-4 px-5 py-4 text-left hover:bg-[#F7F9FC] transition-colors"
      >
        <div className="flex items-start gap-3">
          <span className="flex-shrink-0 w-5 h-5 bg-[#0C2340] text-white text-[10px] font-bold flex items-center justify-center mt-0.5">
            Q
          </span>
          <span className="text-[14px] font-semibold text-[#0C2340]">{item.q}</span>
        </div>
        {open
          ? <ChevronUp className="w-4 h-4 text-[#64748B] flex-shrink-0 mt-0.5" />
          : <ChevronDown className="w-4 h-4 text-[#64748B] flex-shrink-0 mt-0.5" />}
      </button>
      {open && (
        <div className="px-5 pb-5 pt-1 border-t border-[#E2E8F0]">
          <div className="flex items-start gap-3">
            <span className="flex-shrink-0 w-5 h-5 bg-[#EBF2FA] text-[#1F3864] text-[10px] font-bold flex items-center justify-center mt-0.5">
              A
            </span>
            <div className="text-[13px] text-[#334155] leading-relaxed flex-1">
              {item.a}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// ──────────────────────────────────────────────────────────────────────
// FAQ 페이지
// ──────────────────────────────────────────────────────────────────────
export default function FaqPage() {
  return (
    <div className="min-h-screen bg-[#F7F9FC]">
      {/* 헤더 */}
      <header className="bg-[#0C2340] border-b border-[#1F3864] sticky top-0 z-10">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-3.5">
          <div className="flex items-center justify-between">
            <Link href="/" className="flex items-center gap-3 hover:opacity-80 transition-opacity">
              <img src="/pathway-logo.png" alt="PATHWAY Partners" className="h-8 w-auto brightness-0 invert opacity-90" />
              <div className="w-px h-7 bg-white/20" />
              <div className="text-left">
                <h1 className="text-[14px] font-bold text-white leading-tight tracking-tight">패스웨이 기업분석 플랫폼</h1>
                <p className="text-[10px] text-white/50 font-medium tracking-widest">DART·KRX Analysis Platform</p>
              </div>
            </Link>
            <Link
              href="/"
              className="flex items-center gap-1.5 text-[12px] text-white/70 hover:text-white transition-colors"
            >
              <ArrowLeft className="w-3.5 h-3.5" />
              분석 화면으로
            </Link>
          </div>
        </div>
      </header>

      {/* 히어로 */}
      <div className="bg-[#0C2340] border-b border-[#1F3864]">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
          <div className="inline-flex items-center gap-2 bg-white/10 border border-white/20 text-white/80 px-3 py-1 text-[11px] font-semibold uppercase tracking-wider mb-4">
            <FileText className="w-3.5 h-3.5" />
            사용 가이드 · FAQ
          </div>
          <h2 className="text-[28px] font-bold text-white mb-2 leading-tight">자주 묻는 질문</h2>
          <p className="text-[14px] text-white/60">
            플랫폼 구조·분석 방법·결과 해석에 관한 주요 질문과 답변을 정리했습니다.
          </p>
        </div>
      </div>

      {/* 섹션 네비게이션 */}
      <div className="sticky top-[57px] z-[9] bg-white border-b border-[#E2E8F0] shadow-sm">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center gap-1 overflow-x-auto py-2 scrollbar-hide">
            {FAQ_SECTIONS.map((section) => {
              const Icon = section.icon;
              return (
                <a
                  key={section.title}
                  href={`#${encodeURIComponent(section.title)}`}
                  className="flex-shrink-0 flex items-center gap-1.5 px-3 py-1.5 text-[12px] font-semibold text-[#64748B] hover:text-[#0C2340] hover:bg-[#F7F9FC] transition-colors border border-transparent hover:border-[#E2E8F0]"
                >
                  <Icon className="w-3.5 h-3.5" />
                  {section.title}
                </a>
              );
            })}
          </div>
        </div>
      </div>

      {/* 본문 */}
      <main className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-10 space-y-12">
        {FAQ_SECTIONS.map((section) => {
          const Icon = section.icon;
          return (
            <section key={section.title} id={encodeURIComponent(section.title)}>
              {/* 섹션 헤더 */}
              <div className="flex items-center gap-3 mb-4">
                <div className="w-8 h-8 bg-[#0C2340] flex items-center justify-center flex-shrink-0">
                  <Icon className="w-4 h-4 text-white" />
                </div>
                <h2 className="text-[18px] font-bold text-[#0C2340]">{section.title}</h2>
                <div className="flex-1 h-px bg-[#E2E8F0]" />
              </div>

              {/* 아코디언 목록 */}
              <div className="space-y-2">
                {section.items.map((item, idx) => (
                  <FaqAccordionItem key={idx} item={item} idx={idx} />
                ))}
              </div>
            </section>
          );
        })}

        {/* 하단 CTA */}
        <div className="bg-[#0C2340] p-8 text-center">
          <p className="text-white/70 text-[13px] mb-4">궁금한 내용이 해결되었나요?</p>
          <Link
            href="/"
            className="inline-flex items-center gap-2 bg-white text-[#0C2340] px-6 py-3 text-[14px] font-bold hover:bg-[#F7F9FC] transition-colors"
          >
            <Search className="w-4 h-4" />
            기업 분석 시작하기
          </Link>
        </div>
      </main>

      {/* 푸터 */}
      <footer className="bg-[#0C2340] border-t border-[#1F3864] mt-8">
        <div className="max-w-5xl mx-auto px-4 py-5 flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-4">
            <img src="/pathway-logo.png" alt="PATHWAY Partners" className="h-7 w-auto opacity-80 brightness-0 invert" />
            <span className="w-px h-5 bg-white/20" />
            <p className="text-[11px] text-white/50">Copyright ⓒ PATHWAY Partners, co, Ltd. All rights reserved.</p>
          </div>
          <div className="flex items-center gap-4 text-[11px] text-white/30">
            <span>데이터 출처: 금융감독원 DART · 한국거래소 KRX</span>
            <span className="w-px h-3 bg-white/20" />
            <span>투자 자문을 대체하지 않습니다</span>
          </div>
        </div>
      </footer>
    </div>
  );
}
