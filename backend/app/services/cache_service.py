"""
파일 기반 모듈 분석 결과 캐시 서비스

키: {corp_code}_{module_id}_{base_year}
TTL: 24시간
저장 경로: backend/cache/*.json
"""
import json
import hashlib
from pathlib import Path
from datetime import datetime, timedelta
from typing import Any, Optional

_CACHE_DIR  = Path(__file__).parent.parent.parent / "cache"
_TTL_HOURS  = 24


def _ensure_dir() -> None:
    _CACHE_DIR.mkdir(exist_ok=True)


def _cache_path(corp_code: str, module_id: str, base_year: str) -> Path:
    key      = f"{corp_code}_{module_id}_{base_year}"
    filename = hashlib.md5(key.encode()).hexdigest() + ".json"
    return _CACHE_DIR / filename


def get_cached(corp_code: str, module_id: str, base_year: str) -> Optional[Any]:
    """캐시 히트 → 저장 데이터 반환 / 미스·만료 → None"""
    path = _cache_path(corp_code, module_id, base_year)
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            entry = json.load(f)
        cached_at = datetime.fromisoformat(entry.get("cached_at", "2000-01-01"))
        if datetime.now() - cached_at > timedelta(hours=_TTL_HOURS):
            path.unlink(missing_ok=True)
            return None
        return entry.get("data")
    except Exception:
        return None


def set_cached(corp_code: str, module_id: str, base_year: str, data: Any) -> None:
    """결과를 캐시에 저장 (실패 시 무시)"""
    try:
        _ensure_dir()
        path = _cache_path(corp_code, module_id, base_year)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(
                {"cached_at": datetime.now().isoformat(), "data": data},
                f, ensure_ascii=False,
            )
    except Exception:
        pass


def invalidate(corp_code: str, module_id: str, base_year: str) -> None:
    """특정 캐시 무효화"""
    _cache_path(corp_code, module_id, base_year).unlink(missing_ok=True)


def invalidate_corp(corp_code: str) -> int:
    """특정 기업의 모든 캐시 무효화 → 삭제 수 반환"""
    if not _CACHE_DIR.exists():
        return 0
    count = 0
    for f in _CACHE_DIR.glob("*.json"):
        try:
            with open(f, "r", encoding="utf-8") as fp:
                entry = json.load(fp)
            if entry.get("data", {}).get("corp_name") or corp_code in f.name:
                f.unlink(missing_ok=True)
                count += 1
        except Exception:
            pass
    return count


def clear_all() -> int:
    """전체 캐시 삭제 → 삭제 파일 수 반환"""
    if not _CACHE_DIR.exists():
        return 0
    count = 0
    for f in _CACHE_DIR.glob("*.json"):
        f.unlink(missing_ok=True)
        count += 1
    return count


def get_stats() -> dict:
    """캐시 통계 반환"""
    if not _CACHE_DIR.exists():
        return {"total": 0, "valid": 0, "expired": 0, "size_kb": 0}
    total = expired = size = 0
    for f in _CACHE_DIR.glob("*.json"):
        total += 1
        size  += f.stat().st_size
        try:
            with open(f, "r", encoding="utf-8") as fp:
                entry = json.load(fp)
            cached_at = datetime.fromisoformat(entry.get("cached_at", "2000-01-01"))
            if datetime.now() - cached_at > timedelta(hours=_TTL_HOURS):
                expired += 1
        except Exception:
            expired += 1
    return {
        "total":   total,
        "valid":   total - expired,
        "expired": expired,
        "size_kb": round(size / 1024, 1),
    }
