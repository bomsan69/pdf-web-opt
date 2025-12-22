import os
import json
import subprocess
from pathlib import Path
import redis
from rq import Worker, Queue, Connection

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
STORAGE_DIR = os.getenv("STORAGE_DIR", "/data")
CONCURRENCY = int(os.getenv("WORKER_CONCURRENCY", "1"))

BASE = Path(STORAGE_DIR)

def meta_path(job_id: str) -> Path:
    return BASE / "meta" / f"{job_id}.json"

def read_meta(job_id: str) -> dict:
    p = meta_path(job_id)
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))

def write_meta(job_id: str, data: dict):
    p = meta_path(job_id)
    p.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

def process_pdf(job_id: str, dpi: int = 150, jpegq: int = 70):
    meta = read_meta(job_id)
    if not meta:
        raise RuntimeError("meta not found")

    in_path = Path(meta["input"])
    out_path = Path(meta["output"])
    out_path.parent.mkdir(parents=True, exist_ok=True)

    meta["status"] = "processing"
    meta["error"] = None
    write_meta(job_id, meta)

    cmd = [
        "gs",
        "-sDEVICE=pdfwrite",
        "-dCompatibilityLevel=1.4",
        "-dDownsampleColorImages=true", f"-dColorImageResolution={dpi}",
        "-dDownsampleGrayImages=true",  f"-dGrayImageResolution={dpi}",
        "-dDownsampleMonoImages=true",  f"-dMonoImageResolution={dpi}",
        "-dColorImageDownsampleType=/Average",
        "-dGrayImageDownsampleType=/Average",
        "-dMonoImageDownsampleType=/Average",
        f"-dJPEGQ={jpegq}",
        "-dNOPAUSE", "-dQUIET", "-dBATCH",
        f"-sOutputFile={str(out_path)}",
        str(in_path),
    ]

    r = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if r.returncode != 0 or not out_path.exists():
        meta["status"] = "failed"
        meta["error"] = (r.stderr or "Ghostscript failed").strip()[:4000]
        write_meta(job_id, meta)
        raise RuntimeError(meta["error"])

    meta["status"] = "done"
    meta["error"] = None
    write_meta(job_id, meta)
    return {"ok": True, "job_id": job_id, "output": str(out_path)}

def main():
    r = redis.from_url(REDIS_URL)
    with Connection(r):
        qs = [Queue("pdf")]
        w = Worker(qs)
        w.work(with_scheduler=True)

if __name__ == "__main__":
    main()
