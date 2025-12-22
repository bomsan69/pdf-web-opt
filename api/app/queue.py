import redis
from rq import Queue
from .settings import settings

def get_queue():
    r = redis.from_url(settings.REDIS_URL)
    return Queue("pdf", connection=r, default_timeout=3600)
