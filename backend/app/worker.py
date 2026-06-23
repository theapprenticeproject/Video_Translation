import redis
from rq import Worker

from app.config import settings


def main():
    conn = redis.from_url(settings.redis_url)
    worker = Worker(["default"], connection=conn)
    worker.work()


if __name__ == "__main__":
    main()
