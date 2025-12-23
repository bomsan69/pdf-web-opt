# PDF Web Optimizer

A high-performance microservices-based PDF optimization service that reduces PDF file sizes for web delivery using Ghostscript. Built with FastAPI, Redis Queue, and Docker.

## Features

- **High Compression**: Achieve up to 97.8% file size reduction (tested: 1.04GB → 22.4MB)
- **Asynchronous Processing**: Job queue system with Redis and RQ for handling large files
- **RESTful API**: Simple HTTP endpoints for upload, status check, and download
- **Production Ready**:
  - Comprehensive logging
  - Health check endpoints
  - Security hardening (path traversal prevention, file validation)
  - Type hints and documentation
- **Scalable Architecture**: Microservices design with isolated components
- **Docker Deployment**: One-command setup with Docker Compose

## Architecture

```
┌─────────────┐      ┌─────────────┐      ┌─────────────┐
│   Nginx     │─────▶│  API (Fast  │─────▶│    Redis    │
│ (Proxy)     │      │   API)      │      │   (Queue)   │
└─────────────┘      └─────────────┘      └──────┬──────┘
                            │                     │
                            ▼                     ▼
                     ┌─────────────┐      ┌─────────────┐
                     │   Shared    │◀─────│   Worker    │
                     │   Storage   │      │(Ghostscript)│
                     └─────────────┘      └─────────────┘
```

**Components:**
- **Nginx**: Reverse proxy and load balancer
- **API**: FastAPI service handling uploads and job management
- **Redis**: Job queue and message broker
- **Worker**: RQ worker processing PDFs with Ghostscript
- **Shared Storage**: Docker volume for uploaded and optimized files

## Quick Start

### Prerequisites

- Docker Desktop 20.10+
- 2GB+ available disk space

### Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/pdf-web-opt.git
cd pdf-web-opt
```

2. Start all services:
```bash
docker compose up --build -d
```

3. Verify services are running:
```bash
docker compose ps
```

4. Check health:
```bash
curl http://localhost/health
```

## Usage

### Upload a PDF

```bash
curl -X POST http://localhost/api/jobs \
  -F "file=@input.pdf" \
  -F "dpi=150" \
  -F "jpegq=70"
```

**Parameters:**
- `file`: PDF file to optimize (required)
- `dpi`: Image resolution - 96, 120, or 150 (default: 150)
- `jpegq`: JPEG quality - 40-85 (default: 70)

**Response:**
```json
{
  "job_id": "242ac7c0def3498ca3176c2fe327cce5",
  "status": "queued",
  "status_url": "http://localhost/api/jobs/242ac7c0def3498ca3176c2fe327cce5",
  "download_url": "http://localhost/api/jobs/242ac7c0def3498ca3176c2fe327cce5/download",
  "rq_id": "fbd641c3-302a-41eb-9796-6518a8ad1b18"
}
```

### Check Job Status

```bash
curl http://localhost/api/jobs/{job_id}
```

**Response:**
```json
{
  "job_id": "242ac7c0def3498ca3176c2fe327cce5",
  "status": "done",
  "input": "/data/uploads/242ac7c0def3498ca3176c2fe327cce5_input.pdf",
  "output": "/data/outputs/242ac7c0def3498ca3176c2fe327cce5_web.pdf",
  "dpi": 150,
  "jpegq": 70,
  "error": null,
  "original_filename": "input.pdf"
}
```

**Status Values:**
- `queued`: Job is waiting in queue
- `processing`: Currently being processed
- `done`: Successfully completed
- `failed`: Processing failed (check `error` field)

### Download Optimized PDF

```bash
curl -o output.pdf http://localhost/api/jobs/{job_id}/download
```

## Performance

Real-world test results:

| Original Size | Optimized Size | Reduction | Processing Time | Settings |
|---------------|----------------|-----------|-----------------|----------|
| 1.04 GB | 22.4 MB | 97.8% | 38 seconds | dpi=150, jpegq=70 |

## Configuration

### Environment Variables

**API Service:**
```bash
REDIS_URL=redis://redis:6379/0      # Redis connection string
STORAGE_DIR=/data                    # Storage directory path
PUBLIC_BASE_URL=http://localhost     # Public base URL for responses
MAX_UPLOAD_MB=2048                   # Max upload size in MB
```

**Worker Service:**
```bash
REDIS_URL=redis://redis:6379/0       # Redis connection string
STORAGE_DIR=/data                    # Storage directory path
WORKER_CONCURRENCY=2                 # Number of worker processes
```

Modify `docker-compose.yml` to change these values.

### Ghostscript Parameters

The worker uses these Ghostscript settings:
- **Device**: pdfwrite (PDF output)
- **Compatibility**: PDF 1.4
- **Downsampling**: /Average (better quality than /Bicubic)
- **Color/Gray/Mono**: Configurable DPI
- **JPEG Quality**: Configurable quality (40-85)

## Security Features

✅ **Path Traversal Prevention**: Job IDs validated with regex pattern
✅ **PDF Magic Number Validation**: Files verified with `%PDF` signature
✅ **File Size Limits**: Configurable maximum upload size
✅ **Input Sanitization**: Filenames cleaned and validated
✅ **Parameter Validation**: DPI and quality ranges enforced
✅ **Defense in Depth**: Validation at both API and Worker layers

## API Endpoints

### `GET /health`
Health check endpoint for monitoring

**Response:**
```json
{
  "status": "healthy",
  "components": {
    "redis": "healthy",
    "storage": "healthy"
  }
}
```

### `POST /api/jobs`
Create a new PDF optimization job

### `GET /api/jobs/{job_id}`
Get job status and metadata

### `GET /api/jobs/{job_id}/download`
Download the optimized PDF

## Development

### Project Structure

```
pdf-web-opt/
├── api/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py          # FastAPI application
│   │   ├── settings.py      # Configuration
│   │   ├── queue.py         # Redis Queue setup
│   │   └── storage.py       # File operations
│   ├── Dockerfile
│   └── requirements.txt
├── worker/
│   ├── worker.py            # RQ worker
│   ├── Dockerfile
│   └── requirements.txt
├── nginx/
│   └── default.conf         # Nginx configuration
├── docker-compose.yml
└── README.md
```

### Running Tests

```bash
# View logs
docker compose logs -f

# View specific service logs
docker compose logs -f api
docker compose logs -f worker

# Restart a service
docker compose restart worker

# Stop all services
docker compose down

# Remove volumes (clears all uploaded/processed files)
docker compose down -v
```

### Adding Features

See [CLAUDE.md](./CLAUDE.md) for detailed development guidance and architecture documentation.

## Troubleshooting

### Worker keeps restarting
Check worker logs:
```bash
docker compose logs worker
```

Common issues:
- Redis connection failed: Verify Redis is running
- Ghostscript error: Check input PDF is valid

### Upload fails with 413 error
Increase `MAX_UPLOAD_MB` in docker-compose.yml and restart:
```bash
docker compose up -d api
```

### Job stuck in "processing"
Check worker logs and verify Ghostscript is working:
```bash
docker compose exec worker gs --version
```

## Technical Stack

- **API Framework**: FastAPI 0.115.6
- **Web Server**: Uvicorn 0.34.0
- **Queue**: Redis 7 + RQ 2.1.0
- **PDF Processing**: Ghostscript 10.05
- **Reverse Proxy**: Nginx 1.27
- **Container**: Docker & Docker Compose
- **Language**: Python 3.11

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## Acknowledgments

- Built with [FastAPI](https://fastapi.tiangolo.com/)
- PDF processing powered by [Ghostscript](https://www.ghostscript.com/)
- Job queue management with [RQ](https://python-rq.org/)

---

**Note**: This service is designed for internal use or behind authentication. For public deployment, implement rate limiting, authentication, and additional security measures.
