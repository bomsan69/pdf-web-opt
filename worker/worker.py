import os
import json
import logging
import subprocess
from pathlib import Path
import redis
from rq import Worker, Queue

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
STORAGE_DIR = os.getenv("STORAGE_DIR", "/data")
CONCURRENCY = int(os.getenv("WORKER_CONCURRENCY", "1"))

BASE = Path(STORAGE_DIR)

def meta_path(job_id: str) -> Path:
    """
    Get metadata file path for a job.

    Args:
        job_id: Unique job identifier

    Returns:
        Path to the metadata JSON file
    """
    return BASE / "meta" / f"{job_id}.json"

def read_meta(job_id: str) -> dict:
    """
    Read job metadata from disk.

    Args:
        job_id: Unique job identifier

    Returns:
        Metadata dictionary, or empty dict if not found
    """
    p = meta_path(job_id)
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))

def write_meta(job_id: str, data: dict) -> None:
    """
    Write job metadata to disk.

    Args:
        job_id: Unique job identifier
        data: Metadata dictionary to save
    """
    p = meta_path(job_id)
    p.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

def process_pdf(job_id: str, dpi: int = 150, jpegq: int = 70) -> dict:
    """
    Optimize a PDF file using Ghostscript.

    This function processes a PDF by downsampling images and compressing
    with JPEG to reduce file size for web delivery.

    Args:
        job_id: Unique job identifier
        dpi: Image resolution (96, 120, or 150)
        jpegq: JPEG quality (40-85 recommended)

    Returns:
        Dict containing job status and output path

    Raises:
        ValueError: If parameters are invalid or paths are unsafe
        RuntimeError: If metadata not found or Ghostscript fails
    """
    logger.info(f"Starting PDF processing for job {job_id} (dpi={dpi}, jpegq={jpegq})")

    # Re-validate parameters (defense in depth)
    if dpi not in (96, 120, 150):
        logger.error(f"Invalid dpi parameter for job {job_id}: {dpi}")
        raise ValueError(f"Invalid dpi: {dpi}")
    if not (40 <= jpegq <= 85):
        logger.error(f"Invalid jpegq parameter for job {job_id}: {jpegq}")
        raise ValueError(f"Invalid jpegq: {jpegq}")

    meta = read_meta(job_id)
    if not meta:
        logger.error(f"Metadata not found for job {job_id}")
        raise RuntimeError("meta not found")

    in_path = Path(meta["input"])
    out_path = Path(meta["output"])

    # Validate paths to prevent directory traversal
    if not in_path.is_relative_to(BASE / "uploads"):
        logger.error(f"Invalid input path for job {job_id}: {in_path}")
        raise ValueError("Invalid input path")
    if not out_path.is_relative_to(BASE / "outputs"):
        logger.error(f"Invalid output path for job {job_id}: {out_path}")
        raise ValueError("Invalid output path")

    out_path.parent.mkdir(parents=True, exist_ok=True)

    meta["status"] = "processing"
    meta["error"] = None
    write_meta(job_id, meta)
    logger.info(f"Job {job_id} status updated to processing")

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

    logger.info(f"Executing Ghostscript for job {job_id}")
    r = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    if r.returncode != 0 or not out_path.exists():
        error_msg = (r.stderr or "Ghostscript failed").strip()[:4000]
        logger.error(f"Job {job_id} failed: {error_msg}")
        meta["status"] = "failed"
        meta["error"] = error_msg
        write_meta(job_id, meta)
        raise RuntimeError(meta["error"])

    # Get file sizes for logging
    in_size = in_path.stat().st_size
    out_size = out_path.stat().st_size
    reduction = (1 - out_size / in_size) * 100 if in_size > 0 else 0

    logger.info(f"Job {job_id} completed successfully: {in_size} -> {out_size} bytes ({reduction:.1f}% reduction)")
    meta["status"] = "done"
    meta["error"] = None
    write_meta(job_id, meta)
    return {"ok": True, "job_id": job_id, "output": str(out_path)}

def main() -> None:
    """
    Start the RQ worker to process PDF optimization jobs.

    Connects to Redis and listens for jobs on the "pdf" queue.
    Runs with scheduler support for potential delayed jobs.
    """
    logger.info("Starting PDF worker")
    r = redis.from_url(REDIS_URL)
    q = Queue("pdf", connection=r)
    w = Worker([q], connection=r)
    logger.info("Worker ready, waiting for jobs...")
    w.work(with_scheduler=True)

if __name__ == "__main__":
    main()
