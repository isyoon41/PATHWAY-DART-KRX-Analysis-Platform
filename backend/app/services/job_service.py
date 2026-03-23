"""
백그라운드 작업 관리 서비스 (인메모리)

메타 분석 등 장시간 소요 작업을 비동기로 실행하고
job_id 폴링으로 결과를 조회합니다.

제약: 서버 재시작 시 작업 기록이 초기화됩니다.
       Railway 재배포 전 실행 중인 작업은 소실됩니다.
"""
import uuid
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta

# ── 작업 저장소 ────────────────────────────────────────────────────────
_JOBS: Dict[str, Dict] = {}

JobStatus = str  # "pending" | "running" | "completed" | "failed"


def create_job(corp_code: str, task_type: str, meta: Dict = None) -> str:
    """작업 생성 → job_id 반환"""
    job_id = str(uuid.uuid4())
    _JOBS[job_id] = {
        "job_id":     job_id,
        "corp_code":  corp_code,
        "task_type":  task_type,
        "status":     "pending",
        "progress":   0,           # 0~100 진행률
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "result":     None,
        "error":      None,
        **(meta or {}),
    }
    return job_id


def get_job(job_id: str) -> Optional[Dict]:
    """작업 조회 → 없으면 None"""
    return _JOBS.get(job_id)


def update_job(
    job_id: str,
    status: JobStatus,
    result: Any = None,
    error: str  = None,
    progress: int = None,
) -> None:
    """작업 상태 업데이트"""
    if job_id not in _JOBS:
        return
    updates: Dict = {
        "status":     status,
        "updated_at": datetime.now().isoformat(),
    }
    if result   is not None: updates["result"]   = result
    if error    is not None: updates["error"]    = error
    if progress is not None: updates["progress"] = progress
    _JOBS[job_id].update(updates)


def list_jobs(corp_code: str = None, limit: int = 20) -> List[Dict]:
    """작업 목록 (최신순)"""
    jobs = list(_JOBS.values())
    if corp_code:
        jobs = [j for j in jobs if j.get("corp_code") == corp_code]
    jobs.sort(key=lambda j: j.get("created_at", ""), reverse=True)
    return jobs[:limit]


def cleanup_old_jobs(hours: int = 24) -> int:
    """완료된 오래된 작업 정리 → 삭제 수 반환"""
    cutoff = datetime.now() - timedelta(hours=hours)
    to_delete = [
        jid for jid, job in _JOBS.items()
        if job.get("status") in ("completed", "failed")
        and datetime.fromisoformat(job.get("updated_at", "2000-01-01")) < cutoff
    ]
    for jid in to_delete:
        del _JOBS[jid]
    return len(to_delete)
