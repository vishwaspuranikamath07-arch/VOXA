"""
backend/llm/router.py
Production LLM Router with:
- Gemini primary (streaming) — direct, no OpenAI
- Ollama local emergency fallback only
- Full key rotation using ProductionKeyManager
- Structured logging for every call
- Smart system prompt injection
"""

from __future__ import annotations

import asyncio
import logging
import os
import threading
import time
from typing import Any, AsyncGenerator, List, Optional

from dotenv import load_dotenv
from google import genai

load_dotenv()

logger = logging.getLogger(__name__)

from backend.prompts import SYSTEM_PROMPT

# BCP-47 code lookup for [LANG: xx-IN] tag injection
_LANG_TO_BCP47: dict[str, str] = {
    "English": "en-IN",  "Hindi": "hi-IN",  "Kannada": "kn-IN", "Tamil": "ta-IN",
    "Telugu":  "te-IN",  "Bengali": "bn-IN", "Marathi": "mr-IN", "Gujarati": "gu-IN",
    "Malayalam": "ml-IN","Punjabi": "pa-IN", "Hinglish": "hi-IN","Kanglish": "kn-IN",
    "Spanish": "es-ES",  "French": "fr-FR",  "German": "de-DE",  "Japanese": "ja-JP",
    "Chinese": "zh-CN",  "Arabic": "ar-SA",  "Korean": "ko-KR",  "Russian": "ru-RU",
}


def _build_prompt(user_text: str, language: str, history: List[dict], llm_instruction: str = "") -> str:
    """Inject hidden system context right before the user's turn."""
    ctx = ""
    if history:
        lines = []
        # Keep only last 4 turns (2 user + 2 assistant) — shorter prompt = faster TTFT
        for msg in history[-4:]:
            role = "User" if msg["role"] == "user" else "Voxa"
            lang_tag = f" [{msg.get('lang')}]" if msg.get("lang") else ""
            lines.append(f"{role}{lang_tag}: {msg['content']}")
        ctx = "Conversation so far:\n" + "\n".join(lines) + "\n\n"
        
    instruction_block = f"\n[CRITICAL INSTRUCTION: {llm_instruction}]\n" if llm_instruction else ""

    return (
        f"{SYSTEM_PROMPT}\n\n"
        f"{ctx}"
        f"(Detected Language: {language}){instruction_block}\n"
        f"User: {user_text}\n"
        f"Voxa:"
    )


# ── Import the production key manager ─────────────────────────────────────────
# NOTE: openai_keys removed — Gemini is the sole cloud provider now.
from backend.llm.key_manager import gemini_keys, AllKeysExhaustedException


async def _async_gemini(user_text: str, language: str, history: List[dict], llm_instruction: str = "") -> dict[str, str]:
    """
    Asynchronous Gemini non-streaming call. Iterates keys on failure.
    """
    model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite")
    prompt = _build_prompt(user_text, language, history, llm_instruction)
    last_exc: Exception = RuntimeError("All Gemini keys failed")

    while True:
        try:
            api_key = await gemini_keys.get_next_key("gemini")
        except AllKeysExhaustedException:
            break

        try:
            client = genai.Client(api_key=api_key)
            resp = await asyncio.to_thread(
                client.models.generate_content, model=model_name, contents=prompt
            )
            text = (resp.text or "").strip()
            if not text:
                raise RuntimeError("Gemini returned empty content")
            logger.info(
                f"llm.call.complete provider=gemini model={model_name} "
                f"text_len={len(text)}"
            )
            return {"text": text, "model": model_name}
        except Exception as exc:
            logger.warning(f"llm.key.failed provider=gemini error={exc}")
            err_str = str(exc).lower()
            err_type = (
                "auth_error" if "quota" in err_str or "billing" in err_str else
                "rate_limit" if "429" in err_str else
                "auth_error" if "401" in err_str or "403" in err_str else
                "server_error"
            )
            await gemini_keys.mark_key_failed(api_key, "gemini", err_type)
            last_exc = exc
            continue

    raise last_exc


async def stream_reply(
    user_text: str,
    language: str,
    history: Optional[List[dict]] = None,
    llm_instruction: str = "",
) -> AsyncGenerator[Any, None]:
    """
    Streams LLM tokens.
    Level 1: Gemini streaming (primary, sole cloud provider — OpenAI removed).
    Level 2: Ollama local (emergency fallback only, when all Gemini keys fail).
    Level 3: Hardcoded text fallback.
    Yields text chunks and a leading {"model": ...} dict for the frontend chip.
    """
    if history is None:
        history = []

    model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite")
    prompt = _build_prompt(user_text, language, history, llm_instruction)

    logger.info(
        f"llm.call.start provider=gemini model={model_name} "
        f"message_count={len(history)+1}"
    )

    # ── Level 1: Gemini Streaming ──────────────────────────────────────────────
    success = False
    last_exc: Exception = RuntimeError("All Gemini keys failed")
    t_start = time.perf_counter()

    for _ in range(5):  # Max 5 key rotation attempts (was 10)
        try:
            api_key = await gemini_keys.get_next_key("gemini")
        except AllKeysExhaustedException:
            break

        try:
            client = genai.Client(api_key=api_key)
            q: asyncio.Queue = asyncio.Queue()
            loop = asyncio.get_event_loop()
            token_count = 0

            def _producer():
                """Run Gemini sync stream in a background thread."""
                try:
                    # thinking_config budget_tokens=0 disables Gemini 2.5 Flash thinking
                    # overhead, cutting TTFT by 200-600ms on short voice responses.
                    from google.genai import types as _gtypes
                    _cfg = _gtypes.GenerateContentConfig(
                        thinking_config=_gtypes.ThinkingConfig(thinking_budget=0)
                    )
                    stream = client.models.generate_content_stream(
                        model=model_name, contents=prompt, config=_cfg
                    )
                    for chunk in stream:
                        if chunk.text:
                            loop.call_soon_threadsafe(q.put_nowait, chunk.text)
                except Exception as e:
                    logger.error(f"llm.gemini_thread_error error={e}")
                    loop.call_soon_threadsafe(q.put_nowait, e)
                finally:
                    loop.call_soon_threadsafe(q.put_nowait, None)

            t = threading.Thread(target=_producer, daemon=True)
            t.start()

            # Yield model info first (for frontend provider chip)
            yield {"model": model_name}

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
                f"llm.call.complete provider=gemini model={model_name} "
                f"latency_ms={latency_ms:.0f} tokens={token_count}"
            )
            success = True
            break

        except Exception as exc:
            logger.warning(f"llm.gemini_stream_failed error={exc} rotating_key=True")
            err_str = str(exc).lower()
            err_type = (
                "auth_error" if "quota" in err_str or "billing" in err_str else
                "rate_limit" if "429" in err_str else
                "auth_error" if "401" in err_str or "403" in err_str else
                "server_error"
            )
            await gemini_keys.mark_key_failed(api_key, "gemini", err_type)
            last_exc = exc

    if success:
        return

    # ── Level 2: Ollama Local Fallback ─────────────────────────────────────────
    logger.error("llm.all_gemini_keys_failed switching_to=ollama_local")
    try:
        from backend.llm.ollama_client import ollama_stream
        async for chunk in ollama_stream(user_text, language, history):
            yield chunk
        return
    except Exception as exc:
        logger.error(f"llm.ollama_stream_failed error={exc}")

    # ── Level 3: Hardcoded text fallback ──────────────────────────────────────
    from backend.utils import get_fallback
    fallback_text = get_fallback(language)
    logger.error("llm.using_hardcoded_fallback provider=none")
    yield fallback_text


async def generate_reply(
    user_text: str,
    language: str,
    history: Optional[List[dict]] = None,
    llm_instruction: str = "",
) -> dict[str, str]:
    """
    Non-streaming full generate (used by /chat endpoint).
    Gemini → Ollama. OpenAI removed completely.
    """
    if history is None:
        history = []

    t_start = time.perf_counter()
    logger.info(f"llm.call.start provider=gemini mode=full message_count={len(history)+1}")

    # ── Level 1: Gemini ────────────────────────────────────────────────────────
    try:
        result = await _async_gemini(user_text, language, history, llm_instruction)
        latency_ms = (time.perf_counter() - t_start) * 1000
        logger.info(f"llm.call.complete provider=gemini latency_ms={latency_ms:.0f}")
        return result
    except Exception as exc:
        logger.warning(f"llm.gemini_pool_exhausted error={exc}")

    # ── Level 2: Ollama ────────────────────────────────────────────────────────
    try:
        from backend.llm.ollama_client import ollama_generate
        result = await ollama_generate(user_text, language, history)
        latency_ms = (time.perf_counter() - t_start) * 1000
        logger.info(f"llm.call.complete provider=ollama latency_ms={latency_ms:.0f}")
        return result
    except Exception as exc:
        logger.error(f"llm.ollama_fallback_failed error={exc}")

    # ── Ultimate text fallback ─────────────────────────────────────────────────
    from backend.utils import get_fallback
    logger.error("llm.using_hardcoded_fallback provider=none")
    return {"text": get_fallback(language), "model": "Local Fallback"}
