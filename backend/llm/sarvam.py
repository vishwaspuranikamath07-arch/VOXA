"""
backend/llm/sarvam.py
Asynchronous Sarvam LLM API client wrapper.
"""
from __future__ import annotations

import logging
from typing import Optional

try:
    import httpx
except ImportError:
    httpx = None

from backend.config import SARVAM_CHAT_URL
from backend.llm.key_manager import key_manager, AllKeysExhaustedException

logger = logging.getLogger(__name__)


async def ask_sarvam(prompt: str) -> str:
    """Async wrapper for Sarvam LLM Chat endpoint."""
    if not httpx:
        return "Sarvam unavailable: httpx is not installed."

    if not SARVAM_CHAT_URL:
        return "Missing SARVAM_CHAT_URL"

    last_exc: Optional[Exception] = None

    for _ in range(5):
        try:
            api_key = await key_manager.get_next_key("sarvam")
        except AllKeysExhaustedException:
            break

        headers = {
            "api-subscription-key": api_key,
            "Content-Type": "application/json",
        }
        payload = {"messages": [{"role": "user", "content": prompt}]}

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    SARVAM_CHAT_URL, json=payload, headers=headers, timeout=10.0
                )
                response.raise_for_status()

            data = response.json()
            return data.get("response", "No response from Sarvam")

        except Exception as e:
            logger.warning(f"llm.key.failed provider=sarvam (chat) error={e}")
            err_str = str(e).lower()
            err_type = (
                "rate_limit" if "429" in err_str else
                "auth_error" if "401" in err_str or "403" in err_str else
                "server_error"
            )
            await key_manager.mark_key_failed(api_key, "sarvam", err_type)
            last_exc = e

    return f"Sarvam unavailable: {last_exc or 'All keys exhausted'}"
