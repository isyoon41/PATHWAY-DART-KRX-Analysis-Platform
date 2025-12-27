'use client';

import React, { useState } from 'react';
import { Search, Loader2, Building2 } from 'lucide-react';
import { companyAPI, CompanySearchResult } from '@/lib/api';
import SourceBadge from './SourceBadge';

interface CompanySearchProps {
  onSelectCompany: (corpCode: string, corpName: string) => void;
}

export default function CompanySearch({ onSelectCompany }: CompanySearchProps) {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<CompanySearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!query.trim()) {
      setError('기업명을 입력해주세요.');
      return;
    }

    setLoading(true);
    setError('');
    setResults([]);

    try {
      const data = await companyAPI.search(query);
      setResults(data);

      if (data.length === 0) {
        setError('검색 결과가 없습니다.');
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || '검색 중 오류가 발생했습니다.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="w-full max-w-4xl mx-auto">
      <form onSubmit={handleSearch} className="mb-6">
        <div className="relative">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="기업명 또는 종목코드를 입력하세요 (예: 삼성전자, SK하이닉스)"
            className="w-full px-4 py-4 pl-12 pr-24 text-lg border-2 border-gray-300 rounded-xl focus:outline-none focus:border-blue-500 transition-colors"
          />
          <Search className="absolute left-4 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5" />
          <button
            type="submit"
            disabled={loading}
            className="absolute right-2 top-1/2 transform -translate-y-1/2 bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700 disabled:bg-gray-400 transition-colors flex items-center gap-2"
          >
            {loading ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                검색 중...
              </>
            ) : (
              '검색'
            )}
          </button>
        </div>
      </form>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg mb-4">
          {error}
        </div>
      )}

      {results.length > 0 && (
        <div className="bg-white rounded-xl shadow-lg overflow-hidden">
          <div className="px-6 py-4 bg-gray-50 border-b border-gray-200">
            <h3 className="text-lg font-semibold text-gray-900">
              검색 결과 ({results.length}개)
            </h3>
          </div>
          <div className="divide-y divide-gray-200">
            {results.map((company) => (
              <div
                key={company.corp_code}
                className="px-6 py-4 hover:bg-blue-50 transition-colors cursor-pointer"
                onClick={() => onSelectCompany(company.corp_code, company.corp_name)}
              >
                <div className="flex items-start justify-between">
                  <div className="flex items-start gap-3 flex-1">
                    <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center flex-shrink-0">
                      <Building2 className="w-5 h-5 text-blue-600" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <h4 className="text-base font-semibold text-gray-900 mb-1">
                        {company.corp_name}
                      </h4>
                      <div className="flex items-center gap-3 text-sm text-gray-600">
                        <span>종목코드: {company.stock_code || 'N/A'}</span>
                        <span>•</span>
                        <span>기업코드: {company.corp_code}</span>
                      </div>
                      <div className="mt-2">
                        <SourceBadge
                          provider={company._source.provider}
                          url={company._source.url}
                          retrievedAt={company._source.retrieved_at}
                          compact
                        />
                      </div>
                    </div>
                  </div>
                  <div className="ml-4">
                    <button
                      className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm font-medium"
                      onClick={() => onSelectCompany(company.corp_code, company.corp_name)}
                    >
                      분석하기
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
