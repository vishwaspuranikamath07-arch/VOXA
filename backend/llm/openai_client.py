"""
backend/llm/openai_client.py
Production OpenAI streaming client.
Fixed: uses key_manager.get_next_key() / mark_key_failed() (async)
       instead of the non-existent .get_key() / .mark_stale() methods.
"""

from __future__ import annotations

import asyncio
import logging
import os
import threading
import time
from typing import Any, AsyncGenerator, List, Optional

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

try:
    from openai import OpenAI as _OpenAIClient
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False
    logger.warning("openai package not installed — OpenAI provider disabled")

from backend.llm.key_manager import key_manager, AllKeysExhaustedException
from backend.llm.router import _build_prompt

_OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")


async def openai_generate(
    user_text: str,
    language: str,
    history: List[dict],
) -> dict[str, str]:
    """
    Async non-streaming OpenAI call.
    Rotates keys via ProductionKeyManager on failure.
    """
    if not HAS_OPENAI:
        raise RuntimeError("openai package not installed")

    t_start = time.perf_counter()
    last_exc: Optional[Exception] = None
    prompt = _build_prompt(user_text, language, history)
    messages: Any = [{"role": "user", "content": prompt}]

    for _ in range(10):  # max attempts across all keys
        try:
            api_key = await key_manager.get_next_key("openai")
        except AllKeysExhaustedException:
            break

        try:
            client = _OpenAIClient(api_key=api_key)
            resp = await asyncio.to_thread(
                client.chat.completions.create,
                model=_OPENAI_MODEL,
                messages=messages,
                max_tokens=35,
                temperature=0.7,
            )
            text = (resp.choices[0].message.content or "").strip() if resp.choices else ""
            if not text:
                raise RuntimeError("OpenAI returned empty content")

            latency_ms = (time.perf_counter() - t_start) * 1000
            logger.info(
                f"llm.call.complete provider=openai model={_OPENAI_MODEL} "
                f"text_len={len(text)} latency_ms={latency_ms:.0f}"
            )
            return {"text": text, "model": _OPENAI_MODEL}

        except Exception as exc:
            logger.warning(f"llm.openai_key_failed error={exc}")
            err_str = str(exc).lower()
            err_type = (
                "auth_error"   if "insufficient_quota" in err_str or "billing" in err_str else
                "rate_limit"   if "429"              in err_str else
                "auth_error"   if "401" in err_str or "403" in err_str else
                "server_error"
            )
            await key_manager.mark_key_failed(api_key, "openai", err_type)
            last_exc = exc

    raise last_exc or RuntimeError("All OpenAI keys failed")


async def openai_stream(
    user_text: str,
    language: str,
    history: List[dict],
) -> AsyncGenerator[Any, None]:
    """
    Async streaming OpenAI call.
    Rotates keys via ProductionKeyManager on failure.
    Yields model metadata dict first, then text chunks.
    """
    if not HAS_OPENAI:
        raise RuntimeError("openai package not installed")

    t_start = time.perf_counter()
    last_exc: Optional[Exception] = None
    prompt = _build_prompt(user_text, language, history)
    messages: Any = [{"role": "user", "content": prompt}]

    logger.info(f"llm.call.start provider=openai message_count={len(history)+1}")

    for _ in range(10):
        try:
            api_key = await key_manager.get_next_key("openai")
        except AllKeysExhaustedException:
            break

        try:
            client = _OpenAIClient(api_key=api_key)
            q: asyncio.Queue = asyncio.Queue()
            loop = asyncio.get_event_loop()
            token_count = 0

            def _producer():
                """Run OpenAI sync stream in daemon background thread."""
                try:
                    resp = client.chat.completions.create(
                        model=_OPENAI_MODEL,
                        messages=messages,
                        max_tokens=35,
                        temperature=0.7,
                        stream=True,
                    )
                    for chunk in resp:
                        if chunk.choices and chunk.choices[0].delta.content:
                            loop.call_soon_threadsafe(
                                q.put_nowait, chunk.choices[0].delta.content
                            )
                except Exception as e:
                    logger.error(f"llm.openai_thread_error error={e}")
                    loop.call_soon_threadsafe(q.put_nowait, e)
                finally:
                    loop.call_soon_threadsafe(q.put_nowait, None)

            t = threading.Thread(target=_producer, daemon=True)
            t.start()

            # Yield model metadata first (consumed by stream_reply)
            yield {"model": _OPENAI_MODEL}

            while True:
                item = await q.get()
                if item is None:
                    break
                if isinstance(item, Exception):
                    raise item
                token_count += 1
                yield item

            latency_ms = (time.perf_counter() - t_start) * 1000
            logger.info(
                f"llm.call.complete provider=openai model={_OPENAI_MODEL} "
                f"latency_ms={latency_ms:.0f} tokens={token_count}"
            )
            return  # success — stop iterating keys

        except Exception as exc:
            logger.warning(f"llm.openai_stream_failed error={exc} trying_next_key=True")
            err_str = str(exc).lower()
            err_type = (
                "auth_error"   if "insufficient_quota" in err_str or "billing" in err_str else
                "rate_limit"   if "429"              in err_str else
                "auth_error"   if "401" in err_str or "403" in err_str else
                "server_error"
            )
            await key_manager.mark_key_failed(api_key, "openai", err_type)
            last_exc = exc

    # All keys failed — raise so LLM router falls back to Ollama
    raise last_exc or RuntimeError("All OpenAI keys exhausted")
