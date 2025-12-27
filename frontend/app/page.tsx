'use client';

import React, { useState } from 'react';
import { TrendingUp, Database, Shield } from 'lucide-react';
import CompanySearch from '@/components/CompanySearch';
import CompanyAnalysis from '@/components/CompanyAnalysis';

export default function Home() {
  const [selectedCompany, setSelectedCompany] = useState<{
    corpCode: string;
    corpName: string;
  } | null>(null);

  const handleSelectCompany = (corpCode: string, corpName: string) => {
    setSelectedCompany({ corpCode, corpName });
  };

  const handleBackToSearch = () => {
    setSelectedCompany(null);
  };

  return (
    <main className="min-h-screen">
      {/* 헤더 */}
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="flex items-center justify-between">
            <div
              className="flex items-center gap-3 cursor-pointer"
              onClick={handleBackToSearch}
            >
              <div className="w-12 h-12 bg-gradient-to-br from-blue-600 to-indigo-600 rounded-xl flex items-center justify-center">
                <TrendingUp className="w-6 h-6 text-white" />
              </div>
              <div>
                <h1 className="text-2xl font-bold text-gray-900">
                  DART·KRX 기업분석 플랫폼
                </h1>
                <p className="text-sm text-gray-600">
                  실시간 기업 분석 및 근거 기반 리포트
                </p>
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* 메인 컨텐츠 */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {!selectedCompany ? (
          <>
            {/* 히어로 섹션 */}
            <div className="text-center mb-12">
              <h2 className="text-4xl font-bold text-gray-900 mb-4">
                신뢰할 수 있는 기업 분석 플랫폼
              </h2>
              <p className="text-xl text-gray-600 mb-8">
                DART 공시 데이터와 KRX 시장 데이터를 기반으로<br />
                종합적인 기업 분석 리포트를 제공합니다
              </p>

              {/* 특징 카드 */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-12">
                <div className="bg-white rounded-xl shadow-lg p-6 border-t-4 border-blue-600">
                  <div className="w-12 h-12 bg-blue-100 rounded-xl flex items-center justify-center mx-auto mb-4">
                    <Database className="w-6 h-6 text-blue-600" />
                  </div>
                  <h3 className="text-lg font-semibold text-gray-900 mb-2">
                    실시간 데이터
                  </h3>
                  <p className="text-gray-600 text-sm">
                    DART와 KRX에서 실시간으로 수집된 최신 기업 정보와 공시 데이터
                  </p>
                </div>

                <div className="bg-white rounded-xl shadow-lg p-6 border-t-4 border-indigo-600">
                  <div className="w-12 h-12 bg-indigo-100 rounded-xl flex items-center justify-center mx-auto mb-4">
                    <Shield className="w-6 h-6 text-indigo-600" />
                  </div>
                  <h3 className="text-lg font-semibold text-gray-900 mb-2">
                    근거 기반 분석
                  </h3>
                  <p className="text-gray-600 text-sm">
                    모든 데이터에 출처와 근거를 명시하여 신뢰도 확보
                  </p>
                </div>

                <div className="bg-white rounded-xl shadow-lg p-6 border-t-4 border-purple-600">
                  <div className="w-12 h-12 bg-purple-100 rounded-xl flex items-center justify-center mx-auto mb-4">
                    <TrendingUp className="w-6 h-6 text-purple-600" />
                  </div>
                  <h3 className="text-lg font-semibold text-gray-900 mb-2">
                    종합 리포트
                  </h3>
                  <p className="text-gray-600 text-sm">
                    재무제표, 공시 내역, 시장 데이터를 한눈에 확인
                  </p>
                </div>
              </div>
            </div>

            {/* 검색 */}
            <CompanySearch onSelectCompany={handleSelectCompany} />

            {/* 안내사항 */}
            <div className="mt-12 bg-blue-50 border border-blue-200 rounded-xl p-6">
              <h3 className="font-semibold text-blue-900 mb-2">사용 안내</h3>
              <ul className="space-y-2 text-sm text-blue-800">
                <li>• 기업명 또는 종목코드로 검색하여 상세 분석 리포트를 확인하세요</li>
                <li>• 모든 데이터는 금융감독원(DART) 및 한국거래소(KRX) 공식 출처에서 수집됩니다</li>
                <li>• 각 데이터 항목에 출처 정보가 표시되어 신뢰성을 확인할 수 있습니다</li>
                <li>• 본 플랫폼은 투자 자문이 아닌 정보 제공 목적으로 운영됩니다</li>
              </ul>
            </div>
          </>
        ) : (
          <>
            {/* 뒤로가기 버튼 */}
            <button
              onClick={handleBackToSearch}
              className="mb-6 px-4 py-2 text-blue-600 hover:text-blue-800 hover:bg-blue-50 rounded-lg transition-colors flex items-center gap-2"
            >
              ← 검색으로 돌아가기
            </button>

            {/* 분석 리포트 */}
            <CompanyAnalysis
              corpCode={selectedCompany.corpCode}
              corpName={selectedCompany.corpName}
            />
          </>
        )}
      </div>

      {/* 푸터 */}
      <footer className="bg-gray-900 text-white mt-20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="text-center">
            <p className="text-gray-400 text-sm">
              © 2024 DART·KRX 기업분석 플랫폼. 모든 데이터는 공식 출처에서 수집됩니다.
            </p>
            <p className="text-gray-500 text-xs mt-2">
              본 플랫폼의 정보는 투자 판단의 참고 자료이며, 투자 자문을 대체할 수 없습니다.
            </p>
          </div>
        </div>
      </footer>
    </main>
  );
}
