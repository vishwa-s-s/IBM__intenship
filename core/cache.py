import hashlib
from diskcache import Cache
import os

# Initialize disk cache in a local .cache directory
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
cache_dir = os.path.join(project_root, ".cache")
cache = Cache(cache_dir)

def generate_hash(content: str) -> str:
    """Generates an MD5 hash for a given string."""
    return hashlib.md5(content.encode('utf-8')).hexdigest()

def get_cached(key: str):
    """Retrieve value from cache by key."""
    return cache.get(key)

def set_cached(key: str, value: any, expire=None):
    """Save value to cache with an optional expiration time (in seconds)."""
    cache.set(key, value, expire=expire)

def cache_text_result(url: str, text: str):
    key = f"text_{generate_hash(url)}"
    set_cached(key, text)

def get_cached_text(url: str):
    key = f"text_{generate_hash(url)}"
    return get_cached(key)

def cache_audio_result(text: str, voice_id: str, audio_bytes: bytes):
    key = f"audio_{generate_hash(text + voice_id)}"
    set_cached(key, audio_bytes)

def get_cached_audio(text: str, voice_id: str):
    key = f"audio_{generate_hash(text + voice_id)}"
    return get_cached(key)
