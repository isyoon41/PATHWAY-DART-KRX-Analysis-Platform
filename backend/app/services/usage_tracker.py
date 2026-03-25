"""
일별 Gemini API 사용량 추적기 (메모리 기반, 자정 자동 리셋)
"""
import threading
from datetime import date, datetime, timezone, timedelta

# 무료 티어 일일 한도
LIMITS = {
    "flash":      {"requests": 1500, "label": "gemini-2.0-flash"},
    "flash_meta": {"requests": 500,  "label": "gemini-2.5-flash-preview"},
}

# 한국 시간 자정 기준 리셋 (UTC+9)
KST = timezone(timedelta(hours=9))


class DailyUsageTracker:
    def __init__(self):
        self._lock = threading.Lock()
        self._date = self._today()
        self._requests    = {"flash": 0, "flash_meta": 0}
        self._in_tokens   = {"flash": 0, "flash_meta": 0}
        self._out_tokens  = {"flash": 0, "flash_meta": 0}

    def _today(self) -> str:
        return datetime.now(KST).strftime("%Y-%m-%d")

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
            now_kst = datetime.now(KST)
            # 다음 자정까지 남은 시간
            tomorrow = (now_kst + timedelta(days=1)).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            seconds_to_reset = int((tomorrow - now_kst).total_seconds())

            result = {
                "date":            self._date,
                "reset_in_seconds": seconds_to_reset,
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
