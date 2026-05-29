"""
backend/asr/stream.py

WebSocket endpoint: /ws/stt
Real-time word-by-word STT using faster-whisper with word_timestamps=True.

Architecture:
  1. Client sends binary audio chunks (~100ms each, raw WebM/Opus)
  2. Server accumulates chunks in a rolling buffer
  3. Server detects speech end via silence duration counting
  4. On silence: runs faster-whisper on accumulated segment
  5. Server sends per-word JSON back to client
  6. Server sends final sentence JSON after completion

Client → Server:  binary audio chunks (ArrayBuffer)
Server → Client:  JSON text messages:
  {"type":"word",     "word":"gottilla", "confidence":0.94, "final":false}
  {"type":"sentence", "text":"gottilla bro ...", "final":true, "language_hint":"kn"}
  {"type":"status",   "state":"listening"|"processing"|"idle"}
  {"type":"error",    "message":"..."}
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import struct
import tempfile
import time
from typing import Optional

from fastapi import WebSocket, WebSocketDisconnect

from backend.asr.correction import apply_corrections
from backend.config import WHISPER_MODEL_SIZE, LANGUAGE_CONFIG

logger = logging.getLogger(__name__)

# ── Indian language initial prompt (improves Kanglish/Hinglish accuracy) ──────
_INDIAN_PROMPT = (
    # Kannada — most commonly confused words
    "gottilla illa beku hogbeku naanu neevu idu adu enu madilla "
    "barolla helthini madthini barthiya hogthiya nodidya madidya "
    "hege hegide matte sari banni maadi idira yaaru enaadru "
    "nimma namma nange tange avaru avalu keltini "
    # Hinglish
    "yaar kya nahi achha theek bhai matlab samjha bolna dekho "
    "sunna chahiye milta jata aata phir abhi yahan wahan "
    # Tamlish
    "machan enna illai romba vanakkam seri eppadi yeppo irukku "
    "sollu pannrom kashtam "
    # Tenglish
    "cheppandi evaru ledu undi enti ekkada ayindi antunnaru bagunna "
    "endi kada ante kaadu avunu "
    # Malayalam
    "njaan varunnu entha enthanu evide paranju cheyyum undo "
    # Marker
    "Kannada Hinglish Tamlish Tenglish Indian English romanized"
)

# ── Whisper singleton ──────────────────────────────────────────────────────────
_whisper_model = None


def _get_whisper_model():
    global _whisper_model
    if _whisper_model is None:
        from faster_whisper import WhisperModel
        model_size = WHISPER_MODEL_SIZE or "base"
        logger.info(f"ws_stt.whisper.loading model={model_size} device=cpu compute=int8")
        _whisper_model = WhisperModel(model_size, device="cpu", compute_type="int8")
        logger.info("ws_stt.whisper.ready")
    return _whisper_model


async def _transcribe_segment(audio_bytes: bytes, language: str = "en") -> tuple[list[dict], str]:
    """Transcribe a speech segment. Returns (word_list, detected_language)."""

    def _run() -> tuple[list[dict], str]:
        model = _get_whisper_model()
        # Extract 2-char ISO code
        lang_code = language.split("-")[0] if "-" in language else language
        # Pass language=None for auto-detect; pass code for known Indian langs
        whisper_lang = None if lang_code == "en" else lang_code

        with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name

        try:
            segments, info = model.transcribe(
                tmp_path,
                language=whisper_lang,
                beam_size=5,
                vad_filter=True,
                vad_parameters={
                    "min_silence_duration_ms": 300,
                    "speech_pad_ms": 100,
                    "min_speech_duration_ms": 100,
                },
                word_timestamps=True,
                # ── CRITICAL FIXES ───────────────────────────────────────────────────
                # WAS True → CHANGED to False: condition_on_previous_text=True causes
                # Whisper to repeat/hallucinate prior context into new segments.
                # e.g. "gottilla" becomes "got tilla" because it echoes the previous
                # decoded context instead of treating each segment fresh.
                condition_on_previous_text=False,
                # WAS missing → ADDED: temperature=0.0 forces greedy (argmax) decoding.
                # Without this, Whisper samples stochastically and produces different
                # transcriptions each run for the same audio input.
                temperature=0.0,
                # Discard segments where the text is suspiciously repetitive (hallucination).
                compression_ratio_threshold=2.4,
                # Drop segments where Whisper itself is unsure there's speech at all.
                no_speech_threshold=0.6,
                initial_prompt=_INDIAN_PROMPT if whisper_lang in {"hi", "kn", "ta", "te", "bn"} else None,
            )
            words: list[dict] = []
            for seg in segments:
                if seg.words:
                    for w in seg.words:
                        word_text = w.word.strip()
                        if word_text:
                            words.append({
                                "word":       word_text,
                                "start":      round(w.start, 3),
                                "end":        round(w.end, 3),
                                "confidence": round(getattr(w, "probability", 0.9), 3),
                            })
            return words, info.language or lang_code
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

    return await asyncio.to_thread(_run)


# ── Active connection tracker ─────────────────────────────────────────────────
_active_ws_connections: int = 0
MAX_WS_CONNECTIONS = 100


async def stt_websocket(websocket: WebSocket):
    """
    WebSocket handler for /ws/stt.

    Protocol:
      - Client sends binary audio chunks every ~100ms
      - Client sends text "language:en-IN" to set language
      - Client sends text "stop" to force finalization
      - Server replies with JSON messages (see module docstring)
    """
    global _active_ws_connections

    if _active_ws_connections >= MAX_WS_CONNECTIONS:
        await websocket.close(code=1013, reason="Server at capacity")
        return

    _active_ws_connections += 1
    await websocket.accept()
    logger.info(f"ws_stt.connected total={_active_ws_connections}")

    # ── Per-connection state ───────────────────────────────────────────────────
    audio_buffer: list[bytes] = []       # accumulated audio chunks
    silence_chunks: int = 0              # consecutive silent chunks
    speech_started: bool = False         # true after first non-silent chunk
    language: str = "en"                 # default language
    last_activity = time.time()
    
    transcription_lock = asyncio.Lock()

    SILENCE_THRESHOLD = 6                # 6 × ~100ms = 600ms silence → finalize
    MIN_SPEECH_CHUNKS = 3                # require 300ms of speech before transcribing
    speech_chunks: int = 0

    async def send_json(data: dict):
        try:
            await websocket.send_text(json.dumps(data))
        except Exception:
            pass

    async def finalize_segment(is_interim=False):
        """Transcribe accumulated buffer and send word+sentence events."""
        async with transcription_lock:
            nonlocal audio_buffer, silence_chunks, speech_started, speech_chunks
            
            # Don't transcribe if not enough data
            if not audio_buffer or speech_chunks < MIN_SPEECH_CHUNKS:
                if not is_interim:
                    first_chunk = audio_buffer[0] if audio_buffer else b""
                    audio_buffer = [first_chunk] if first_chunk else []
                    silence_chunks = 0
                    speech_started = False
                    speech_chunks = 0
                return

            segment_bytes = b"".join(audio_buffer)
            
            if not is_interim:
                # Keep the first chunk (WebM header) so future chunks can still be decoded
                first_chunk = audio_buffer[0] if audio_buffer else b""
                audio_buffer = [first_chunk] if first_chunk else []
                silence_chunks = 0
                speech_started = False
                speech_chunks = 0

            await send_json({"type": "status", "state": "processing"})
            t0 = time.perf_counter()

            try:
                words, detected_lang = await _transcribe_segment(segment_bytes, language)
            except Exception as exc:
                logger.error(f"ws_stt.transcribe_error error={exc}")
                if not is_interim:
                    await send_json({"type": "error", "message": str(exc)})
                await send_json({"type": "status", "state": "listening"})
                return

            latency_ms = round((time.perf_counter() - t0) * 1000)
            logger.info(
                f"ws_stt.transcribed words={len(words)} lang={detected_lang} "
                f"latency_ms={latency_ms} interim={is_interim}"
            )

            # Build sentence from words
            raw_sentence = " ".join(w["word"] for w in words).strip()
            corrected_sentence = apply_corrections(raw_sentence)

            if is_interim:
                # Just send the sentence as an interim result
                if corrected_sentence:
                    await send_json({
                        "type":          "sentence",
                        "text":          corrected_sentence,
                        "raw_text":      raw_sentence,
                        "final":         False,
                        "language_hint": detected_lang,
                        "latency_ms":    latency_ms,
                    })
            else:
                # Send per-word events
                for i, w in enumerate(words):
                    corrected_word = apply_corrections(w["word"])
                    await send_json({
                        "type":       "word",
                        "word":       corrected_word,
                        "raw_word":   w["word"],
                        "confidence": w["confidence"],
                        "start":      w["start"],
                        "end":        w["end"],
                        "final":      i == len(words) - 1,
                    })

                # Send final sentence event
                if corrected_sentence:
                    await send_json({
                        "type":          "sentence",
                        "text":          corrected_sentence,
                        "raw_text":      raw_sentence,
                        "final":         True,
                        "language_hint": detected_lang,
                        "latency_ms":    latency_ms,
                    })

            await send_json({"type": "status", "state": "listening"})

    # ── Send initial status ────────────────────────────────────────────────────
    await send_json({"type": "status", "state": "listening"})

    # Task to periodically process interim results
    async def periodic_transcriber():
        while True:
            await asyncio.sleep(0.5) # Process every 500ms
            if speech_started and not silence_chunks >= SILENCE_THRESHOLD:
                if not transcription_lock.locked():
                    await finalize_segment(is_interim=True)

    transcriber_task = asyncio.create_task(periodic_transcriber())

    try:
        while True:
            # Receive next message (binary chunk or text command)
            message = await asyncio.wait_for(websocket.receive(), timeout=30.0)

            if message["type"] == "websocket.disconnect":
                break

            if message.get("text"):
                # Text control message
                text_msg = message["text"].strip()
                if text_msg.startswith("language:"):
                    language = text_msg.split(":", 1)[1].strip().split("-")[0]
                    logger.info(f"ws_stt.language_set lang={language}")
                elif text_msg == "stop":
                    await finalize_segment()
                continue

            if message.get("bytes"):
                chunk = message["bytes"]
                if not chunk:
                    continue

                last_activity = time.time()
                audio_buffer.append(chunk)

                # Simple energy estimation from raw bytes
                # WebM chunks don't have raw PCM, so we use byte variance as proxy
                byte_sum = sum(chunk) / max(len(chunk), 1)
                # WebM silence ≈ all bytes near 0 or a header pattern
                is_silent = (len(chunk) < 200) or (byte_sum < 5.0)

                if not is_silent:
                    silence_chunks = 0
                    speech_started = True
                    speech_chunks += 1
                elif speech_started:
                    silence_chunks += 1
                    if silence_chunks >= SILENCE_THRESHOLD:
                        await finalize_segment()

    except asyncio.TimeoutError:
        logger.info("ws_stt.timeout — finalizing and closing")
        await finalize_segment()
    except WebSocketDisconnect:
        logger.info("ws_stt.disconnected")
    except Exception as exc:
        logger.error(f"ws_stt.error error={exc}")
    finally:
        transcriber_task.cancel()
        _active_ws_connections -= 1
        logger.info(f"ws_stt.closed remaining={_active_ws_connections}")
        # Finalize any remaining audio
        if audio_buffer and speech_started:
            try:
                await finalize_segment()
            except Exception:
                pass
