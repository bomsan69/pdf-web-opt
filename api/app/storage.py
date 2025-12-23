import json
from pathlib import Path
from typing import Any, Dict

def ensure_dirs(base: Path) -> None:
    """
    Ensure required storage directories exist.

    Args:
        base: Base storage directory path
    """
    (base / "uploads").mkdir(parents=True, exist_ok=True)
    (base / "outputs").mkdir(parents=True, exist_ok=True)
    (base / "meta").mkdir(parents=True, exist_ok=True)

def meta_path(base: Path, job_id: str) -> Path:
    """
    Get metadata file path for a job.

    Args:
        base: Base storage directory path
        job_id: Unique job identifier

    Returns:
        Path to the metadata JSON file
    """
    return base / "meta" / f"{job_id}.json"

def write_meta(base: Path, job_id: str, data: Dict[str, Any]) -> None:
    """
    Write job metadata to disk.

    Args:
        base: Base storage directory path
        job_id: Unique job identifier
        data: Metadata dictionary to save
    """
    p = meta_path(base, job_id)
    p.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

def read_meta(base: Path, job_id: str) -> Dict[str, Any]:
    """
    Read job metadata from disk.

    Args:
        base: Base storage directory path
        job_id: Unique job identifier

    Returns:
        Metadata dictionary, or empty dict if not found
    """
    p = meta_path(base, job_id)
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))
