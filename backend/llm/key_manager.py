"""
backend/llm/key_manager.py
Production-grade API Key Manager with:
- Weighted round-robin (prefer keys with fewer failures)
- Per-error-type handling (rate_limit, auth_error, server_error)
- Exponential backoff cooldown (60s → 3600s)
- Async background recovery loop every 30 seconds
- Thread-safe with asyncio.Lock
- AllKeysExhaustedException for instant fallback
"""

from __future__ import annotations

import asyncio
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Literal, Optional

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class AllKeysExhaustedException(Exception):
    """Raised when all keys for a provider are unavailable."""
    def __init__(self, provider: str):
        self.provider = provider
        super().__init__(f"All API keys exhausted for provider: {provider}")


@dataclass
class KeyStatus:
    """Tracks health and usage statistics for a single API key."""
    key: str
    provider: str
    status: Literal["active", "rate_limited", "failed"] = "active"
    fail_count: int = 0
    rate_limited_until: Optional[datetime] = None
    last_used: Optional[datetime] = None
    total_requests: int = 0
    total_failures: int = 0
    cooldown_seconds: float = 60.0  # Starts at 60s, grows exponentially
    failed_at: Optional[datetime] = None


class ProductionKeyManager:
    """
    Thread-safe, production-grade API key manager.
    Supports providers: gemini (LLM), sarvam (TTS/STT).
    OpenAI has been removed — Gemini is the sole cloud LLM provider.
    Features:
    - Weighted round-robin key selection
    - Exponential backoff on rate limits
    - Automatic key recovery in background
    - Full status reporting for /health/keys
    """

    def __init__(self):
        self._keys: Dict[str, List[KeyStatus]] = {}
        self._indexes: Dict[str, int] = {}
        self._lock = asyncio.Lock()
        self._initialized = False
        self._ollama_available = False
        self._max_fail_count = int(os.getenv("KEY_MAX_FAIL_COUNT", "3"))
        self._base_cooldown = float(os.getenv("KEY_RATE_LIMIT_COOLDOWN_SECONDS", "60"))
        self._recovery_interval = int(os.getenv("KEY_RECOVERY_CHECK_INTERVAL_SECONDS", "30"))

    def _load_provider_keys(self, provider: str) -> List[KeyStatus]:
        """
        Load keys for a provider from environment variables.
        Supports comma-separated list in PROVIDER_API_KEYS or PROVIDER_API_KEY.
        """
        env_map = {
            "gemini":      ["GEMINI_API_KEYS",     "GEMINI_API_KEY"],
            "openai":      ["OPENAI_API_KEYS",     "OPENAI_API_KEY"],
            "sarvam":      ["SARVAM_API_KEYS",     "SARVAM_API_KEY"],
            "elevenlabs":  ["ELEVENLABS_API_KEYS", "ELEVENLABS_API_KEY"],
        }
        var_names = env_map.get(provider.lower(), [])
        raw = ""
        for var in var_names:
            raw = os.getenv(var, "").strip()
            if raw:
                break

        keys = [k.strip() for k in raw.split(",") if k.strip()]
        statuses = [KeyStatus(key=k, provider=provider) for k in keys]

        if not keys:
            logger.warning(f"[KeyManager] No keys found for provider: {provider}")
        else:
            logger.info(f"[KeyManager] Loaded {len(keys)} key(s) for provider: {provider}")

        return statuses

    async def initialize(self):
        """Load all provider keys. Call once at startup."""
        await self.reload()
        self._initialized = True
        logger.info("[KeyManager] Initialized all providers")

    async def reload(self):
        """Re-reads .env and updates the key pool without discarding health stats."""
        from dotenv import load_dotenv
        load_dotenv(override=True)

        async with self._lock:
            # NOTE: Only 'gemini', 'sarvam', and 'elevenlabs' are loaded. OpenAI has been removed.
            for provider in ["gemini", "sarvam", "elevenlabs"]:
                new_statuses = self._load_provider_keys(provider)
                if provider not in self._keys:
                    self._keys[provider] = new_statuses
                    self._indexes[provider] = 0
                    continue

                # Merge: Keep existing KeyStatus objects to preserve statistics,
                # add new ones, remove those no longer in .env
                existing_map = {ks.key: ks for ks in self._keys[provider]}
                updated_list = []
                for ns in new_statuses:
                    if ns.key in existing_map:
                        updated_list.append(existing_map[ns.key])
                    else:
                        updated_list.append(ns)
                self._keys[provider] = updated_list
            logger.info("[KeyManager] Reloaded keys from environment (gemini + sarvam + elevenlabs)")

    async def start_recovery_loop(self):
        """
        Background task: every N seconds, checks if rate-limited keys
        have recovered and reactivates them.
        """
        logger.info(f"[KeyManager] Recovery loop started (interval={self._recovery_interval}s)")
        
        # We need this inside or at top level. We'll import inside to avoid circular imports.
        from backend.llm.ollama_client import _check_ollama_health
        
        while True:
            await asyncio.sleep(self._recovery_interval)
            
            # Check Ollama health
            self._ollama_available = await _check_ollama_health()
            
            async with self._lock:
                now = datetime.now()
                for provider, keys in self._keys.items():
                    for ks in keys:
                        if ks.status == "rate_limited" and ks.rate_limited_until:
                            if now >= ks.rate_limited_until:
                                ks.status = "active"
                                ks.rate_limited_until = None
                                ks.cooldown_seconds = self._base_cooldown  # Reset backoff on recovery
                                logger.info(
                                    f"[KeyManager] key.recovered provider={provider} "
                                    f"key_prefix={ks.key[:8]}"
                                )
                        
                        # Proactive Recovery: retry 'failed' keys every 15 minutes
                        # (fail_count >= 5 keys stay failed for 1 hour)
                        if ks.status == "failed":
                            if ks.failed_at is None:
                                ks.failed_at = now
                            elif now - ks.failed_at >= timedelta(minutes=15):
                                ks.status = "active"
                                ks.fail_count = 0
                                ks.failed_at = None
                                logger.info(
                                    f"[KeyManager] key.proactive_retry provider={provider} "
                                    f"key_prefix={ks.key[:8]}"
                                )

    def _weighted_select(self, available: List[KeyStatus]) -> KeyStatus:
        """
        Selects the best key from available pool using weighted selection.
        Prefers keys with fewer total failures and lower fail_count.
        """
        # Score = fewer failures = higher priority
        # Sort by (fail_count, total_failures) ascending — prefer cleanest key
        sorted_keys = sorted(available, key=lambda k: (k.fail_count, k.total_failures))
        return sorted_keys[0]

    async def _recover_keys(self, provider: str) -> None:
        """Check and recover any expired rate-limited keys for a provider."""
        now = datetime.now()
        for ks in self._keys.get(provider, []):
            if ks.status == "rate_limited" and ks.rate_limited_until:
                if now >= ks.rate_limited_until:
                    ks.status = "active"
                    ks.rate_limited_until = None
                    ks.cooldown_seconds = self._base_cooldown  # Reset backoff on recovery
                    logger.info(
                        f"[KeyManager] key.recovered provider={provider} "
                        f"key_prefix={ks.key[:8]}"
                    )

    async def get_next_key(self, provider: str) -> str:
        """
        Returns the next healthy key for the provider using weighted round-robin.
        Raises AllKeysExhaustedException if no keys are available.
        """
        async with self._lock:
            available = [
                k for k in self._keys.get(provider, [])
                if k.status == "active"
            ]
            if not available:
                # Try recovering rate-limited keys before giving up
                await self._recover_keys(provider)
                available = [
                    k for k in self._keys.get(provider, [])
                    if k.status == "active"
                ]
            if not available:
                raise AllKeysExhaustedException(provider)

            # Use weighted select for smart picking, or simple round-robin via indexes
            # We'll use weighted select to ensure "hot" keys are used first
            # but preserve round-robin feel by sorting by last_used too.
            sorted_keys = sorted(available, key=lambda k: (
                k.fail_count, 
                k.total_failures, 
                k.last_used.timestamp() if k.last_used else 0
            ))
            selected = sorted_keys[0]
            
            selected.last_used = datetime.now()
            selected.total_requests += 1
            return selected.key

    async def mark_key_failed(
        self,
        key: str,
        provider: str,
        error_type: Literal["rate_limit", "auth_error", "server_error"],
    ) -> None:
        """
        Marks a key as failed based on the error type.
        """
        async with self._lock:
            target = next(
                (k for k in self._keys.get(provider, []) if k.key == key), None
            )
            if not target:
                return

            target.total_failures += 1

            if error_type == "rate_limit":
                target.cooldown_seconds = min(target.cooldown_seconds * 2, 3600.0)
                target.status = "rate_limited"
                target.rate_limited_until = datetime.now() + timedelta(
                    seconds=target.cooldown_seconds
                )
                logger.warning(
                    f"[KeyManager] key.rate_limited provider={provider} "
                    f"key_prefix={key[:8]} retry_after_seconds={target.cooldown_seconds:.0f}"
                )

            elif error_type == "auth_error":
                target.status = "failed"
                target.failed_at = datetime.now()
                logger.error(
                    f"[KeyManager] key.auth_failed provider={provider} "
                    f"key_prefix={key[:8]} — permanently disabled"
                )

            elif error_type == "server_error":
                target.fail_count += 1
                # Use max(5, _max_fail_count) to avoid false permanent failures on transient errors
                effective_max = max(5, self._max_fail_count)
                if target.fail_count >= effective_max:
                    target.status = "failed"
                    target.failed_at = datetime.now()
                    logger.error(
                        f"[KeyManager] key.server_failed provider={provider} "
                        f"key_prefix={key[:8]} fail_count={target.fail_count}"
                    )
                else:
                    logger.warning(
                        f"[KeyManager] key.server_error provider={provider} "
                        f"key_prefix={key[:8]} fail_count={target.fail_count}/{effective_max}"
                    )

    def get_status(self) -> Dict:
        """
        Returns health status of all providers and keys.
        """
        result = {}
        for provider, keys in self._keys.items():
            active = [k for k in keys if k.status == "active"]
            rate_limited = [k for k in keys if k.status == "rate_limited"]
            failed = [k for k in keys if k.status == "failed"]

            result[provider] = {
                "active_keys": len(active),
                "rate_limited_keys": len(rate_limited),
                "failed_keys": len(failed),
                "total_keys": len(keys),
                "keys": [
                    {
                        "prefix": k.key[:8] + "...",
                        "status": k.status,
                        "fail_count": k.fail_count,
                        "total_requests": k.total_requests,
                        "total_failures": k.total_failures,
                        "rate_limited_until": (
                            k.rate_limited_until.isoformat()
                            if k.rate_limited_until else None
                        ),
                        "last_used": (
                            k.last_used.isoformat() if k.last_used else None
                        ),
                    }
                    for k in keys
                ],
            }
            
        # Add Ollama status
        result["ollama"] = {
            "active_keys": 1 if self._ollama_available else 0,
            "rate_limited_keys": 0,
            "failed_keys": 0 if self._ollama_available else 1,
            "total_keys": 1,
            "keys": []
        }
        return result


# ── Global singleton ──────────────────────────────────────────────────────────────────────
key_manager = ProductionKeyManager()
# Alias for backward compat — any code importing openai_keys still works but
# openai is not loaded. gemini_keys and sarvam_keys are the active ones.
gemini_keys = key_manager
openai_keys = key_manager  # kept as alias, no-op since openai pool is empty
sarvam_keys = key_manager
