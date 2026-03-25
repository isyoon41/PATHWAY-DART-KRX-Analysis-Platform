"""
일별 Gemini API 사용량 추적기 (메모리 기반, 자정 자동 리셋)
Gemini 무료 티어 쿼터는 미국 태평양 시간(PT) 자정 기준으로 리셋됩니다.
- PDT (3월 둘째 일요일 ~ 11월 첫째 일요일): UTC-7 → 한국시간 16:00
- PST (그 외): UTC-8 → 한국시간 17:00
"""
import threading
from datetime import date, datetime, timezone, timedelta

# 무료 티어 일일 한도
LIMITS = {
    "flash":      {"requests": 1500, "label": "gemini-2.0-flash"},
    "flash_meta": {"requests": 500,  "label": "gemini-2.5-flash-preview"},
}

# 한국 시간 (표시용)
KST = timezone(timedelta(hours=9))


def _pacific_tz() -> tuple[timezone, str]:
    """현재 날짜 기준 미국 태평양 시간대(PDT/PST) 반환"""
    now_utc = datetime.now(timezone.utc)
    year = now_utc.year
    # 미국 DST 시작: 3월 둘째 일요일
    march_1 = date(year, 3, 1)
    dst_start = march_1 + timedelta(days=(6 - march_1.weekday()) % 7 + 7)
    # 미국 DST 종료: 11월 첫째 일요일
    nov_1 = date(year, 11, 1)
    dst_end = nov_1 + timedelta(days=(6 - nov_1.weekday()) % 7)
    today = now_utc.date()
    if dst_start <= today < dst_end:
        return timezone(timedelta(hours=-7)), "PDT"
    return timezone(timedelta(hours=-8)), "PST"


class DailyUsageTracker:
    def __init__(self):
        self._lock = threading.Lock()
        self._date = self._today()
        self._requests    = {"flash": 0, "flash_meta": 0}
        self._in_tokens   = {"flash": 0, "flash_meta": 0}
        self._out_tokens  = {"flash": 0, "flash_meta": 0}

    def _today(self) -> str:
        pt, _ = _pacific_tz()
        return datetime.now(pt).strftime("%Y-%m-%d")

    def _check_reset(self):
        today = self._today()
        if self._date != today:
            self._date = today
            self._requests   = {"flash": 0, "flash_meta": 0}
            self._in_tokens  = {"flash": 0, "flash_meta": 0}
            self._out_tokens = {"flash": 0, "flash_meta": 0}

    def _model_key(self, model: str) -> str:
        """모델명으로 집계 키 결정"""
        if "preview" in model or "2.5" in model:
            return "flash_meta"
        return "flash"

    def record(self, model: str, input_tokens: int, output_tokens: int):
        key = self._model_key(model)
        with self._lock:
            self._check_reset()
            self._requests[key]   += 1
            self._in_tokens[key]  += input_tokens
            self._out_tokens[key] += output_tokens

    def get_stats(self) -> dict:
        with self._lock:
            self._check_reset()
            pt, tz_label = _pacific_tz()
            now_pt = datetime.now(pt)
            # 다음 태평양 시간 자정까지 남은 초
            tomorrow_pt = (now_pt + timedelta(days=1)).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            seconds_to_reset = int((tomorrow_pt - now_pt).total_seconds())
            # KST로 리셋 시각 표시
            reset_kst = tomorrow_pt.astimezone(KST)

            result = {
                "date":             self._date,
                "reset_in_seconds": seconds_to_reset,
                "reset_time_kst":   reset_kst.strftime("%H:%M"),
                "reset_tz":         tz_label,
                "models": {}
            }
            for key, meta in LIMITS.items():
                used_req = self._requests[key]
                limit_req = meta["requests"]
                in_tok  = self._in_tokens[key]
                out_tok = self._out_tokens[key]
                result["models"][key] = {
                    "label":          meta["label"],
                    "requests_used":  used_req,
                    "requests_limit": limit_req,
                    "requests_pct":   round(used_req / limit_req * 100, 1),
                    "input_tokens":   in_tok,
                    "output_tokens":  out_tok,
                    "total_tokens":   in_tok + out_tok,
                }
            return result


usage_tracker = DailyUsageTracker()
