from goalstats_template.infrastructure.cache.redis_cache import RedisCache


def is_ready(cache: RedisCache, prefix: str) -> bool:
    return cache.ready(prefix)
