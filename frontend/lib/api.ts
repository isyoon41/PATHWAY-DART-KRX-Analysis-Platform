import axios from 'axios';

// rewrites() 덕분에 /api/* → localhost:8000/api/* 로 프록시됨
const api = axios.create({
  baseURL: '',
  headers: { 'Content-Type': 'application/json' },
});

// ─────────────────────────────────────────────
// 공통 타입
// ─────────────────────────────────────────────
export interface SourceInfo {
  provider: string;
  url?: string;
  retrieved_at: string;
  [key: string]: any;
}

// ─────────────────────────────────────────────
// 기업 검색
// ─────────────────────────────────────────────
export interface CompanySearchResult {
  corp_code: string;
  corp_name: string;
  stock_code?: string;
  modify_date?: string;
  _source: SourceInfo;
}

// ─────────────────────────────────────────────
// 기업 기본정보
// ─────────────────────────────────────────────
export interface CompanyInfo {
  corp_code: string;
  corp_name: string;
  corp_name_eng?: string;
  stock_name?: string;
  stock_code?: string;
  ceo_nm?: string;
  corp_cls?: string;
  adres?: string;
  hm_url?: string;
  ir_url?: string;
  phn_no?: string;
  induty_code?: string;
  est_dt?: string;
  listing_dt?: string;
  acc_mt?: string;
  _source: SourceInfo;
}

// ─────────────────────────────────────────────
// 공시
// ─────────────────────────────────────────────
export interface DisclosureItem {
  rcept_no: string;
  corp_cls: string;
  corp_code: string;
  corp_name: string;
  report_nm: string;
  rcept_dt: string;
  flr_nm: string;
  rm?: string;
  _source_url: string;
}

// ─────────────────────────────────────────────
// 재무제표 (structure_financial_data 반환형)
// ─────────────────────────────────────────────
export interface FinancialPeriod {
  revenue?: number;
  operating_profit?: number;
  net_income?: number;
  total_assets?: number;
  current_assets?: number;
  non_current_assets?: number;
  total_liabilities?: number;
  current_liabilities?: number;
  total_equity?: number;
  operating?: number;
  investing?: number;
  financing?: number;
}

export interface FinancialData {
  periods?: string[];
  income_statement?: { current: FinancialPeriod; previous: FinancialPeriod };
  balance_sheet?: { current: FinancialPeriod; previous: FinancialPeriod };
  cash_flow?: { current: FinancialPeriod; previous: FinancialPeriod };
  ratios?: {
    gross_margin_pct?: number;
    operating_margin_pct?: number;
    net_margin_pct?: number;
    debt_ratio_pct?: number;
    current_ratio?: number;
    roa_pct?: number;
    roe_pct?: number;
  };
  growth?: {
    revenue_yoy_pct?: number;
    operating_profit_yoy_pct?: number;
    net_income_yoy_pct?: number;
  };
  _source?: SourceInfo;
}

// ─────────────────────────────────────────────
// 종합 분석 응답
// ─────────────────────────────────────────────
export interface ComprehensiveAnalysis {
  company_info: CompanyInfo;
  analysis_metadata: {
    generated_at: string;
    corp_code: string;
    included_sections: {
      financial: boolean;
      disclosures: boolean;
      market_data: boolean;
    };
  };
  financial_statement?: FinancialData;
  recent_disclosures?: {
    list: DisclosureItem[];
    total_count?: number;
    _source: SourceInfo;
  };
  market_data?: any;
  sources_summary: {
    description: string;
    primary_sources: Array<{ name: string; url: string; description: string }>;
    data_reliability: string;
    last_updated: string;
  };
}

// ─────────────────────────────────────────────
// AI 분석 리포트 응답
// ─────────────────────────────────────────────
export interface AIReportData {
  corp_code: string;
  corp_name: string;
  base_year: string;
  years_covered: string[];
  report: string;
  generated_at: string;
  model: string;
  data_coverage: {
    annual_years: string[];
    quarterly_periods: string[];
    has_governance: boolean;
    disclosure_count: number;
  };
  _source: SourceInfo;
}

// ─────────────────────────────────────────────
// 분석 설정
// ─────────────────────────────────────────────
export interface AnalysisOptions {
  bsnsYear: string;
  includeAI: boolean;
  includeFinancial: boolean;
  includeDisclosures: boolean;
}

// ─────────────────────────────────────────────
// API 함수
// ─────────────────────────────────────────────
export const companyAPI = {
  search: async (query: string): Promise<CompanySearchResult[]> => {
    const response = await api.get('/api/companies/search', { params: { query } });
    return response.data;
  },

  getInfo: async (corpCode: string): Promise<CompanyInfo> => {
    const response = await api.get(`/api/companies/${corpCode}`);
    return response.data;
  },

  getDisclosures: async (
    corpCode: string,
    bgnDe: string,
    endDe: string,
    pageNo = 1,
    pageCount = 10,
  ) => {
    const response = await api.get(`/api/companies/${corpCode}/disclosures`, {
      params: { bgn_de: bgnDe, end_de: endDe, page_no: pageNo, page_count: pageCount },
    });
    return response.data;
  },

  getFinancial: async (corpCode: string, bsnsYear: string, reprtCode = '11011') => {
    const response = await api.get(`/api/companies/${corpCode}/financial`, {
      params: { bsns_year: bsnsYear, reprt_code: reprtCode },
    });
    return response.data;
  },
};

export const analysisAPI = {
  getComprehensive: async (
    corpCode: string,
    includeFinancial = true,
    includeDisclosures = true,
    includeMarketData = true,
  ): Promise<ComprehensiveAnalysis> => {
    const response = await api.get(`/api/analysis/${corpCode}/comprehensive`, {
      params: {
        include_financial: includeFinancial,
        include_disclosures: includeDisclosures,
        include_market_data: includeMarketData,
      },
    });
    return response.data;
  },

  getAIReport: async (corpCode: string, bsnsYear?: string): Promise<AIReportData> => {
    const response = await api.get(`/api/analysis/${corpCode}/ai-report`, {
      params: bsnsYear ? { bsns_year: bsnsYear } : {},
      timeout: 180_000, // Claude 분석은 최대 3분 허용
    });
    return response.data;
  },

  getSummary: async (corpCode: string) => {
    const response = await api.get(`/api/analysis/${corpCode}/summary`);
    return response.data;
  },
};

export default api;
