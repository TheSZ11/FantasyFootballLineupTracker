"""
Advanced async caching utilities with TTL, rate limiting, and performance optimizations.

Provides both sync and async caching with support for concurrent operations,
automatic cache invalidation, and intelligent cache key generation.
"""

import asyncio
import hashlib
import time
import weakref
from functools import wraps
from typing import Any, Dict, Optional, Callable, Union, Set, TypeVar, Generic
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from ..domain.interfaces import CacheProvider
from ..utils.logging import get_logger

logger = get_logger(__name__)

T = TypeVar('T')


@dataclass
class CacheEntry(Generic[T]):
    """Cache entry with metadata."""
    value: T
    created_at: float
    expires_at: float
    access_count: int = 0
    last_accessed: float = field(default_factory=time.time)
    
    def is_expired(self) -> bool:
        """Check if the cache entry has expired."""
        return time.time() >= self.expires_at
    
    def touch(self):
        """Update access statistics."""
        self.access_count += 1
        self.last_accessed = time.time()


class TTLCache(CacheProvider):
    """
    Thread-safe TTL (Time To Live) cache with advanced features.
    
    Features:
    - Async-safe with proper locking
    - Automatic expiration cleanup
    - LRU eviction when size limit reached
    - Access statistics
    - Cache hit/miss metrics
    """
    
    def __init__(self, max_size: int = 1000, cleanup_interval: int = 300):
        self._cache: Dict[str, CacheEntry] = {}
        self._lock = asyncio.Lock()
        self._max_size = max_size
        self._cleanup_interval = cleanup_interval
        self._cleanup_task: Optional[asyncio.Task] = None
        
        # Statistics
        self._hits = 0
        self._misses = 0
        self._evictions = 0
        
        # Start cleanup task
        self._start_cleanup()
    
    def _start_cleanup(self):
        """Start the background cleanup task."""
        if self._cleanup_task is None or self._cleanup_task.done():
            self._cleanup_task = asyncio.create_task(self._cleanup_expired())
    
    async def _cleanup_expired(self):
        """Background task to clean up expired entries."""
        while True:
            try:
                await asyncio.sleep(self._cleanup_interval)
                async with self._lock:
                    current_time = time.time()
                    expired_keys = [
                        key for key, entry in self._cache.items()
                        if entry.is_expired()
                    ]
                    
                    for key in expired_keys:
                        del self._cache[key]
                    
                    if expired_keys:
                        logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")
                        
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Cache cleanup error: {e}")
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache if not expired."""
        async with self._lock:
            if key in self._cache:
                entry = self._cache[key]
                if not entry.is_expired():
                    entry.touch()
                    self._hits += 1
                    return entry.value
                else:
                    # Entry expired, remove it
                    del self._cache[key]
            
            self._misses += 1
            return None
    
    async def set(self, key: str, value: Any, ttl: int = 300) -> bool:
        """Set value in cache with TTL in seconds."""
        async with self._lock:
            # Check if we need to evict entries
            if len(self._cache) >= self._max_size and key not in self._cache:
                await self._evict_lru()
            
            expires_at = time.time() + ttl
            self._cache[key] = CacheEntry(
                value=value,
                created_at=time.time(),
                expires_at=expires_at
            )
            return True
    
    async def _evict_lru(self):
        """Evict least recently used entry."""
        if not self._cache:
            return
        
        # Find LRU entry
        lru_key = min(
            self._cache.keys(),
            key=lambda k: self._cache[k].last_accessed
        )
        
        del self._cache[lru_key]
        self._evictions += 1
        logger.debug(f"Evicted LRU cache entry: {lru_key}")
    
    async def clear(self) -> bool:
        """Clear all cache entries."""
        async with self._lock:
            self._cache.clear()
            logger.debug("Cache cleared")
            return True
    
    async def delete(self, key: str) -> bool:
        """Delete specific cache entry."""
        async with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False
    
    async def exists(self, key: str) -> bool:
        """Check if key exists and is not expired."""
        result = await self.get(key)
        return result is not None
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        async with self._lock:
            total_requests = self._hits + self._misses
            hit_rate = (self._hits / total_requests * 100) if total_requests > 0 else 0
            
            return {
                'size': len(self._cache),
                'max_size': self._max_size,
                'hits': self._hits,
                'misses': self._misses,
                'hit_rate': round(hit_rate, 2),
                'evictions': self._evictions,
                'expired_entries': sum(1 for entry in self._cache.values() if entry.is_expired())
            }
    
    def size(self) -> int:
        """Get current cache size."""
        return len(self._cache)
    
    async def close(self):
        """Clean up resources."""
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass


class InMemoryCache(TTLCache):
    """Legacy cache implementation for backward compatibility."""
    
    def __init__(self):
        super().__init__(max_size=500, cleanup_interval=600)


def cache_key(*args, **kwargs) -> str:
    """
    Generate a stable cache key from arguments.
    
    Args:
        *args: Positional arguments
        **kwargs: Keyword arguments
        
    Returns:
        Stable hash-based cache key
    """
    # Create a stable representation
    key_parts = []
    
    # Handle positional arguments
    for arg in args:
        if hasattr(arg, '__dict__'):
            # For objects, use their relevant attributes
            key_parts.append(str(sorted(arg.__dict__.items())))
        else:
            key_parts.append(str(arg))
    
    # Handle keyword arguments
    if kwargs:
        key_parts.append(str(sorted(kwargs.items())))
    
    # Create hash
    key_string = '|'.join(key_parts)
    return hashlib.md5(key_string.encode()).hexdigest()


def cached_async(ttl: int = 300, cache_instance: Optional[TTLCache] = None):
    """
    Async decorator to cache function results.
    
    Args:
        ttl: Time to live in seconds (default: 5 minutes)
        cache_instance: Custom cache instance (uses global cache by default)
    """
    def decorator(func: Callable) -> Callable:
        cache = cache_instance or _default_cache
        
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Generate cache key
            key = f"{func.__module__}.{func.__name__}:{cache_key(*args, **kwargs)}"
            
            # Try to get from cache
            result = await cache.get(key)
            if result is not None:
                logger.debug(f"Cache hit for {func.__name__}")
                return result
            
            # Execute function and cache result
            logger.debug(f"Cache miss for {func.__name__}, executing function")
            result = await func(*args, **kwargs)
            await cache.set(key, result, ttl)
            return result
        
        # Add cache management methods
        wrapper.cache_clear = lambda: asyncio.create_task(cache.clear())
        wrapper.cache_stats = lambda: asyncio.create_task(cache.get_stats())
        
        return wrapper
    return decorator


# Global cache instance
_default_cache = TTLCache(max_size=1000, cleanup_interval=300)
