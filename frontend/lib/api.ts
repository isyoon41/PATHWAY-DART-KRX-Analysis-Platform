import axios from 'axios';

// 백엔드 URL: 환경변수 NEXT_PUBLIC_BACKEND_URL 우선, 없으면 localhost:8000
// Vercel 배포 시: NEXT_PUBLIC_BACKEND_URL 을 백엔드 서버 주소로 설정
const BACKEND_URL =
  process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: BACKEND_URL,
  timeout: 120_000,           // 2분 타임아웃
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
  periods?: { current: string; previous: string; two_years_ago?: string };
  income_statement?: { current: FinancialPeriod; previous: FinancialPeriod; two_years_ago?: FinancialPeriod };
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
  startYear: string;   // 분석 시작 연도 (예: "2021")
  startQtr: number;    // 시작 분기 1~4
  endYear: string;     // 분석 종료 연도 (예: "2024")
  endQtr: number;      // 종료 분기 1~4
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
    endYear?: string,
  ): Promise<ComprehensiveAnalysis> => {
    const response = await api.get(`/api/analysis/${corpCode}/comprehensive`, {
      params: {
        include_financial: includeFinancial,
        include_disclosures: includeDisclosures,
        include_market_data: includeMarketData,
        ...(endYear ? { bsns_year: endYear } : {}),
      },
    });
    return response.data;
  },

  getAIReport: async (
    corpCode: string,
    opts: { startYear?: string; startQtr?: number; endYear?: string; endQtr?: number } = {},
  ): Promise<AIReportData> => {
    const params: Record<string, string | number> = {};
    if (opts.startYear) params.start_year = Number(opts.startYear);
    if (opts.startQtr)  params.start_qtr  = opts.startQtr;
    if (opts.endYear)   params.end_year   = Number(opts.endYear);
    if (opts.endQtr)    params.end_qtr    = opts.endQtr;
    const response = await api.get(`/api/analysis/${corpCode}/ai-report`, {
      params,
      timeout: 180_000, // Gemini 분석은 최대 3분 허용
    });
    return response.data;
  },

  getSummary: async (corpCode: string) => {
    const response = await api.get(`/api/analysis/${corpCode}/summary`);
    return response.data;
  },
};

export default api;
