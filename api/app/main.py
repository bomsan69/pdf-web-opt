import logging
import os
import re
import unicodedata
import uuid
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse, FileResponse
from .settings import settings
from .storage import ensure_dirs, write_meta, read_meta
from .queue import get_queue

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI()

BASE = Path(settings.STORAGE_DIR)
ensure_dirs(BASE)

@app.get("/health")
def health_check():
    """
    Health check endpoint for monitoring and load balancers.

    Verifies:
    - API is running
    - Redis connection is available
    - Storage directories are accessible

    Returns:
        Dict with status and component health information

    Raises:
        HTTPException 503: If critical components are unavailable
    """
    health_status = {"status": "healthy", "components": {}}

    # Check Redis connection
    try:
        q = get_queue()
        q.connection.ping()
        health_status["components"]["redis"] = "healthy"
    except Exception as e:
        logger.error(f"Health check failed - Redis: {e}")
        health_status["components"]["redis"] = "unhealthy"
        health_status["status"] = "unhealthy"
        raise HTTPException(status_code=503, detail="Redis unavailable")

    # Check storage accessibility
    try:
        BASE.exists()
        (BASE / "uploads").exists()
        (BASE / "outputs").exists()
        (BASE / "meta").exists()
        health_status["components"]["storage"] = "healthy"
    except Exception as e:
        logger.error(f"Health check failed - Storage: {e}")
        health_status["components"]["storage"] = "unhealthy"
        health_status["status"] = "unhealthy"
        raise HTTPException(status_code=503, detail="Storage unavailable")

    return health_status

def validate_job_id(job_id: str) -> None:
    """Validate job_id to prevent path traversal attacks."""
    if not re.match(r'^[a-f0-9]{32}$', job_id):
        raise HTTPException(status_code=400, detail="Invalid job ID format")

def safe_filename(name: str) -> str:
    """
    Sanitize filename to prevent security issues.
    - Normalizes unicode
    - Removes non-ASCII characters
    - Allows only alphanumeric, dash, underscore, and dot
    - Preserves extension and limits stem length
    """
    # Normalize unicode
    name = unicodedata.normalize('NFKD', name)
    # Remove non-ASCII
    name = name.encode('ascii', 'ignore').decode('ascii')
    # Allow only safe characters (no spaces)
    name = "".join(c for c in name if c.isalnum() or c in ("-", "_", "."))
    # Preserve extension and limit stem length
    stem, ext = os.path.splitext(name)
    if not ext or ext.lower() != '.pdf':
        ext = '.pdf'
    return f"{stem[:150]}{ext}" if stem else "file.pdf"

@app.post("/api/jobs")
async def create_job(file: UploadFile = File(...), dpi: int = 150, jpegq: int = 70):
    if file.content_type not in ("application/pdf", "application/x-pdf"):
        logger.warning(f"Invalid content type: {file.content_type}")
        raise HTTPException(status_code=400, detail="PDF 파일만 업로드 가능합니다.")

    if dpi not in (96, 120, 150):
        logger.warning(f"Invalid dpi value: {dpi}")
        raise HTTPException(status_code=400, detail="dpi는 96, 120, 150 중 하나여야 합니다.")
    if not (40 <= jpegq <= 85):
        logger.warning(f"Invalid jpegq value: {jpegq}")
        raise HTTPException(status_code=400, detail="jpegq는 40~85 범위를 권장합니다.")

    job_id = uuid.uuid4().hex
    orig_name = safe_filename(file.filename or "input.pdf")
    logger.info(f"Creating job {job_id} for file {orig_name} (dpi={dpi}, jpegq={jpegq})")
    in_path = BASE / "uploads" / f"{job_id}_{orig_name}"
    out_path = BASE / "outputs" / f"{job_id}_web.pdf"

    # 스트리밍 저장(메모리 폭발 방지)
    max_bytes = settings.MAX_UPLOAD_MB * 1024 * 1024
    written = 0
    first_chunk = True

    with in_path.open("wb") as f:
        while True:
            chunk = await file.read(1024 * 1024)  # 1MB
            if not chunk:
                break

            # Validate PDF magic number on first chunk
            if first_chunk:
                if len(chunk) < 4 or not chunk.startswith(b'%PDF'):
                    logger.warning(f"Invalid PDF magic number for job {job_id}")
                    try:
                        in_path.unlink(missing_ok=True)
                    except OSError:
                        pass
                    raise HTTPException(status_code=400, detail="유효하지 않은 PDF 파일입니다.")
                first_chunk = False

            # Check size before writing
            if written + len(chunk) > max_bytes:
                logger.warning(f"File size exceeded for job {job_id}: {written + len(chunk)} bytes")
                try:
                    in_path.unlink(missing_ok=True)
                except OSError:
                    pass  # File deletion failed, but continue with error response
                raise HTTPException(status_code=413, detail=f"파일이 너무 큽니다. 최대 {settings.MAX_UPLOAD_MB}MB")

            f.write(chunk)
            written += len(chunk)

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
    logger.info(f"Job {job_id} queued successfully (rq_id={rq_job.id}, size={written} bytes)")

    return JSONResponse({
        "job_id": job_id,
        "status": "queued",
        "status_url": f"{settings.PUBLIC_BASE_URL}/api/jobs/{job_id}",
        "download_url": f"{settings.PUBLIC_BASE_URL}/api/jobs/{job_id}/download",
        "rq_id": rq_job.id,
    })

@app.get("/api/jobs/{job_id}")
def get_job(job_id: str):
    validate_job_id(job_id)
    meta = read_meta(BASE, job_id)
    if not meta:
        logger.warning(f"Job not found: {job_id}")
        raise HTTPException(status_code=404, detail="job not found")
    logger.debug(f"Job status retrieved: {job_id} - {meta.get('status')}")
    return meta

@app.get("/api/jobs/{job_id}/download")
def download(job_id: str):
    validate_job_id(job_id)
    meta = read_meta(BASE, job_id)
    if not meta:
        logger.warning(f"Job not found for download: {job_id}")
        raise HTTPException(status_code=404, detail="job not found")
    if meta.get("status") != "done":
        logger.info(f"Download attempted for incomplete job {job_id} (status={meta.get('status')})")
        raise HTTPException(status_code=409, detail=f"not ready (status={meta.get('status')})")

    out_path = Path(meta["output"])
    if not out_path.exists():
        logger.error(f"Output file missing for job {job_id}: {out_path}")
        raise HTTPException(status_code=500, detail="output missing")

    logger.info(f"Downloading job {job_id}")
    stem = Path(meta.get("original_filename", "input.pdf")).stem
    return FileResponse(
        path=str(out_path),
        media_type="application/pdf",
        filename=f"{stem}_web.pdf",
    )
