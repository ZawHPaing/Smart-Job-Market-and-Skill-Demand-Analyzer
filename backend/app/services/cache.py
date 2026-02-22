# backend/app/services/cache.py
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import hashlib
import json

class SimpleCache:
    def __init__(self):
        self.cache: Dict[str, Any] = {}
        self.cache_times: Dict[str, datetime] = {}
        self.ttl = timedelta(hours=3)  # Cache lasts 2 hours
        
    def _generate_key(self, *args, **kwargs) -> str:
        """Generate a cache key from arguments"""
        key_parts = [str(arg) for arg in args]
        key_parts.extend([f"{k}:{v}" for k, v in sorted(kwargs.items())])
        key_string = "|".join(key_parts)
        return hashlib.md5(key_string.encode()).hexdigest()
    
    def get(self, key: str) -> Optional[Any]:
        if key in self.cache:
            # Check if cache is still fresh
            if datetime.now() - self.cache_times[key] < self.ttl:
                print(f"✅ Cache HIT: {key[:20]}...")
                return self.cache[key]
            else:
                # Remove expired cache
                print(f"⏰ Cache EXPIRED: {key[:20]}...")
                del self.cache[key]
                del self.cache_times[key]
        return None
    
    def set(self, key: str, value: Any):
        self.cache[key] = value
        self.cache_times[key] = datetime.now()
        print(f"💾 Cache SET: {key[:20]}...")
    
    def clear(self):
        self.cache.clear()
        self.cache_times.clear()
        print("🧹 Cache cleared")
    
    def get_or_set(self, key: str, func, *args, **kwargs):
        """Get from cache or execute function and cache result"""
        cached = self.get(key)
        if cached:
            return cached
        
        result = func(*args, **kwargs)
        self.set(key, result)
        return result

# Create a single instance to share across the app
cache = SimpleCache()