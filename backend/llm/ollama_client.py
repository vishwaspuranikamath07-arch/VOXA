"""
backend/llm/ollama_client.py
Production Ollama local model fallback client with streaming support and structured logging.
"""

from __future__ import annotations

import json
import logging
import os
import time
from typing import AsyncGenerator, Union

import httpx

logger = logging.getLogger(__name__)

from backend.llm.router import _build_prompt

async def _check_ollama_health() -> bool:
    host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(f"{host}/api/tags")
            return resp.status_code == 200
    except Exception:
        return False

async def ollama_generate(
    user_text: str,
    language: str,
    history: list[dict],
) -> dict[str, str]:
    """Async wrapper for Ollama generate call."""
    t_start = time.perf_counter()
    host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    model = os.getenv("OLLAMA_MODEL", "llama3")
    
    if not await _check_ollama_health():
        raise RuntimeError("Ollama service not available locally")
        
    prompt = _build_prompt(user_text, language, history)
    
    async with httpx.AsyncClient(timeout=45.0) as client:
        try:
            resp = await client.post(
                f"{host}/api/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    "stream": False
                }
            )
            
            # If 404, try appending :latest (common Ollama quirk)
            if resp.status_code == 404 and ":" not in model:
                logger.info(f"llm.ollama_retry model={model}:latest")
                resp = await client.post(
                    f"{host}/api/generate",
                    json={
                        "model": f"{model}:latest",
                        "prompt": prompt,
                        "stream": False
                    }
                )

            if resp.status_code != 200:
                raise RuntimeError(f"Ollama returned HTTP {resp.status_code}")
                
            data = resp.json()
            text = (data.get("response") or "").strip()
            
            latency_ms = (time.perf_counter() - t_start) * 1000
            logger.info(f"llm.call.complete provider=ollama model={model} text_len={len(text)} latency_ms={latency_ms:.0f}")
            
            return {"text": text, "model": f"{model} (Offline)"}
            
        except httpx.RequestError as exc:
            logger.error(f"llm.ollama_error error={exc}")
            raise RuntimeError(f"Ollama Request Error: {exc}")

async def ollama_stream(
    user_text: str,
    language: str,
    history: list[dict],
) -> AsyncGenerator[Union[str, dict], None]:
    """Async generator yielding text chunks via Ollama streaming."""
    t_start = time.perf_counter()
    host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    model = os.getenv("OLLAMA_MODEL", "llama3")
    
    if not await _check_ollama_health():
        raise RuntimeError("Ollama service not running locally — skipping")

    logger.info(f"llm.call.start provider=ollama message_count={len(history)+1}")
    prompt = _build_prompt(user_text, language, history)
    
    # Yield model metadata first
    yield {"model": f"{model} (Offline)"}
    
    async with httpx.AsyncClient(timeout=45.0) as client:
        try:
            url = f"{host}/api/generate"
            payload = {
                "model": model,
                "prompt": prompt,
                "stream": True
            }

            # We use a helper context manager to handle the fallback logic cleanly
            async def _stream_with_fallback(m_name: str):
                local_payload = payload.copy()
                local_payload["model"] = m_name
                async with client.stream("POST", url, json=local_payload) as response:
                    # If 404 and no tag, try :latest
                    if response.status_code == 404 and ":" not in m_name:
                        logger.info(f"llm.ollama_retry_stream model={m_name}:latest")
                        local_payload["model"] = f"{m_name}:latest"
                        async with client.stream("POST", url, json=local_payload) as retry_resp:
                            yield retry_resp
                    else:
                        yield response

            async for response in _stream_with_fallback(model):
                if response.status_code != 200:
                    raise RuntimeError(f"Ollama returned HTTP {response.status_code}")
                
                token_count = 0
                async for chunk in response.aiter_lines():
                    if not chunk:
                        continue
                    try:
                        data = json.loads(chunk)
                        fragment = data.get("response", "")
                        if fragment:
                            token_count += 1
                            yield fragment
                    except json.JSONDecodeError:
                        continue
                        
                latency_ms = (time.perf_counter() - t_start) * 1000
                logger.info(
                    f"llm.call.complete provider=ollama model={model} "
                    f"latency_ms={latency_ms:.0f} tokens={token_count}"
                )
                
        except httpx.RequestError as exc:
            logger.error(f"llm.ollama_stream_failed error={exc}")
            raise RuntimeError(f"Ollama connection failed: {exc}")
