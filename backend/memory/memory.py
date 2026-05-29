import json
import os
from typing import Dict, List

try:
    import redis
except ImportError:
    redis = None

REDIS_URL = os.getenv("REDIS_URL", "")
redis_client = None
_memory_store: Dict[str, List[dict]] = {}

if redis and REDIS_URL:
    try:
        redis_client = redis.Redis.from_url(REDIS_URL, decode_responses=True)
    except Exception:
        redis_client = None

SESSION_LIMIT = 10  # number of messages to remember


def _redis_get(key: str):
    if not redis_client:
        return None
    try:
        return redis_client.get(key)
    except Exception:
        return None


def _redis_set(key: str, value: str):
    if not redis_client:
        return False
    try:
        redis_client.set(key, value)
        return True
    except Exception:
        return False


def _redis_delete(key: str):
    if not redis_client:
        return False
    try:
        redis_client.delete(key)
        return True
    except Exception:
        return False


def save_message(session_id, role, message):
    key = f"chat:{session_id}"

    if redis_client:
        history = _redis_get(key)
        if history:
            history = json.loads(history)
        else:
            history = []
    else:
        history = _memory_store.get(key, [])

    # Add new message
    history.append({"role": role, "content": message})

    # Keep only last N messages
    history = history[-SESSION_LIMIT:]

    if redis_client and _redis_set(key, json.dumps(history)):
        return
    else:
        _memory_store[key] = history


def get_history(session_id):
    key = f"chat:{session_id}"
    if redis_client:
        history = _redis_get(key)
        if history:
            return json.loads(history)
        if key in _memory_store:
            return _memory_store[key]
        return []

    if key in _memory_store:
        return _memory_store[key]
    return []


def clear_history(session_id):
    key = f"chat:{session_id}"
    if not (redis_client and _redis_delete(key)):
        _memory_store.pop(key, None)
