import os

import redis

_client = redis.Redis.from_url(os.environ["REDIS_URL"], decode_responses=True)


def get_redis() -> redis.Redis:
    return _client