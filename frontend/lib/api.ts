import axios from 'axios';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 타입 정의
export interface SourceInfo {
  provider: string;
  url: string;
  retrieved_at: string;
  additional_info?: Record<string, any>;
}

export interface CompanySearchResult {
  corp_code: string;
  corp_name: string;
  stock_code?: string;
  modify_date?: string;
  _source: SourceInfo;
}

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
  acc_mt?: string;
  _source: SourceInfo;
}

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
  financial_statement?: any;
  recent_disclosures?: {
    list: DisclosureItem[];
    _source: SourceInfo;
  };
  market_data?: any;
  sources_summary: {
    description: string;
    primary_sources: Array<{
      name: string;
      url: string;
      description: string;
    }>;
    data_reliability: string;
    last_updated: string;
  };
}

// API 함수들
export const companyAPI = {
  search: async (query: string): Promise<CompanySearchResult[]> => {
    const response = await api.get(`/api/companies/search`, {
      params: { query },
    });
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
    pageNo: number = 1,
    pageCount: number = 10
  ) => {
    const response = await api.get(`/api/companies/${corpCode}/disclosures`, {
      params: {
        bgn_de: bgnDe,
        end_de: endDe,
        page_no: pageNo,
        page_count: pageCount,
      },
    });
    return response.data;
  },

  getFinancial: async (
    corpCode: string,
    bsnsYear: string,
    reprtCode: string = '11011'
  ) => {
    const response = await api.get(`/api/companies/${corpCode}/financial`, {
      params: {
        bsns_year: bsnsYear,
        reprt_code: reprtCode,
      },
    });
    return response.data;
  },
};

export const analysisAPI = {
  getComprehensive: async (
    corpCode: string,
    includeFinancial: boolean = true,
    includeDisclosures: boolean = true,
    includeMarketData: boolean = true
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

  getSummary: async (corpCode: string) => {
    const response = await api.get(`/api/analysis/${corpCode}/summary`);
    return response.data;
  },
};

export default api;
