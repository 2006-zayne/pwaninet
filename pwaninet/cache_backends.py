from django.core.cache.backends.redis import RedisCache
from django.core.cache.backends.locmem import LocMemCache
from django.core.cache import caches
import logging

logger = logging.getLogger(__name__)


class FallbackRedisCache(RedisCache):
    """
    Redis cache backend that falls back to local memory cache if Redis is unavailable.
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._fallback_cache = None
        self._redis_available = True
        
    def _get_fallback_cache(self):
        if self._fallback_cache is None:
            self._fallback_cache = caches['fallback']
        return self._fallback_cache
    
    def _check_redis_availability(self):
        try:
            # Try a simple ping to check if Redis is available
            self._cache.ping()
            self._redis_available = True
            return True
        except Exception as e:
            logger.warning(f"Redis unavailable, falling back to local memory cache: {e}")
            self._redis_available = False
            return False
    
    def get(self, key, default=None, version=None):
        if self._redis_available:
            try:
                return super().get(key, default=default, version=version)
            except Exception as e:
                logger.warning(f"Redis get failed, falling back: {e}")
                self._redis_available = False
        
        return self._get_fallback_cache().get(key, default=default, version=version)
    
    def set(self, key, value, timeout=None, version=None):
        if self._redis_available:
            try:
                return super().set(key, value, timeout=timeout, version=version)
            except Exception as e:
                logger.warning(f"Redis set failed, falling back: {e}")
                self._redis_available = False
        
        return self._get_fallback_cache().set(key, value, timeout=timeout, version=version)
    
    def delete(self, key, version=None):
        if self._redis_available:
            try:
                return super().delete(key, version=version)
            except Exception as e:
                logger.warning(f"Redis delete failed, falling back: {e}")
                self._redis_available = False
        
        return self._get_fallback_cache().delete(key, version=version)
    
    def get_many(self, keys, version=None):
        if self._redis_available:
            try:
                return super().get_many(keys, version=version)
            except Exception as e:
                logger.warning(f"Redis get_many failed, falling back: {e}")
                self._redis_available = False
        
        return self._get_fallback_cache().get_many(keys, version=version)
    
    def set_many(self, data, timeout=None, version=None):
        if self._redis_available:
            try:
                return super().set_many(data, timeout=timeout, version=version)
            except Exception as e:
                logger.warning(f"Redis set_many failed, falling back: {e}")
                self._redis_available = False
        
        return self._get_fallback_cache().set_many(data, timeout=timeout, version=version)
    
    def delete_many(self, keys, version=None):
        if self._redis_available:
            try:
                return super().delete_many(keys, version=version)
            except Exception as e:
                logger.warning(f"Redis delete_many failed, falling back: {e}")
                self._redis_available = False
        
        return self._get_fallback_cache().delete_many(keys, version=version)
    
    def clear(self):
        if self._redis_available:
            try:
                return super().clear()
            except Exception as e:
                logger.warning(f"Redis clear failed, falling back: {e}")
                self._redis_available = False
        
        return self._get_fallback_cache().clear()
    
    def incr(self, key, delta=1, version=None):
        if self._redis_available:
            try:
                return super().incr(key, delta=delta, version=version)
            except Exception as e:
                logger.warning(f"Redis incr failed, falling back: {e}")
                self._redis_available = False
        
        return self._get_fallback_cache().incr(key, delta=delta, version=version)
    
    def decr(self, key, delta=1, version=None):
        if self._redis_available:
            try:
                return super().decr(key, delta=delta, version=version)
            except Exception as e:
                logger.warning(f"Redis decr failed, falling back: {e}")
                self._redis_available = False
        
        return self._get_fallback_cache().decr(key, delta=delta, version=version)
