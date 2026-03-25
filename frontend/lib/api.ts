import axios from 'axios';

// 백엔드 URL: 환경변수 NEXT_PUBLIC_BACKEND_URL 우선
// Vercel 배포 시: NEXT_PUBLIC_BACKEND_URL="" 로 설정하면 Vercel rewrites 프록시 사용
// 로컬 개발 시: NEXT_PUBLIC_BACKEND_URL=http://localhost:8000 설정
const BACKEND_URL =
  process.env.NEXT_PUBLIC_BACKEND_URL ?? 'http://localhost:8000';

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
// VC/PE 모듈 결과 (strict JSON skeleton)
// ─────────────────────────────────────────────

// evidence_map 배열 아이템 (백엔드 skeleton 기준)
export interface VcpeEvidenceItem {
  point: string;
  source_sections?: string[];
  assessment_type?: 'fact' | 'inference' | string;
}

// 스코어카드 항목 — v2: {score, basis} 구조 / v1 폴백: 숫자
export interface VcpeScorecardEntry {
  score: number;
  basis?: string;     // 근거 수치 (예: "영업이익률 2.1%, 전년 5.3%")
}

export interface VcpeScorecard {
  성장성?: number;
  수익성?: number;
  현금창출?: number;
  자본효율?: number;
  거버넌스?: number;
  [key: string]: number | VcpeScorecardEntry | undefined;
}

export interface VcpeSignal {
  // v2 강화 스키마 (5-field)
  claim?: string;
  data_point?: string;
  source_section?: string;
  delta_or_threshold?: string;        // Layer 1: 업종 평균·전기 대비 차이값
  investment_implication?: string;
  // 구 스키마 하위호환
  signal?: string;
  evidence?: string;
  importance?: 'high' | 'medium' | 'low' | string;
}

// Layer 3: 구조화된 리스크 항목
export interface VcpeRiskItem {
  description: string;
  evidence?: string;
  source_section?: string;
  context?: string;   // structural: 반복 기간 / fatal: Exit 영향
}

export interface VcpeVcView {
  summary?: string;
  upside_drivers?: string[];
  key_risks?: string[];
  entry_strategy?: string;
}

export interface VcpePeView {
  summary?: string;
  value_creation_levers?: string[];
  exit_considerations?: string[];
  ebitda_assessment?: string;
}

export interface VcpeConfidence {
  overall?: number;
  data_quality?: number;
  analysis_depth?: number;
}

export interface VcpeRisks {
  temporary?: string[];
  structural?: string[];
  fatal?: string[];
}

export interface VcpeModuleResultData {
  one_line_summary?: string;
  scorecard?: VcpeScorecard;
  key_facts?: string[];
  positive_signals?: VcpeSignal[];
  negative_signals?: VcpeSignal[];
  vc_view?: VcpeVcView;
  pe_view?: VcpePeView;
  recommended_action?: string;
  // evidence_map: 백엔드 skeleton은 배열, 구형은 Record — 둘 다 허용
  evidence_map?: VcpeEvidenceItem[] | Record<string, string>;
  confidence?: VcpeConfidence | number;  // 백엔드 skeleton이 숫자(0.0)로 반환할 수 있음
  risks?: VcpeRisks;
  questions_to_validate?: string[];
  structural_insights?: string[];
  // Layer 3: 구조화된 리스크 (최상위 필드, data.risks 구형 아님)
  temporary_issues?: (VcpeRiskItem | string)[];
  structural_risks?:  (VcpeRiskItem | string)[];
  fatal_risks?:       (VcpeRiskItem | string)[];
  [key: string]: any;
}

export interface ModuleResult {
  module_id: string;
  module_name: string;
  corp_name: string;
  corp_code?: string;
  base_year?: string;
  period: string;
  generated_at: string;
  model: string;
  report?: string;                      // 마크다운 폴백
  result?: VcpeModuleResultData;        // strict JSON
  incremental?: boolean;
}

// ─────────────────────────────────────────────
// 메타 분석 / 백그라운드 작업
// ─────────────────────────────────────────────
export interface JobStatus {
  job_id: string;
  corp_code: string;
  task_type: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  progress: number;
  created_at: string;
  updated_at: string;
  result?: any;
  error?: string;
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

  // ── VC/PE 모듈 분석 ──────────────────────────────────────────────
  runModule: async (
    corpCode: string,
    moduleId: string,
    endYear?: string,
  ): Promise<ModuleResult> => {
    const params = endYear ? { end_year: endYear } : {};
    const response = await api.post(
      `/api/analysis/${corpCode}/module/${moduleId}`,
      null,
      { params, timeout: 300_000 },
    );
    return response.data;
  },

  // ── 증분(PATCH) 분석 ─────────────────────────────────────────────
  runIncrementalModule: async (
    corpCode: string,
    moduleId: string,
    endYear: string,
    prevResult?: VcpeModuleResultData,
  ): Promise<ModuleResult> => {
    const response = await api.patch(
      `/api/analysis/${corpCode}/module/${moduleId}`,
      { end_year: endYear, prev_result: prevResult ?? null },
      { timeout: 300_000 },
    );
    return response.data;
  },

  // ── 비동기 메타 분석 시작 ────────────────────────────────────────
  startMetaAnalysisAsync: async (
    corpCode: string,
    endYear?: string,
  ): Promise<{ job_id: string; status: string; poll_url: string }> => {
    const params = endYear ? { end_year: endYear } : {};
    const response = await api.post(
      `/api/analysis/${corpCode}/meta-analysis/async`,
      null,
      { params },
    );
    return response.data;
  },

  // ── 동기 메타 분석 (기존 유지) ───────────────────────────────────
  runMetaAnalysis: async (
    corpCode: string,
    endYear?: string,
  ) => {
    const params = endYear ? { end_year: endYear } : {};
    const response = await api.post(
      `/api/analysis/${corpCode}/meta-analysis`,
      null,
      { params, timeout: 600_000 },
    );
    return response.data;
  },

  // ── 작업 폴링 ────────────────────────────────────────────────────
  pollJob: async (jobId: string): Promise<JobStatus> => {
    const response = await api.get(`/api/analysis/jobs/${jobId}`);
    return response.data;
  },
};

export default api;
