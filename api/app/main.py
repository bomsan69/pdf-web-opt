import uuid
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse, FileResponse
from .settings import settings
from .storage import ensure_dirs, write_meta, read_meta
from .queue import get_queue

app = FastAPI()

BASE = Path(settings.STORAGE_DIR)
ensure_dirs(BASE)

def safe_filename(name: str) -> str:
    # 아주 단순한 정리(실서비스면 더 엄격히)
    return "".join(c for c in name if c.isalnum() or c in ("-", "_", ".", " ")).strip()[:180] or "file.pdf"

@app.post("/api/jobs")
async def create_job(file: UploadFile = File(...), dpi: int = 150, jpegq: int = 70):
    if file.content_type not in ("application/pdf", "application/x-pdf"):
        raise HTTPException(status_code=400, detail="PDF 파일만 업로드 가능합니다.")

    if dpi not in (96, 120, 150):
        raise HTTPException(status_code=400, detail="dpi는 96, 120, 150 중 하나여야 합니다.")
    if not (40 <= jpegq <= 85):
        raise HTTPException(status_code=400, detail="jpegq는 40~85 범위를 권장합니다.")

    job_id = uuid.uuid4().hex
    orig_name = safe_filename(file.filename or "input.pdf")
    in_path = BASE / "uploads" / f"{job_id}_{orig_name}"
    out_path = BASE / "outputs" / f"{job_id}_web.pdf"

    # 스트리밍 저장(메모리 폭발 방지)
    max_bytes = settings.MAX_UPLOAD_MB * 1024 * 1024
    written = 0
    with in_path.open("wb") as f:
        while True:
            chunk = await file.read(1024 * 1024)  # 1MB
            if not chunk:
                break
            written += len(chunk)
            if written > max_bytes:
                try:
                    in_path.unlink(missing_ok=True)
                except:
                    pass
                raise HTTPException(status_code=413, detail=f"파일이 너무 큽니다. 최대 {settings.MAX_UPLOAD_MB}MB")
            f.write(chunk)

    write_meta(BASE, job_id, {
        "job_id": job_id,
        "status": "queued",
        "input": str(in_path),
        "output": str(out_path),
        "dpi": dpi,
        "jpegq": jpegq,
        "error": None,
        "original_filename": orig_name,
    })

    q = get_queue()
    rq_job = q.enqueue("worker.process_pdf", job_id, dpi, jpegq)

    return JSONResponse({
        "job_id": job_id,
        "status": "queued",
        "status_url": f"{settings.PUBLIC_BASE_URL}/api/jobs/{job_id}",
        "download_url": f"{settings.PUBLIC_BASE_URL}/api/jobs/{job_id}/download",
        "rq_id": rq_job.id,
    })

@app.get("/api/jobs/{job_id}")
def get_job(job_id: str):
    meta = read_meta(BASE, job_id)
    if not meta:
        raise HTTPException(status_code=404, detail="job not found")
    return meta

@app.get("/api/jobs/{job_id}/download")
def download(job_id: str):
    meta = read_meta(BASE, job_id)
    if not meta:
        raise HTTPException(status_code=404, detail="job not found")
    if meta.get("status") != "done":
        raise HTTPException(status_code=409, detail=f"not ready (status={meta.get('status')})")

    out_path = Path(meta["output"])
    if not out_path.exists():
        raise HTTPException(status_code=500, detail="output missing")

    stem = Path(meta.get("original_filename", "input.pdf")).stem
    return FileResponse(
        path=str(out_path),
        media_type="application/pdf",
        filename=f"{stem}_web.pdf",
    )
