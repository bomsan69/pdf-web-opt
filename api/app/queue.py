import redis
from rq import Queue
from .settings import settings

def get_queue() -> Queue:
    """
    Get Redis Queue instance for PDF processing jobs.

    Returns:
        RQ Queue instance connected to Redis with 1-hour timeout

    Note:
        Queue name is "pdf" and timeout is 3600 seconds (1 hour)
    """
    r = redis.from_url(settings.REDIS_URL)
    return Queue("pdf", connection=r, default_timeout=3600)
