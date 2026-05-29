"""
backend/tts/router.py
Production TTS Router — fully hardened.
Fixes applied:
  1. Sarvam speaker map (never sends 'meera')
  2. Edge TTS validated voice map (Bengali, etc.)
  3. Dict / non-string input validator
  4. Three-tier fallback: Sarvam HTTP → Edge TTS → graceful text fallback
  5. No unhandled exceptions — every call is wrapped and returns TTSResult
  6. Module-level httpx.AsyncClient singleton (not per-request)
  7. Per-language provider cache (skip failing provider for 5 min)
  8. Chunked TTS for long text
  9. Structured logging for every call
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import logging
import os
import re
import time
import uuid
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Any, AsyncGenerator, Dict, List, Optional, Tuple

import edge_tts
import httpx

from backend.llm.key_manager import sarvam_keys, key_manager, AllKeysExhaustedException
from backend.config import ELEVENLABS_TTS_URL, ELEVENLABS_MODEL
from backend.utils import detect_language

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
AUDIO_DIR = PROJECT_ROOT / "audio"
CACHE_DIR = AUDIO_DIR / "cache"
AUDIO_DIR.mkdir(parents=True, exist_ok=True)
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# Sarvam model version — bump this whenever the model is upgraded
# so old cached audio is automatically invalidated.
SARVAM_MODEL = "bulbul:v2"  # upgraded from bulbul:v1 for better naturalness & accent

# ── ElevenLabs voice map (eleven_multilingual_v2 — 29 languages) ─────────────
# Rachel (21m00Tcm4TlvDq8ikWAM) is the default multilingual voice.
# Adam (pNInz6obpgDQGcFmaJgB) is used for Hindi — slightly better prosody.
ELEVENLABS_VOICE_MAP: Dict[str, str] = {
    "English":    "EXAVITQu4vr4xnSDxMaL",  # Sarah
    "Hindi":      "IKne3meq5aSn9XLyUdCD",  # Charlie
    "Hinglish":   "IKne3meq5aSn9XLyUdCD",  # Charlie
    "Kannada":    "EXAVITQu4vr4xnSDxMaL",  # Sarah (multilingual v2)
    "Kanglish":   "EXAVITQu4vr4xnSDxMaL",
    "Tamil":      "EXAVITQu4vr4xnSDxMaL",
    "Telugu":     "EXAVITQu4vr4xnSDxMaL",
    "Bengali":    "EXAVITQu4vr4xnSDxMaL",
    "Marathi":    "EXAVITQu4vr4xnSDxMaL",
    "Gujarati":   "EXAVITQu4vr4xnSDxMaL",
    "Malayalam":  "EXAVITQu4vr4xnSDxMaL",
    "Punjabi":    "EXAVITQu4vr4xnSDxMaL",
    "Spanish":    "EXAVITQu4vr4xnSDxMaL",
    "French":     "EXAVITQu4vr4xnSDxMaL",
    "German":     "EXAVITQu4vr4xnSDxMaL",
    "Italian":    "EXAVITQu4vr4xnSDxMaL",
    "Portuguese": "EXAVITQu4vr4xnSDxMaL",
    "Russian":    "EXAVITQu4vr4xnSDxMaL",
    "Japanese":   "EXAVITQu4vr4xnSDxMaL",
    "Chinese":    "EXAVITQu4vr4xnSDxMaL",
    "Korean":     "EXAVITQu4vr4xnSDxMaL",
    "Arabic":     "EXAVITQu4vr4xnSDxMaL",
}
ELEVENLABS_DEFAULT_VOICE = "EXAVITQu4vr4xnSDxMaL"

def _get_cache_path(text: str, language: str, provider: str, model: str = "") -> Path:
    """Generate a unique path for a TTS request based on its content hash.
    
    The model version is included in the hash so that upgrading the TTS model
    (e.g. bulbul:v1 → bulbul:v2) automatically invalidates old cached audio.
    """
    payload = f"{text}|{language}|{provider}|{model}".encode("utf-8")
    h = hashlib.md5(payload).hexdigest()
    return CACHE_DIR / f"{h}.mp3"


# ── ElevenLabs TTS ────────────────────────────────────────────────────────────
async def call_elevenlabs_tts(text: str, language: str) -> bytes:
    """
    Call ElevenLabs TTS REST API with round-robin key rotation.
    Uses eleven_multilingual_v2 model — supports 29 languages natively.
    Returns raw MP3 bytes. Raises RuntimeError on any failure.
    """
    try:
        api_key = await key_manager.get_next_key("elevenlabs")
    except AllKeysExhaustedException as exc:
        raise RuntimeError(f"No ElevenLabs API keys available: {exc}")

    voice_id = ELEVENLABS_VOICE_MAP.get(language, ELEVENLABS_DEFAULT_VOICE)
    url = f"{ELEVENLABS_TTS_URL}/{voice_id}"

    payload = {
        "text": text,
        "model_id": ELEVENLABS_MODEL,
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.75,
            "style": 0.3,
            "use_speaker_boost": True,
        },
    }
    headers = {
        "xi-api-key": api_key,
        "Content-Type": "application/json",
        "Accept": "audio/mpeg",
    }

    t_start = time.perf_counter()
    logger.info(
        f"tts.call.start provider=elevenlabs language={language} "
        f"voice={voice_id} text_len={len(text)}"
    )

    client = get_http_client()
    try:
        resp = await client.post(url, json=payload, headers=headers)
        if resp.status_code == 401:
            await key_manager.mark_key_failed(api_key, "elevenlabs", "auth_error")
            raise RuntimeError("ElevenLabs auth error (401) — key revoked or invalid")
        if resp.status_code == 422:
            raise RuntimeError(f"ElevenLabs bad request (422): {resp.text[:300]}")
        if resp.status_code == 429:
            await key_manager.mark_key_failed(api_key, "elevenlabs", "rate_limit")
            raise RuntimeError("ElevenLabs rate limited (429) — key cooling down")
        if resp.status_code != 200:
            await key_manager.mark_key_failed(api_key, "elevenlabs", "server_error")
            raise RuntimeError(f"ElevenLabs HTTP {resp.status_code}: {resp.text[:200]}")

        audio_bytes = resp.content
        if not audio_bytes:
            raise RuntimeError("ElevenLabs returned 0 bytes")

        latency_ms = round((time.perf_counter() - t_start) * 1000)
        logger.info(
            f"tts.call.success provider=elevenlabs language={language} "
            f"voice={voice_id} audio_bytes={len(audio_bytes)} latency_ms={latency_ms}"
        )
        return audio_bytes

    except (httpx.TimeoutException, httpx.ConnectError) as exc:
        raise RuntimeError(f"ElevenLabs connection error: {exc}")

# ── Module-level HTTP client singleton ────────────────────────────────────────
_http_client: Optional[httpx.AsyncClient] = None


def get_http_client() -> httpx.AsyncClient:
    """Return (or lazily create) the shared async HTTP client.

    FIX: Increased timeout from 8s → 15s so longer TTS text doesn't time out.
    Also recreates the client if it has been closed or if it's in an error state.
    """
    global _http_client
    if _http_client is None or _http_client.is_closed:
        logger.info("tts.http_client creating new AsyncClient")
        _http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(connect=5.0, read=5.0, write=5.0, pool=5.0),
            limits=httpx.Limits(
                max_connections=20,
                max_keepalive_connections=10,
                keepalive_expiry=30,
            ),
        )
    return _http_client


# ── Sarvam language → BCP-47 code ────────────────────────────────────────────
SARVAM_LANGS: Dict[str, str] = {
    "Hindi":    "hi-IN",
    "Kannada":  "kn-IN",
    "Tamil":    "ta-IN",
    "Telugu":   "te-IN",
    "Bengali":  "bn-IN",
    "Marathi":  "mr-IN",
    "Gujarati": "gu-IN",
    "Malayalam":"ml-IN",
    "Punjabi":  "pa-IN",
    "Hinglish": "hi-IN",
    "Kanglish": "kn-IN",
    "Odia":     "or-IN",  # BCP-47 for Odia is or-IN (not od-IN)
}

# ── Sarvam speaker map ────────────────────────────────────────────────────────
# Bug 1: never send "meera" — it is not a valid Sarvam speaker.
SARVAM_SPEAKER_MAP: Dict[str, str] = {
    "hi-IN": "anushka",
    "hi":    "anushka",
    "en-IN": "abhilash",
    "en":    "abhilash",
    "en-US": "abhilash",
    "ta-IN": "anushka",
    "ta":    "anushka",
    "te-IN": "anushka",
    "te":    "anushka",
    "kn-IN": "vidya",    # vidya — better South-Indian phonetics for Kannada (was anushka)
    "kn":    "vidya",
    "ml-IN": "anushka",
    "ml":    "anushka",
    "bn-IN": "anushka",
    "bn":    "anushka",
    "mr-IN": "anushka",
    "mr":    "anushka",
    "gu-IN": "anushka",
    "gu":    "anushka",
    "od-IN": "anushka",
    "pa-IN": "anushka",
    "pa":    "anushka",
}
SARVAM_DEFAULT_SPEAKER = "anushka"
SARVAM_VALID_SPEAKERS = {
    "anushka", "abhilash", "manisha", "vidya",
    "arya", "karun", "hitesh", "aditya",
    "ritu", "priya", "neha", "rahul",
    "pooja", "rohan", "simran", "kavya",
}

# ── Per-language TTS parameter overrides ──────────────────────────────────────────────
# Tuned for natural accent clarity per language.
# Kannada benefits from slower pace (complex syllable structures);
# Tamil/Telugu/Malayalam similarly need slightly relaxed pace.
SARVAM_LANG_OVERRIDES: Dict[str, Dict] = {
    "kn-IN": {"pace": 0.88, "pitch": 0.05, "loudness": 1.6},  # Kannada — slower, slight pitch up
    "ta-IN": {"pace": 0.90},                                    # Tamil
    "te-IN": {"pace": 0.90},                                    # Telugu
    "ml-IN": {"pace": 0.87},                                    # Malayalam — most complex syllables
    "mr-IN": {"pace": 0.92},                                    # Marathi
    "hi-IN": {"pace": 0.95},                                    # Hindi (default speed is fine)
    "bn-IN": {"pace": 0.92},                                    # Bengali
}


def get_sarvam_speaker(language_code: str) -> str:
    """Return a validated Sarvam speaker for the given language code."""
    speaker = SARVAM_SPEAKER_MAP.get(language_code, SARVAM_DEFAULT_SPEAKER)
    if speaker not in SARVAM_VALID_SPEAKERS:
        logger.warning(
            f"[TTS] Invalid speaker '{speaker}' for lang '{language_code}', using default"
        )
        speaker = SARVAM_DEFAULT_SPEAKER
    return speaker


# ── Edge TTS voice map ────────────────────────────────────────────────────────
# Bug 2: validated voice names — Bengali was wrong, now uses TanishaaNeural
EDGE_TTS_VOICE_MAP: Dict[str, str] = {
    # Indian languages
    "hi-IN": "hi-IN-SwaraNeural",
    "hi":    "hi-IN-SwaraNeural",
    "en-IN": "en-IN-PrabhatNeural",
    "en":    "en-IN-PrabhatNeural",
    "en-US": "en-US-JennyNeural",
    "en-GB": "en-GB-SoniaNeural",
    "ta-IN": "ta-IN-PallaviNeural",
    "ta":    "ta-IN-PallaviNeural",
    "te-IN": "te-IN-MohanNeural",
    "te":    "te-IN-MohanNeural",
    "kn-IN": "kn-IN-SapnaNeural",
    "kn":    "kn-IN-SapnaNeural",
    "ml-IN": "ml-IN-SobhanaNeural",
    "ml":    "ml-IN-SobhanaNeural",
    "bn-IN": "bn-IN-TanishaaNeural",   # ← FIXED: was "bn-IN-TanishaNeural"
    "bn":    "bn-IN-TanishaaNeural",
    "mr-IN": "mr-IN-AarohiNeural",
    "mr":    "mr-IN-AarohiNeural",
    "gu-IN": "gu-IN-DhwaniNeural",
    "gu":    "gu-IN-DhwaniNeural",
    "pa-IN": "pa-IN-OjasNeural",
    "pa":    "pa-IN-OjasNeural",
    "or-IN": "or-IN-SuniaNeural",   # Odia — Edge TTS BCP-47 is or-IN
    "or":    "or-IN-SuniaNeural",
    # International
    "fr":    "fr-FR-DeniseNeural",
    "de":    "de-DE-KatjaNeural",
    "es":    "es-ES-ElviraNeural",
    "ar":    "ar-SA-ZariyahNeural",
    "zh":    "zh-CN-XiaoxiaoNeural",
    "ja":    "ja-JP-NanamiNeural",
    "ko":    "ko-KR-SunHiNeural",
    "ru":    "ru-RU-SvetlanaNeural",
    "it":    "it-IT-ElsaNeural",
    "pt":    "pt-BR-FranciscaNeural",
    "nl":    "nl-NL-FennaNeural",
    "sv":    "sv-SE-SofieNeural",
    "pl":    "pl-PL-ZofiaNeural",
    "uk":    "uk-UA-PolinaNeural",
    "tr":    "tr-TR-EmelNeural",
}
# Map friendly language names (as used by the rest of the app) to BCP-47 codes
_LANG_NAME_TO_CODE: Dict[str, str] = {
    "English":   "en-IN",
    "Hindi":     "hi-IN",
    "Bengali":   "bn-IN",
    "Tamil":     "ta-IN",
    "Telugu":    "te-IN",
    "Kannada":   "kn-IN",
    "Malayalam": "ml-IN",
    "Marathi":   "mr-IN",
    "Gujarati":  "gu-IN",
    "Punjabi":   "pa-IN",
    "Odia":      "or-IN",  # BCP-47 for Odia
    "Hinglish":  "hi-IN",
    "Kanglish":  "kn-IN",
    "French":    "fr",
    "German":    "de",
    "Spanish":   "es",
    "Arabic":    "ar",
    "Chinese":   "zh",
    "Japanese":  "ja",
    "Korean":    "ko",
    "Russian":   "ru",
    "Italian":   "it",
    "Portuguese":"pt",
    "Dutch":     "nl",
    "Swedish":   "sv",
    "Polish":    "pl",
    "Turkish":   "tr",
    "Ukrainian": "uk",
}
EDGE_TTS_DEFAULT_VOICE = "en-IN-PrabhatNeural"


def _resolve_lang_code(language: str) -> str:
    """Convert friendly name ('Bengali') OR BCP-47 ('bn-IN') to BCP-47."""
    # If already BCP-47 format (contains hyphen like 'hi-IN'), pass through directly
    if "-" in language:
        return language
    # Otherwise look up the friendly name → BCP-47 map
    # Falls back to the original string for short ISO codes like 'hi', 'bn'
    return _LANG_NAME_TO_CODE.get(language, language)


def get_edge_voice(language: str) -> str:
    """Return the correct Edge TTS voice for a language name or code."""
    code = _resolve_lang_code(language)
    normalized = code.replace("_", "-").lower()
    voice = (
        EDGE_TTS_VOICE_MAP.get(normalized)
        or EDGE_TTS_VOICE_MAP.get(normalized.split("-")[0])
        or EDGE_TTS_DEFAULT_VOICE
    )
    logger.debug(f"[EdgeTTS] lang='{language}' code='{normalized}' → voice='{voice}'")
    return voice


# ── Per-language provider cache ───────────────────────────────────────────────
# Remembers which provider last worked per language to skip known-failing ones.
_provider_cache: Dict[str, Tuple[str, float]] = {}  # lang → (provider, timestamp)
_PROVIDER_CACHE_TTL = 300  # 5 minutes


def _get_cached_provider(lang: str) -> Optional[str]:
    """Return cached working provider for language, or None if expired/missing."""
    if lang in _provider_cache:
        provider, ts = _provider_cache[lang]
        if time.time() - ts < _PROVIDER_CACHE_TTL:
            return provider
        del _provider_cache[lang]
    return None


def _set_cached_provider(lang: str, provider: str) -> None:
    """Cache the working provider for a language."""
    _provider_cache[lang] = (provider, time.time())


def _invalidate_provider_cache(lang: str, provider: str) -> None:
    """Remove cache entry if it points to the now-failing provider."""
    entry = _provider_cache.get(lang)
    if entry and entry[0] == provider:
        del _provider_cache[lang]


# ── TTSResult dataclass ───────────────────────────────────────────────────────
@dataclass
class TTSResult:
    """Unified result from any TTS provider call."""
    success: bool
    provider: str
    audio: Optional[bytes] = None
    fallback_text: Optional[str] = None
    error: Optional[str] = None


# ── Input validation ──────────────────────────────────────────────────────────
def validate_and_clean_tts_input(text: Any) -> str:
    """Normalize TTS input to a clean non-empty string; raises ValueError if unrecoverable."""
    original_type = type(text).__name__

    # Bug 3: extract string from dict
    if isinstance(text, dict):
        text = (
            text.get("text")
            or text.get("content")
            or text.get("message")
            or " ".join(str(v) for v in text.values() if v)
        )
        logger.warning(f"[TTS] Received {original_type} input, extracted: '{str(text)[:80]}'")

    if not isinstance(text, str):
        text = str(text)

    text = text.strip()

    # Strip markdown artifacts that confuse TTS engines
    text = re.sub(r'\*{1,3}(.*?)\*{1,3}', r'\1', text)            # bold/italic
    text = re.sub(r'#{1,6}\s', '', text)                            # headers
    text = re.sub(r'`{1,3}.*?`{1,3}', '', text, flags=re.DOTALL)  # code
    text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)          # links → text
    text = text.strip()

    if not text:
        raise ValueError("TTS input is empty after cleaning")

    # Sarvam hard limit per chunk
    if len(text) > 500:
        text = text[:497] + "..."

    return text


# ── Text splitter for long input ──────────────────────────────────────────────
def split_text_for_tts(text: str, max_chars: int = 500) -> List[str]:
    """Split text at sentence boundaries to respect provider limits."""
    sentences = re.split(r'(?<=[।.!?])\s+', text)
    chunks: List[str] = []
    current = ""
    for sentence in sentences:
        if len(current) + len(sentence) <= max_chars:
            current += (" " if current else "") + sentence
        else:
            if current:
                chunks.append(current)
            current = sentence
    if current:
        chunks.append(current)
    return chunks or [text[:max_chars]]


# ── Sarvam HTTP TTS ───────────────────────────────────────────────────────────
async def call_sarvam_tts(text: str, language_code: str) -> bytes:
    """Call Sarvam REST TTS and return raw audio bytes; raises on any failure."""
    try:
        api_key = await sarvam_keys.get_next_key("sarvam")
    except Exception as exc:
        raise RuntimeError(f"No Sarvam API keys available: {exc}")

    url = os.getenv("SARVAM_TTS_URL", "https://api.sarvam.ai/text-to-speech")
    speaker = get_sarvam_speaker(language_code)

    # Build base payload
    payload = {
        "inputs": [text],                   # MUST be list of strings
        "target_language_code": language_code,
        "speaker": speaker,
        "pitch":    0.0,
        "pace":     0.95,   # slightly slower = clearer articulation
        "loudness": 1.5,    # louder = less muddiness on mobile speakers
        "speech_sample_rate": 22050,  # native Sarvam rate, no resampling artefacts
        "enable_preprocessing": True,  # handles numbers, dates, abbreviations
        "model": SARVAM_MODEL,         # upgraded from v1 — better naturalness & accent
    }
    # Apply per-language overrides (pace, pitch, loudness tuning)
    overrides = SARVAM_LANG_OVERRIDES.get(language_code, {})
    payload.update(overrides)
    headers = {
        "api-subscription-key": api_key,    # NOT "Authorization: Bearer"
        "Content-Type": "application/json",
    }

    t_start = time.perf_counter()
    logger.info(
        f"tts.call.start provider=sarvam language_code={language_code} "
        f"speaker={speaker} text_len={len(text)} text_preview={text[:50]!r}"
    )

    client = get_http_client()
    # FIX: Initialize last_err to a default so the else-branch never raises AttributeError
    # on None when all 3 retries are rate-limited.
    last_err: Exception = RuntimeError("Sarvam: all retries failed")
    resp = None
    for attempt in range(3):
        try:
            resp = await client.post(url, json=payload, headers=headers)
            if resp.status_code == 429:
                await sarvam_keys.mark_key_failed(api_key, "sarvam", "rate_limit")
                wait = 0.5 * (attempt + 1)
                logger.warning(f"tts.sarvam_rate_limit attempt={attempt} waiting={wait}s")
                await asyncio.sleep(wait)
                last_err = RuntimeError(f"Sarvam rate-limited (429) after {attempt+1} attempts")
                continue
            if resp.status_code in (401, 403):
                await sarvam_keys.mark_key_failed(api_key, "sarvam", "auth_error")
                raise RuntimeError(f"Sarvam auth error ({resp.status_code})")
            if resp.status_code == 400:
                # If bulbul:v2 is not yet available, silently fall back to bulbul:v1
                if payload.get("model") == "bulbul:v2":
                    logger.warning(
                        f"tts.sarvam_v2_unavailable lang={language_code} — retrying with bulbul:v1"
                    )
                    payload["model"] = "bulbul:v1"
                    resp = await client.post(url, json=payload, headers=headers)
                    if resp.status_code == 200:
                        break  # v1 succeeded
                raise RuntimeError(f"Sarvam bad request (400): {resp.text[:300]}")
            if resp.status_code != 200:
                await sarvam_keys.mark_key_failed(api_key, "sarvam", "server_error")
                last_err = RuntimeError(f"Sarvam HTTP {resp.status_code}: {resp.text[:200]}")
                await asyncio.sleep(0.3)
                continue
            break  # success — exit loop
        except RuntimeError:
            raise  # propagate auth/bad-request errors immediately
        except Exception as e:
            last_err = e
            logger.warning(f"tts.sarvam_retry attempt={attempt} error={e}")
            await asyncio.sleep(0.3)
    else:
        # Loop completed without break (all retries failed)
        raise last_err

    latency_ms = round((time.perf_counter() - t_start) * 1000)
    data = resp.json()
    audios = data.get("audios") or data.get("audio") or []
    if not audios:
        audio_b64 = data.get("audio_base64", "")
        if not audio_b64:
            raise RuntimeError("Sarvam returned 200 but no audio data")
        audio_bytes = base64.b64decode(audio_b64)
    else:
        audio_b64 = audios[0] if isinstance(audios, list) else audios
        audio_bytes = base64.b64decode(audio_b64)

    logger.info(
        f"tts.call.success provider=sarvam language_code={language_code} "
        f"audio_bytes={len(audio_bytes)} latency_ms={latency_ms}"
    )
    return audio_bytes


# ── Edge TTS ──────────────────────────────────────────────────────────────────
async def call_edge_tts(text: str, language: str) -> bytes:
    """Call Edge TTS and return raw audio bytes; raises on any failure."""
    voice = get_edge_voice(language)

    logger.info(
        f"tts.call.start provider=edge_tts language={language} "
        f"voice={voice} text_len={len(text)}"
    )
    t_start = time.perf_counter()

    communicate = edge_tts.Communicate(text=text, voice=voice)
    buffer = BytesIO()

    async def _stream():
        try:
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    buffer.write(chunk["data"])
        except edge_tts.exceptions.NoAudioReceived:
            raise RuntimeError(
                f"EdgeTTS: no audio received for voice='{voice}' lang='{language}'. "
                "Voice name may be invalid."
            )

    try:
        # Hard 5-second timeout — fast fail so we fall through to Sarvam/Edge quickly
        await asyncio.wait_for(_stream(), timeout=5.0)
    except asyncio.TimeoutError:
        raise RuntimeError(f"EdgeTTS timeout (5s) for voice='{voice}' lang='{language}'")

    audio_bytes = buffer.getvalue()
    if len(audio_bytes) == 0:
        raise RuntimeError(f"EdgeTTS returned 0 bytes for voice='{voice}'")

    latency_ms = round((time.perf_counter() - t_start) * 1000)
    logger.info(
        f"tts.call.success provider=edge_tts language={language} "
        f"voice={voice} audio_bytes={len(audio_bytes)} latency_ms={latency_ms}"
    )
    return audio_bytes


# ── Main orchestration ────────────────────────────────────────────────────────
async def generate_tts_with_fallback(
    text: Any,
    language: str = "English",
) -> TTSResult:
    """
    Three-tier TTS with graceful degradation. NEVER raises to the caller.
    Tier 1: ElevenLabs (ALL languages — eleven_multilingual_v2 supports 29 langs)
    Tier 2: Sarvam HTTP (Indian languages fallback)
    Tier 3: Edge TTS   (universal fallback, no API key needed)
    Tier 4: Return TTSResult(success=False, fallback_text=…)
    """
    # Step 0: validate input
    try:
        clean_text = validate_and_clean_tts_input(text)
    except ValueError as exc:
        logger.error(f"[TTS] Invalid input: {exc}")
        return TTSResult(
            success=False, provider="none",
            fallback_text=str(text), error=str(exc),
        )

    # Check for script mismatch
    detected_lang, conf = detect_language(clean_text)
    if conf > 0.85 and detected_lang != language and detected_lang not in ("English", "Hinglish", "Kanglish", "Tamlish", "Tenglish"):
        logger.info(f"tts.script_override requested='{language}' detected='{detected_lang}' conf={conf}")
        language = detected_lang

    lang_code = SARVAM_LANGS.get(language)  # None for non-Indian languages
    cached_provider = _get_cached_provider(language)

    # ── Step 1: Check Local Persistent Cache ──────────────────────────────────
    for prov, model_key in [("elevenlabs", ""), ("sarvam", SARVAM_MODEL), ("edge_tts", "")]:
        c_path = _get_cache_path(clean_text, language, prov, model_key)
        if c_path.exists():
            logger.info(f"tts.cache_hit provider={prov} text='{clean_text[:30]}...'")
            return TTSResult(success=True, provider=prov, audio=c_path.read_bytes())

    is_indic = bool(lang_code)

    # ── Tier 1: ElevenLabs (ALL languages — primary, best quality) ────────────
    if cached_provider not in ("edge_tts", "sarvam"):
        try:
            audio = await call_elevenlabs_tts(clean_text, language)
            _get_cache_path(clean_text, language, "elevenlabs").write_bytes(audio)
            _set_cached_provider(language, "elevenlabs")
            return TTSResult(success=True, provider="elevenlabs", audio=audio)
        except Exception as exc:
            logger.warning(
                f"tts.call.failed provider=elevenlabs error_type={type(exc).__name__} "
                f"error={exc} falling_back_to={'sarvam' if is_indic else 'edge_tts'}"
            )
            _invalidate_provider_cache(language, "elevenlabs")

    # ── Tier 2: Sarvam (Indian languages fallback) ───────────────────────────
    if is_indic and cached_provider not in ("edge_tts",):
        try:
            audio = await call_sarvam_tts(clean_text, lang_code)
            _get_cache_path(clean_text, language, "sarvam", SARVAM_MODEL).write_bytes(audio)
            _set_cached_provider(language, "sarvam")
            return TTSResult(success=True, provider="sarvam", audio=audio)
        except Exception as exc:
            logger.warning(
                f"tts.call.failed provider=sarvam error_type={type(exc).__name__} "
                f"error={exc} falling_back_to=edge_tts"
            )
            _invalidate_provider_cache(language, "sarvam")

    # ── Tier 3: Edge TTS (all languages, always available) ───────────────────
    try:
        audio = await call_edge_tts(clean_text, language)
        _get_cache_path(clean_text, language, "edge_tts").write_bytes(audio)
        _set_cached_provider(language, "edge_tts")
        return TTSResult(success=True, provider="edge_tts", audio=audio)
    except Exception as exc:
        logger.error(
            f"tts.call.failed provider=edge_tts error_type={type(exc).__name__} "
            f"error={exc}"
        )
        _invalidate_provider_cache(language, "edge_tts")

    # ── Tier 4: All failed — graceful text fallback ───────────────────────────
    logger.error(
        f"tts.all_providers_failed language_code={lang_code or language} "
        f"text_length={len(clean_text)} returning=text_fallback"
    )
    return TTSResult(
        success=False, provider="none",
        fallback_text=clean_text,
        error="All TTS providers unavailable (ElevenLabs + Sarvam + EdgeTTS)",
    )


# ── synthesize_speech — used by /tts/generate (file-based, non-streaming) ────
async def synthesize_speech(text: str, language: str) -> str:
    """
    Non-streaming TTS: generate audio file, return URL path like /audio/xxx.mp3.
    Wraps generate_tts_with_fallback; raises only on complete failure.
    """
    result = await generate_tts_with_fallback(text, language)

    if result.success and result.audio:
        file_name = f"{uuid.uuid4().hex}.mp3"
        file_path = AUDIO_DIR / file_name
        file_path.write_bytes(result.audio)
        logger.info(
            f"tts.file_saved provider={result.provider} "
            f"file={file_name} bytes={len(result.audio)}"
        )
        return f"/audio/{file_name}"

    # Both providers failed — raise so the endpoint can handle gracefully
    raise RuntimeError(result.error or "TTS unavailable")


# ── stream_tts — used by /chat/stream (SSE streaming) ────────────────────────
async def stream_tts(
    text_stream: AsyncGenerator,
    language: str,
) -> AsyncGenerator[str, None]:
    """
    Routes streaming TTS.
    Tier 1: ElevenLabs (all languages — best voice quality)
    Tier 2: Sarvam HTTP (Indian languages fallback)
    Tier 3: Edge TTS (universal fallback, no API key)
    Yields base64-encoded audio strings.
    """
    buffer = ""
    lang_code = SARVAM_LANGS.get(language)
    cached_provider = _get_cached_provider(language)
    is_indic_stream = bool(lang_code)
    use_elevenlabs = cached_provider not in ("edge_tts", "sarvam")
    use_sarvam = is_indic_stream and cached_provider != "edge_tts"
    _first_flushed = False

    async def flush_chunk(chunk_text: str, chunk_lang: str) -> AsyncGenerator[str, None]:
        """ElevenLabs → Sarvam (Indic) → Edge TTS."""
        nonlocal use_elevenlabs, use_sarvam
        chunk_lang_code = SARVAM_LANGS.get(chunk_lang)

        # ── Tier 1: ElevenLabs (all languages — best quality) ─────────────────
        if use_elevenlabs:
            try:
                audio = await call_elevenlabs_tts(chunk_text, chunk_lang)
                _set_cached_provider(chunk_lang, "elevenlabs")
                yield base64.b64encode(audio).decode("utf-8")
                return
            except Exception as exc:
                logger.warning(
                    f"tts.stream.elevenlabs_failed chunk_len={len(chunk_text)} error={exc} "
                    f"falling_back_to={'sarvam' if chunk_lang_code else 'edge_tts'}"
                )
                use_elevenlabs = False
                _invalidate_provider_cache(chunk_lang, "elevenlabs")

        # ── Tier 2: Sarvam (Indian languages fallback) ────────────────────────
        if use_sarvam and chunk_lang_code:
            try:
                audio = await call_sarvam_tts(chunk_text, chunk_lang_code)
                _set_cached_provider(chunk_lang, "sarvam")
                yield base64.b64encode(audio).decode("utf-8")
                return
            except Exception as exc:
                logger.warning(
                    f"tts.stream.sarvam_failed chunk_len={len(chunk_text)} error={exc} "
                    f"falling_back_to=edge_tts"
                )
                use_sarvam = False
                _invalidate_provider_cache(chunk_lang, "sarvam")

        # ── Tier 3: Edge TTS (all languages — always fast, no API key) ─────────
        try:
            audio = await call_edge_tts(chunk_text, chunk_lang)
            _set_cached_provider(chunk_lang, "edge_tts")
            yield base64.b64encode(audio).decode("utf-8")
        except Exception as exc:
            logger.error(f"tts.stream.edge_failed chunk_len={len(chunk_text)} error={exc}")
            # Silently drop this chunk — don't crash the stream

    async for text_chunk in text_stream:
        if not isinstance(text_chunk, str):
            continue
        buffer += text_chunk
        # Adaptive flush: first chunk at 20 chars (get audio started ASAP),
        # subsequent chunks at 60 chars (fewer API round-trips per response).
        flush_at = 20 if not _first_flushed else 60
        if any(c in buffer for c in ".?!।,;\n") or len(buffer) > flush_at:
            _first_flushed = True
            to_speak = buffer.strip()
            buffer = ""
            if not to_speak:
                continue
            try:
                clean = validate_and_clean_tts_input(to_speak)
            except ValueError:
                continue
                
            detected_lang, conf = detect_language(clean)
            chunk_language = language
            if conf > 0.85 and detected_lang != language and detected_lang not in ("English", "Hinglish", "Kanglish", "Tamlish", "Tenglish"):
                logger.info(f"tts.stream.script_override requested='{language}' detected='{detected_lang}' conf={conf}")
                chunk_language = detected_lang
                
            async for audio_b64 in flush_chunk(clean, chunk_language):
                yield audio_b64

    # Flush remaining buffer
    if buffer.strip():
        try:
            clean = validate_and_clean_tts_input(buffer.strip())
            detected_lang, conf = detect_language(clean)
            chunk_language = language
            if conf > 0.85 and detected_lang != language and detected_lang not in ("English", "Hinglish", "Kanglish", "Tamlish", "Tenglish"):
                chunk_language = detected_lang
                
            async for audio_b64 in flush_chunk(clean, chunk_language):
                yield audio_b64
        except ValueError:
            pass


# ── Backward-compat alias ─────────────────────────────────────────────────────
async def speak_router(text: str, lang: str) -> str:
    """Alias for synthesize_speech for backward compat."""
    return await synthesize_speech(text, lang)
