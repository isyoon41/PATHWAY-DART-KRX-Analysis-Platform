'use client';

import React, { useEffect, useState } from 'react';
import {
  Loader2,
  Building2,
  Calendar,
  Globe,
  Phone,
  MapPin,
  FileText,
  TrendingUp,
  AlertCircle
} from 'lucide-react';
import { analysisAPI, ComprehensiveAnalysis } from '@/lib/api';
import SourceBadge from './SourceBadge';

interface CompanyAnalysisProps {
  corpCode: string;
  corpName: string;
}

export default function CompanyAnalysis({ corpCode, corpName }: CompanyAnalysisProps) {
  const [analysis, setAnalysis] = useState<ComprehensiveAnalysis | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const fetchAnalysis = async () => {
      setLoading(true);
      setError('');

      try {
        const data = await analysisAPI.getComprehensive(corpCode);
        setAnalysis(data);
      } catch (err: any) {
        setError(err.response?.data?.detail || '분석 데이터를 불러오는 중 오류가 발생했습니다.');
      } finally {
        setLoading(false);
      }
    };

    fetchAnalysis();
  }, [corpCode]);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="text-center">
          <Loader2 className="w-12 h-12 animate-spin text-blue-600 mx-auto mb-4" />
          <p className="text-gray-600">기업 분석 데이터를 불러오는 중...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 text-red-700 px-6 py-4 rounded-xl flex items-start gap-3">
        <AlertCircle className="w-5 h-5 mt-0.5 flex-shrink-0" />
        <div>
          <h3 className="font-semibold mb-1">오류 발생</h3>
          <p>{error}</p>
        </div>
      </div>
    );
  }

  if (!analysis) {
    return null;
  }

  const { company_info, recent_disclosures, sources_summary } = analysis;

  return (
    <div className="space-y-6">
      {/* 헤더 */}
      <div className="bg-gradient-to-r from-blue-600 to-indigo-600 text-white rounded-xl shadow-lg p-8">
        <div className="flex items-start gap-4">
          <div className="w-16 h-16 bg-white/20 backdrop-blur-sm rounded-xl flex items-center justify-center flex-shrink-0">
            <Building2 className="w-8 h-8" />
          </div>
          <div className="flex-1">
            <h1 className="text-3xl font-bold mb-2">{company_info.corp_name}</h1>
            {company_info.corp_name_eng && (
              <p className="text-blue-100 text-lg mb-3">{company_info.corp_name_eng}</p>
            )}
            <div className="flex items-center gap-4 text-sm">
              {company_info.stock_code && (
                <span className="bg-white/20 px-3 py-1 rounded-full">
                  종목코드: {company_info.stock_code}
                </span>
              )}
              {company_info.ceo_nm && (
                <span className="bg-white/20 px-3 py-1 rounded-full">
                  대표이사: {company_info.ceo_nm}
                </span>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* 기업 기본 정보 */}
      <div className="bg-white rounded-xl shadow-lg p-6">
        <h2 className="text-xl font-bold text-gray-900 mb-4 flex items-center gap-2">
          <Building2 className="w-5 h-5 text-blue-600" />
          기업 기본 정보
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {company_info.est_dt && (
            <div className="flex items-start gap-3 p-3 bg-gray-50 rounded-lg">
              <Calendar className="w-5 h-5 text-gray-600 mt-0.5" />
              <div>
                <p className="text-sm text-gray-600">설립일</p>
                <p className="font-medium text-gray-900">{company_info.est_dt}</p>
              </div>
            </div>
          )}
          {company_info.hm_url && (
            <div className="flex items-start gap-3 p-3 bg-gray-50 rounded-lg">
              <Globe className="w-5 h-5 text-gray-600 mt-0.5" />
              <div className="min-w-0 flex-1">
                <p className="text-sm text-gray-600">홈페이지</p>
                <a
                  href={company_info.hm_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="font-medium text-blue-600 hover:underline truncate block"
                >
                  {company_info.hm_url}
                </a>
              </div>
            </div>
          )}
          {company_info.phn_no && (
            <div className="flex items-start gap-3 p-3 bg-gray-50 rounded-lg">
              <Phone className="w-5 h-5 text-gray-600 mt-0.5" />
              <div>
                <p className="text-sm text-gray-600">전화번호</p>
                <p className="font-medium text-gray-900">{company_info.phn_no}</p>
              </div>
            </div>
          )}
          {company_info.adres && (
            <div className="flex items-start gap-3 p-3 bg-gray-50 rounded-lg">
              <MapPin className="w-5 h-5 text-gray-600 mt-0.5" />
              <div className="min-w-0 flex-1">
                <p className="text-sm text-gray-600">주소</p>
                <p className="font-medium text-gray-900">{company_info.adres}</p>
              </div>
            </div>
          )}
        </div>
        <SourceBadge
          provider={company_info._source.provider}
          url={company_info._source.url}
          retrievedAt={company_info._source.retrieved_at}
        />
      </div>

      {/* 최근 공시 */}
      {recent_disclosures && recent_disclosures.list && recent_disclosures.list.length > 0 && (
        <div className="bg-white rounded-xl shadow-lg p-6">
          <h2 className="text-xl font-bold text-gray-900 mb-4 flex items-center gap-2">
            <FileText className="w-5 h-5 text-blue-600" />
            최근 공시 내역 (최근 3개월)
          </h2>
          <div className="space-y-3">
            {recent_disclosures.list.slice(0, 10).map((disclosure) => (
              <div
                key={disclosure.rcept_no}
                className="border border-gray-200 rounded-lg p-4 hover:border-blue-300 hover:bg-blue-50 transition-colors"
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <h3 className="font-semibold text-gray-900 mb-1">
                      {disclosure.report_nm}
                    </h3>
                    <div className="flex items-center gap-3 text-sm text-gray-600">
                      <span>접수일: {disclosure.rcept_dt}</span>
                      <span>•</span>
                      <span>제출인: {disclosure.flr_nm}</span>
                    </div>
                  </div>
                  <a
                    href={disclosure._source_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm font-medium whitespace-nowrap"
                  >
                    공시 보기
                  </a>
                </div>
              </div>
            ))}
          </div>
          <SourceBadge
            provider={recent_disclosures._source.provider}
            url={recent_disclosures._source.url}
            retrievedAt={recent_disclosures._source.retrieved_at}
          />
        </div>
      )}

      {/* 출처 요약 */}
      <div className="bg-gradient-to-br from-blue-50 to-indigo-50 rounded-xl shadow-lg p-6 border border-blue-200">
        <h2 className="text-xl font-bold text-gray-900 mb-4 flex items-center gap-2">
          <TrendingUp className="w-5 h-5 text-blue-600" />
          데이터 출처 및 신뢰성
        </h2>
        <p className="text-gray-700 mb-4">{sources_summary.description}</p>

        <div className="space-y-3 mb-4">
          {sources_summary.primary_sources.map((source, index) => (
            <div key={index} className="bg-white rounded-lg p-4 border border-blue-200">
              <div className="flex items-start gap-3">
                <div className="w-8 h-8 bg-blue-100 rounded-lg flex items-center justify-center flex-shrink-0">
                  <FileText className="w-4 h-4 text-blue-600" />
                </div>
                <div className="flex-1 min-w-0">
                  <h3 className="font-semibold text-gray-900 mb-1">{source.name}</h3>
                  <p className="text-sm text-gray-600 mb-2">{source.description}</p>
                  <a
                    href={source.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-sm text-blue-600 hover:underline"
                  >
                    {source.url}
                  </a>
                </div>
              </div>
            </div>
          ))}
        </div>

        <div className="bg-blue-100 border border-blue-300 rounded-lg p-4">
          <p className="text-sm text-blue-900">
            <strong>신뢰도:</strong> {sources_summary.data_reliability}
          </p>
          <p className="text-sm text-blue-700 mt-2">
            최종 업데이트: {new Date(sources_summary.last_updated).toLocaleString('ko-KR')}
          </p>
        </div>
      </div>
    </div>
  );
}
