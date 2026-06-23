import redis
from rq import Worker

from app.config import settings
from app.logger import get_logger

log = get_logger(__name__)


def main():
    log.info("RQ worker starting — connecting to %s", settings.redis_url)
    conn = redis.from_url(settings.redis_url)
    log.info("Connected to Redis, listening on queue: default")
    worker = Worker(["default"], connection=conn)
    worker.work()


if __name__ == "__main__":
    main()
