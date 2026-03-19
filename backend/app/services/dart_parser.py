"""
DART 공시 문서 파서

DART 공시 자료(HTML)를 표준 목차 기준으로 섹션별 분해하여
AI 분석에 최적화된 구조로 변환합니다.

DART 사업보고서는 금융감독원 고시에 의해 목차가 표준화되어 있어
섹션 경계를 자동으로 감지할 수 있습니다.
"""
import re
import httpx
from bs4 import BeautifulSoup, Tag
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass, field


# ──────────────────────────────────────────────────
# 섹션 정의: DART 사업보고서 표준 목차 (법정 양식)
# 출처: 증권의 발행 및 공시 등에 관한 규정 시행세칙
# ──────────────────────────────────────────────────
SECTION_PATTERNS = [
    # (섹션 코드, 표시명, 정규표현식 패턴 목록)
    ("company_overview",   "회사의 개요",            [r"회사의\s*개요", r"I\.\s*회사의\s*개요"]),
    ("business_content",   "사업의 내용",            [r"사업의\s*내용", r"II\.\s*사업의\s*내용"]),
    ("financial_info",     "재무에 관한 사항",        [r"재무에\s*관한\s*사항", r"III\.\s*재무"]),
    ("mda",                "경영진단 및 분석의견",    [r"경영진단", r"MD&A", r"이사의\s*경영진단"]),
    ("audit_opinion",      "감사인의 감사의견",       [r"감사인의\s*감사의견", r"감사보고서"]),
    ("board_governance",   "이사회 및 지배구조",      [r"이사회", r"회사의\s*기관"]),
    ("shareholders",       "주주에 관한 사항",        [r"주주에\s*관한", r"주주현황"]),
    ("executives",         "임원 및 직원",            [r"임원\s*및\s*직원", r"임원현황"]),
    ("affiliates",         "계열회사",                [r"계열회사", r"관계회사"]),
    ("related_party",      "이해관계자 거래",         [r"이해관계자", r"특수관계인"]),
    ("other",              "기타 사항",               [r"그\s*밖에", r"기타\s*사항"]),
]

# 재무제표 주요 계정 패턴 (XBRL 계정명 기반)
FINANCIAL_ACCOUNTS = {
    "revenue":           ["매출액", "영업수익", "수익(매출액)"],
    "operating_profit":  ["영업이익", "영업손익"],
    "net_income":        ["당기순이익", "당기순손익"],
    "total_assets":      ["자산총계", "총자산"],
    "total_equity":      ["자본총계", "총자본"],
    "total_liabilities": ["부채총계", "총부채"],
    "operating_cashflow":["영업활동현금흐름", "영업활동으로인한현금흐름"],
}


@dataclass
class ReportSection:
    """공시 보고서의 단일 섹션"""
    code: str                          # 섹션 식별 코드
    title: str                         # 섹션 제목
    content: str                       # 원본 텍스트 (정제된)
    tables: List[Dict] = field(default_factory=list)   # 표 데이터
    key_numbers: Dict = field(default_factory=dict)    # 추출된 수치
    char_count: int = 0                # 텍스트 길이
    source_url: str = ""               # 출처 URL


@dataclass
class ParsedReport:
    """파싱 완료된 공시 보고서"""
    rcept_no: str          # 접수번호
    corp_code: str         # 기업 고유번호
    corp_name: str         # 기업명
    report_type: str       # 보고서 유형 (사업보고서 등)
    report_date: str       # 보고서 기준 날짜
    sections: Dict[str, ReportSection] = field(default_factory=dict)
    raw_html_url: str = "" # 원본 HTML URL
    parsed_at: str = ""    # 파싱 시각


class DARTReportParser:
    """
    DART 공시 HTML을 섹션별로 분해하는 파서

    사업보고서의 표준화된 목차 구조를 이용하여
    각 섹션의 경계를 감지하고 내용을 추출합니다.
    """

    def __init__(self, dart_api_key: str):
        self.api_key = dart_api_key
        self.base_url = "https://opendart.fss.or.kr"

    async def fetch_report_index(self, rcept_no: str) -> List[Dict]:
        """
        공시 접수번호로 문서 목록 조회

        하나의 공시는 여러 파일(본문, 첨부)로 구성됩니다.
        본문(사업보고서) HTML 파일의 URL을 추출합니다.
        """
        url = f"{self.base_url}/api/document.json"
        params = {"crtfc_key": self.api_key, "rcept_no": rcept_no}

        async with httpx.AsyncClient() as client:
            resp = await client.get(url, params=params, timeout=30.0)
            resp.raise_for_status()
            data = resp.json()

        if data.get("status") != "000":
            raise ValueError(f"DART API 오류: {data.get('message')}")

        # 본문 파일만 필터링 (첨부서류 제외)
        files = data.get("list", [])
        return [f for f in files if f.get("ord") == "1"]  # ord=1이 본문

    async def fetch_document_html(self, rcept_no: str, file_url: str) -> str:
        """공시 HTML 문서 다운로드"""
        # DART 뷰어 URL 구성
        viewer_url = f"{self.base_url}/dsaf001/main.do?rcpNo={rcept_no}"
        direct_url = f"{self.base_url}{file_url}" if file_url.startswith("/") else file_url

        async with httpx.AsyncClient(
            headers={"User-Agent": "Mozilla/5.0"},
            follow_redirects=True,
            timeout=30.0
        ) as client:
            resp = await client.get(direct_url)
            resp.raise_for_status()
            return resp.text

    def parse_sections(self, html: str, rcept_no: str, corp_info: Dict) -> ParsedReport:
        """
        HTML 문서를 섹션별로 분해

        전략:
        1. HTML을 BeautifulSoup으로 파싱
        2. 표준 목차 패턴으로 섹션 헤딩 위치 감지
        3. 인접한 헤딩 사이의 내용을 각 섹션에 할당
        4. 표는 별도로 구조화하여 저장
        5. 숫자 데이터 추출
        """
        soup = BeautifulSoup(html, "lxml")

        # 불필요한 태그 제거 (스크립트, 스타일, 네비게이션)
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()

        report = ParsedReport(
            rcept_no=rcept_no,
            corp_code=corp_info.get("corp_code", ""),
            corp_name=corp_info.get("corp_name", ""),
            report_type=corp_info.get("report_type", "사업보고서"),
            report_date=corp_info.get("report_date", ""),
            raw_html_url=f"{self.base_url}/dsaf001/main.do?rcpNo={rcept_no}",
            parsed_at=datetime.now().isoformat(),
        )

        # 전체 텍스트에서 섹션 경계 감지
        section_boundaries = self._detect_section_boundaries(soup)

        # 섹션별로 내용 추출
        all_elements = list(soup.find_all(True))
        for idx, (sec_code, sec_title, start_pos, end_pos) in enumerate(section_boundaries):
            section_elements = all_elements[start_pos:end_pos]
            section = self._extract_section(
                sec_code, sec_title, section_elements, rcept_no
            )
            report.sections[sec_code] = section

        # 섹션이 하나도 감지 안 된 경우: 전체를 단일 섹션으로
        if not report.sections:
            full_text = self._clean_text(soup.get_text())
            tables = self._extract_tables(soup)
            report.sections["full_document"] = ReportSection(
                code="full_document",
                title="전체 문서",
                content=full_text[:50000],  # 최대 50K자
                tables=tables,
                char_count=len(full_text),
                source_url=report.raw_html_url,
            )

        return report

    def _detect_section_boundaries(
        self, soup: BeautifulSoup
    ) -> List[Tuple[str, str, int, int]]:
        """표준 목차 패턴으로 섹션 경계 감지"""
        all_elements = list(soup.find_all(True))
        boundaries = []
        found_sections = []

        for i, elem in enumerate(all_elements):
            text = elem.get_text(strip=True)
            if len(text) < 3 or len(text) > 80:
                continue

            # 헤딩 요소이거나 강조 텍스트인 경우만 체크
            is_heading = elem.name in ["h1", "h2", "h3", "h4", "h5", "h6"]
            is_bold = elem.name in ["b", "strong"] or (
                elem.get("style", "") and "bold" in elem.get("style", "")
            )

            if not (is_heading or is_bold):
                continue

            for sec_code, sec_title, patterns in SECTION_PATTERNS:
                if any(re.search(p, text, re.IGNORECASE) for p in patterns):
                    # 이미 찾은 섹션은 중복 등록 방지
                    if sec_code not in [s[0] for s in found_sections]:
                        found_sections.append((sec_code, sec_title, i))
                    break

        # 경계 구간 계산 (현재 섹션 시작 ~ 다음 섹션 시작)
        total = len(all_elements)
        for idx, (sec_code, sec_title, start) in enumerate(found_sections):
            end = found_sections[idx + 1][2] if idx + 1 < len(found_sections) else total
            boundaries.append((sec_code, sec_title, start, end))

        return boundaries

    def _extract_section(
        self,
        code: str,
        title: str,
        elements: List[Tag],
        rcept_no: str,
    ) -> ReportSection:
        """섹션 요소들에서 텍스트, 표, 수치 추출"""
        # 임시 soup 생성
        temp_html = "".join(str(e) for e in elements)
        temp_soup = BeautifulSoup(temp_html, "lxml")

        # 텍스트 정제
        raw_text = temp_soup.get_text(separator="\n")
        clean = self._clean_text(raw_text)

        # 표 구조화
        tables = self._extract_tables(temp_soup)

        # 주요 수치 추출 (재무 섹션에만 의미 있음)
        key_numbers = {}
        if code in ("financial_info", "mda"):
            key_numbers = self._extract_numbers(clean, tables)

        return ReportSection(
            code=code,
            title=title,
            content=clean[:30000],   # 섹션당 최대 30K자
            tables=tables[:10],      # 표 최대 10개
            key_numbers=key_numbers,
            char_count=len(clean),
            source_url=f"{self.base_url}/dsaf001/main.do?rcpNo={rcept_no}",
        )

    def _clean_text(self, text: str) -> str:
        """텍스트 정제: 공백/특수문자 정규화"""
        # 연속 공백 및 줄바꿈 정리
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = re.sub(r"[ \t]{2,}", " ", text)
        # 의미없는 기호 제거
        text = re.sub(r"[─━─\-]{5,}", "---", text)
        # 페이지 번호 패턴 제거
        text = re.sub(r"^\s*\d+\s*$", "", text, flags=re.MULTILINE)
        return text.strip()

    def _extract_tables(self, soup: BeautifulSoup) -> List[Dict]:
        """HTML 표를 구조화된 딕셔너리로 변환"""
        tables = []
        for tbl in soup.find_all("table"):
            rows = []
            for tr in tbl.find_all("tr"):
                row = [td.get_text(strip=True) for td in tr.find_all(["th", "td"])]
                if any(cell for cell in row):  # 빈 행 제외
                    rows.append(row)

            if len(rows) >= 2:  # 헤더 + 1행 이상
                tables.append({
                    "headers": rows[0],
                    "rows": rows[1:],
                    "row_count": len(rows) - 1,
                })

        return tables

    def _extract_numbers(self, text: str, tables: List[Dict]) -> Dict:
        """재무 관련 핵심 수치 추출"""
        numbers = {}

        # 텍스트에서 숫자 패턴 추출 (단위: 백만원, 억원 등)
        amount_pattern = r"([\d,]+)\s*(백만원|억원|원|천원)"
        for match in re.finditer(amount_pattern, text):
            value_str = match.group(1).replace(",", "")
            unit = match.group(2)
            try:
                value = int(value_str)
                # 단위 정규화 (백만원 기준)
                if unit == "억원":
                    value *= 100
                elif unit == "원":
                    value //= 1_000_000
                elif unit == "천원":
                    value //= 1_000

                # 주변 텍스트로 계정명 추정
                start = max(0, match.start() - 30)
                context = text[start:match.start()].strip()
                for account_key, account_names in FINANCIAL_ACCOUNTS.items():
                    if any(name in context for name in account_names):
                        numbers[account_key] = value
                        break
            except ValueError:
                continue

        return numbers


class SectionAnalyzer:
    """
    분해된 섹션별 분석 로직

    각 섹션의 특성에 맞는 분석을 수행합니다.
    - 재무 섹션: 수치 계산 및 비율 분석
    - 사업 내용: 주요 사업 및 리스크 키워드 추출
    - 감사의견: 의견 유형 분류
    """

    # 감사의견 유형 키워드
    AUDIT_OPINIONS = {
        "적정":   ["적정의견", "적정", "unqualified"],
        "한정":   ["한정의견", "한정", "qualified"],
        "부적정": ["부적정의견", "부적정", "adverse"],
        "의견거절": ["의견거절", "disclaimer"],
    }

    # 리스크 키워드 (사업의 내용 섹션)
    RISK_KEYWORDS = [
        "경쟁 심화", "규제", "환율", "금리", "원자재", "인력 부족",
        "기술 변화", "시장 포화", "소송", "분쟁", "환경", "ESG",
        "사이버보안", "공급망", "지정학적",
    ]

    def analyze_section(self, section: ReportSection) -> Dict:
        """섹션 유형에 따라 적합한 분석 수행"""
        base = {
            "section_code": section.code,
            "section_title": section.title,
            "char_count": section.char_count,
            "table_count": len(section.tables),
            "source_url": section.source_url,
            "retrieved_at": datetime.now().isoformat(),
        }

        if section.code == "financial_info":
            base.update(self._analyze_financial(section))
        elif section.code == "business_content":
            base.update(self._analyze_business(section))
        elif section.code == "audit_opinion":
            base.update(self._analyze_audit(section))
        elif section.code == "mda":
            base.update(self._analyze_mda(section))
        elif section.code == "company_overview":
            base.update(self._analyze_overview(section))

        return base

    def _analyze_financial(self, section: ReportSection) -> Dict:
        """재무 섹션: 주요 지표 및 비율 계산"""
        nums = section.key_numbers
        result = {"key_financials": nums}

        # 수익성 비율
        if "net_income" in nums and "total_assets" in nums and nums["total_assets"]:
            result["roa"] = round(nums["net_income"] / nums["total_assets"] * 100, 2)
        if "net_income" in nums and "total_equity" in nums and nums["total_equity"]:
            result["roe"] = round(nums["net_income"] / nums["total_equity"] * 100, 2)

        # 부채비율
        if "total_liabilities" in nums and "total_equity" in nums and nums["total_equity"]:
            result["debt_ratio"] = round(
                nums["total_liabilities"] / nums["total_equity"] * 100, 2
            )

        # 표 개수로 재무 정보 충실도 평가
        result["data_richness"] = "풍부" if len(section.tables) >= 5 else "보통"
        return result

    def _analyze_business(self, section: ReportSection) -> Dict:
        """사업의 내용 섹션: 주요 사업 및 리스크 추출"""
        content = section.content
        found_risks = [kw for kw in self.RISK_KEYWORDS if kw in content]

        # 사업 부문 감지 (숫자로 열거된 패턴)
        segments = re.findall(r"[①②③④⑤⑥⑦⑧⑨]|[가나다라마바사][.)]", content)

        return {
            "risk_keywords": found_risks,
            "risk_count": len(found_risks),
            "business_segments_detected": len(segments),
        }

    def _analyze_audit(self, section: ReportSection) -> Dict:
        """감사의견 섹션: 의견 유형 분류"""
        content = section.content
        detected = "확인 불가"

        for opinion_type, keywords in self.AUDIT_OPINIONS.items():
            if any(kw in content for kw in keywords):
                detected = opinion_type
                break

        # 계속기업 불확실성 여부
        going_concern = "계속기업" in content and (
            "불확실성" in content or "의문" in content
        )

        return {
            "audit_opinion": detected,
            "going_concern_risk": going_concern,
            "opinion_note": "감사의견은 반드시 원문을 직접 확인하세요",
        }

    def _analyze_mda(self, section: ReportSection) -> Dict:
        """MD&A 섹션: 경영진 전망 및 주요 언급 추출"""
        content = section.content

        # 긍정/부정 신호어
        positive = ["성장", "증가", "개선", "확대", "달성", "호조"]
        negative = ["감소", "하락", "부진", "어려움", "위축", "손실"]

        pos_count = sum(content.count(w) for w in positive)
        neg_count = sum(content.count(w) for w in negative)

        tone = "중립"
        if pos_count > neg_count * 1.5:
            tone = "긍정적"
        elif neg_count > pos_count * 1.5:
            tone = "부정적"

        return {
            "management_tone": tone,
            "positive_signals": pos_count,
            "negative_signals": neg_count,
        }

    def _analyze_overview(self, section: ReportSection) -> Dict:
        """회사 개요 섹션: 핵심 기업 정보 추출"""
        content = section.content

        # 업종 코드/명칭 패턴
        industry = re.search(r"주요\s*사업\s*[:：]?\s*(.{5,30})", content)

        return {
            "industry_mention": industry.group(1).strip() if industry else None,
        }


# 모듈 레벨 인스턴스 (config에서 주입)
def create_parser(api_key: str) -> DARTReportParser:
    return DARTReportParser(api_key)

analyzer = SectionAnalyzer()
