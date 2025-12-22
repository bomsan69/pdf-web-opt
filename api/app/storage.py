import json
from pathlib import Path
from typing import Any, Dict

def ensure_dirs(base: Path):
    (base / "uploads").mkdir(parents=True, exist_ok=True)
    (base / "outputs").mkdir(parents=True, exist_ok=True)
    (base / "meta").mkdir(parents=True, exist_ok=True)

def meta_path(base: Path, job_id: str) -> Path:
    return base / "meta" / f"{job_id}.json"

def write_meta(base: Path, job_id: str, data: Dict[str, Any]):
    p = meta_path(base, job_id)
    p.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

def read_meta(base: Path, job_id: str) -> Dict[str, Any]:
    p = meta_path(base, job_id)
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))
