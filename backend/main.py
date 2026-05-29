"""
backend/main.py  — Voxa AI v3.0  (Production-Grade)
FastAPI app with:
  - /chat/stream  : SSE streaming with TTFT badge + provider chip
  - /chat         : Non-streaming fallback
  - /tts/generate : On-demand TTS for speaker button
  - /tts/test     : Debug TTS without touching UI
  - /health       : Provider key-pool status
  - /health/keys  : Full masked key table
  - /chat/clear   : Clear session
  - /ws/chat      : WebSocket with 25s keepalive ping
  Startup: initialises ProductionKeyManager + recovery loop
"""

import asyncio
import json
import logging
import os
import sys
import time
from contextlib import asynccontextmanager
from pathlib import Path

# ── Resolve project root so `backend.*` imports work ───────────────────────────
root = Path(__file__).resolve().parents[1]
if str(root) not in sys.path:
    sys.path.append(str(root))

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, Query, Request, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

load_dotenv()
logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO")),
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)

# ── Import after path fix ──────────────────────────────────────────────────────
from backend.llm.router import generate_reply, stream_reply
from backend.tts.router import synthesize_speech, stream_tts, generate_tts_with_fallback, SARVAM_LANGS
from backend.utils import detect_language, get_flag
from backend.config import DEFAULT_MODEL, SARVAM_STT_URL, BACKEND_STT_LANGS, LANGUAGE_CONFIG, WHISPER_MODEL_SIZE
from backend.llm.key_manager import key_manager
from backend.asr.correction import apply_corrections
from backend.asr.stream import stt_websocket

# ── Paths ─────────────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parents[1]
FRONTEND_DIR = PROJECT_ROOT / "frontend"
AUDIO_DIR    = PROJECT_ROOT / "audio"
AUDIO_DIR.mkdir(parents=True, exist_ok=True)

# Keep max messages to MAX_CONVERSATION_MEMORY_TURNS from config
from backend.config import MAX_CONVERSATION_MEMORY_TURNS
MAX_HISTORY = MAX_CONVERSATION_MEMORY_TURNS

# ── In-memory session state ────────────────────────────────────────────────────
_sessions: dict[str, dict] = {}
_active_tasks: dict[str, asyncio.Task] = {}

# ── Performance tracking ───────────────────────────────────────────────────────
_stats: dict = {"total_requests": 0, "total_latency_ms": 0.0, "cache_hits": 0}


def _get_session(session_id: str) -> dict:
    """Get or create a session dict."""
    if session_id not in _sessions:
        _sessions[session_id] = {
            "history": [],
            "lang_history": [],
            "created_at": time.time(),
        }
    return _sessions[session_id]


def _get_history(session_id: str) -> list[dict]:
    return _get_session(session_id)["history"]


def _push_history(session_id: str, role: str, text: str, lang: str | None = None):
    sess = _get_session(session_id)
    sess["history"].append({"role": role, "content": text, "lang": lang})
    # Only log language once per exchange (on user turn) — logging on both
    # user+assistant with the same lang was doubling history size unnecessarily.
    if lang and role == "user":
        sess["lang_history"].append(lang)
    if len(sess["history"]) > MAX_HISTORY:
        sess["history"] = sess["history"][-MAX_HISTORY:]
    # Keep only the 2 most recent language detections.
    # A smaller window means a language switch takes effect within 1 turn
    # instead of needing to overcome a 3-turn majority.
    if len(sess["lang_history"]) > 2:
        sess["lang_history"] = sess["lang_history"][-2:]


def _get_rolling_lang(session_id: str) -> list[str]:
    return _get_session(session_id)["lang_history"]


# ── Audio helpers ──────────────────────────────────────────────────────────────
def _resolve_audio_path(returned: str | None) -> Path | None:
    """
    Converts whatever synthesize_speech() returns into an absolute Path.
    Handles: /audio/file.mp3 → PROJECT_ROOT/audio/file.mp3 (Windows fix).
    """
    if not returned:
        return None
    stripped = returned.lstrip("/\\")
    candidate = PROJECT_ROOT / stripped
    if candidate.exists() and candidate.stat().st_size > 0:
        return candidate
    p = Path(returned)
    if p.exists() and p.stat().st_size > 0:
        return p
    return None


def _mime(path: Path) -> str:
    return {
        ".mp3": "audio/mpeg",
        ".wav": "audio/wav",
        ".ogg": "audio/ogg",
        ".m4a": "audio/mp4",
    }.get(path.suffix.lower(), "audio/mpeg")


def _serve_audio(path: Path) -> Response:
    """Read file bytes and serve them directly — no redirects."""
    data = path.read_bytes()
    return Response(
        content=data,
        media_type=_mime(path),
        headers={
            "Cache-Control": "no-cache, no-store",
            "Content-Length": str(len(data)),
        },
    )


# ── Lifespan (startup / shutdown) ────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize key manager and start background recovery loop on startup."""
    logger.info("🚀 Voxa AI v3.0 starting up…")
    await key_manager.initialize()
    asyncio.create_task(key_manager.start_recovery_loop())
    
    from backend.utils import _build_ngram_profiles, _compile_lexicons
    _compile_lexicons()
    _build_ngram_profiles()
    
    logger.info("✅ KeyManager initialized — recovery loop started")
    logger.info("✅ Language Detection lexicons & n-gram profiles compiled")
    logger.info(f"✅ Frontend served from: {FRONTEND_DIR}")
    logger.info(f"✅ Audio dir: {AUDIO_DIR}")
    yield
    logger.info("🛑 Voxa AI shutting down…")


# ── FastAPI app ───────────────────────────────────────────────────────────────
app = FastAPI(
    title="Voxa AI",
    version="3.0.0",
    description="Production-grade multilingual voice AI assistant",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/audio", StaticFiles(directory=AUDIO_DIR), name="audio")
app.mount("/app", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")

app.add_api_websocket_route("/ws/stt", stt_websocket)
# ── Pydantic request/response models ─────────────────────────────────────────
class ChatRequest(BaseModel):
    text:            str        = Field(default="", max_length=1000)
    session_id:      str        = Field(default="default")
    stt_latency_ms:  float      = Field(default=0.0)
    # Optional: BCP-47 language code determined by the frontend's unicode-script
    # check (e.g. 'kn-IN' when Kannada script chars are detected).  When set,
    # detect_language() skips langdetect entirely — fixes misidentification of
    # transliterated Kannada/Bengali as English.
    detected_script: str | None = Field(default=None)


class ChatResponse(BaseModel):
    response:      str
    language:      str
    language_flag: str
    latency:       float
    llm_latency:   float
    tts_latency:   float
    model:         str
    audio:         str | None
    error:         str | None = None


# ── Routes ────────────────────────────────────────────────────────────────────
@app.get("/")
async def root() -> RedirectResponse:
    return RedirectResponse(url="/app")


@app.get("/health")
async def health() -> dict:
    """Provider key-pool summary + avg response metrics."""
    key_status = key_manager.get_status()
    total_req = _stats["total_requests"]
    avg_ms = (
        _stats["total_latency_ms"] / total_req if total_req > 0 else 0
    )
    cache_pct = (
        f"{(_stats['cache_hits'] / total_req * 100):.0f}%"
        if total_req > 0 else "0%"
    )
    return {
        "name": "Voxa AI",
        "version": "3.0.0",
        "status": "ok",
        "providers": {
            provider: {
                "active_keys": data["active_keys"],
                "rate_limited_keys": data["rate_limited_keys"],
                "failed_keys": data["failed_keys"],
            }
            for provider, data in key_status.items()
        },
        "cache_hit_rate": cache_pct,
        "avg_response_ms": round(avg_ms, 1),
        "total_requests": total_req,
        "frontend": "/app",
    }


@app.get("/health/keys")
async def health_keys() -> dict:
    """Full key status table — keys masked to first 8 chars for security."""
    return key_manager.get_status()


@app.post("/health/reload")
async def reload_keys() -> dict:
    """Force re-read .env and refresh the key pool."""
    await key_manager.reload()
    return {
        "status": "ok",
        "message": "API keys reloaded from environment",
        "pool_status": key_manager.get_status()
    }


@app.get("/health/apis")
async def api_health() -> dict:
    """Legacy API health endpoint for frontend compatibility."""
    key_status = key_manager.get_status()
    gemini_ok = key_status.get("gemini", {}).get("active_keys", 0) > 0
    sarvam_ok = key_status.get("sarvam", {}).get("active_keys", 0) > 0
    ollama_ok = key_status.get("ollama", {}).get("active_keys", 0) > 0

    return {
        "gemini": {
            "status": "ok" if gemini_ok else "error",
            "message": (
                f"{key_status.get('gemini',{}).get('active_keys',0)} active key(s)"
                if gemini_ok else "All Gemini keys exhausted"
            ),
        },
        # OpenAI removed — Gemini is the sole cloud LLM provider
        "openai": {
            "status": "disabled",
            "message": "OpenAI removed — using Gemini directly",
        },
        "sarvam": {
            "status": "ok" if sarvam_ok else "error",
            "message": "Sarvam TTS ready" if sarvam_ok else "SARVAM_API_KEY missing",
        },
        "ollama": {
            "status": "ok" if ollama_ok else "error",
            "message": "Local Ollama active" if ollama_ok else "Ollama unreachable",
        },
        "tts": {
            "status": "ok",
            "message": "Hybrid (Sarvam/Edge) TTS ready",
        },
    }


@app.post("/chat/clear")
async def clear_session(session_id: str = Query(default="default")) -> dict:
    """Clear session history and cancel any active streaming task."""
    _sessions.pop(session_id, None)
    if session_id in _active_tasks:
        _active_tasks[session_id].cancel()
        _active_tasks.pop(session_id, None)
    return {"status": "cleared", "session_id": session_id}


# ── /tts/generate — Speaker button TTS ───────────────────────────────────────
@app.post("/tts/generate")
async def generate_tts(request: Request):
    """
    On-demand TTS for the 🔊 speaker button.
    Returns raw audio bytes on success (audio/mpeg).
    Returns HTTP 200 JSON with fallback_text on failure — NEVER 500.
    """
    try:
        data     = await request.json()
        text     = data.get("text", "")
        language = data.get("language", "English")
    except Exception as exc:
        return JSONResponse(status_code=400, content={"error": f"Invalid JSON: {exc}"})

    if not text or (isinstance(text, str) and not text.strip()):
        return JSONResponse(status_code=400, content={"error": "No text provided"})

    logger.info(f"tts.generate language={language!r} text_len={len(str(text))}")

    # generate_tts_with_fallback NEVER raises — always returns a TTSResult
    result = await generate_tts_with_fallback(text, language)

    if result.success and result.audio:
        logger.info(
            f"tts.serving provider={result.provider} "
            f"audio_bytes={len(result.audio)}"
        )
        return Response(
            content=result.audio,
            media_type="audio/mpeg",
            headers={
                "X-TTS-Provider": result.provider,
                "X-TTS-Language": language,
                "Cache-Control": "no-cache, no-store",
            },
        )

    # Graceful degradation — HTTP 200 with JSON so the frontend can show text
    logger.error(
        f"tts.all_providers_failed language={language!r} "
        f"error={result.error!r} returning=text_fallback"
    )
    return JSONResponse(
        status_code=200,
        content={
            "success": False,
            "audio": None,
            "fallback_text": result.fallback_text,
            "error": result.error,
            "provider": "none",
            "message": "Audio generation failed. Display text response instead.",
        },
    )


@app.get("/tts/test")
async def test_tts(text: str = "Hello, this is a test.", language: str = "English"):
    """Debug endpoint: verify TTS without touching the UI."""
    try:
        returned   = await synthesize_speech(text, language)
        audio_path = _resolve_audio_path(returned)
        return {
            "returned":        returned,
            "resolved":        str(audio_path) if audio_path else None,
            "exists":          audio_path.exists() if audio_path else False,
            "size":            audio_path.stat().st_size if audio_path else 0,
            "project_root":    str(PROJECT_ROOT),
            "audio_dir":       str(AUDIO_DIR),
            "audio_dir_files": [f.name for f in AUDIO_DIR.iterdir()] if AUDIO_DIR.exists() else [],
        }
    except Exception as exc:
        return {"error": str(exc)}


# ── /stt/transcribe — Sarvam AI Speech-to-Text for Indian languages ──────────
@app.post("/stt/transcribe")
async def stt_transcribe(
    audio: UploadFile = File(...),
    language: str = Form(default="kn-IN"),
):
    """
    Sarvam AI STT endpoint for Indian language transcription.
    Called by frontend MediaRecorder when language is Kannada, Hindi, etc.
    Returns: {"transcript": "...", "language": "..."}
    """
    try:
        api_key = await key_manager.get_next_key("sarvam")
    except Exception:
        raise HTTPException(status_code=503, detail="No Sarvam STT keys available")

    audio_bytes = await audio.read()
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="Empty audio file")

    logger.info(f"stt.transcribe language={language} bytes={len(audio_bytes)}")

    import httpx as _httpx
    try:
        async with _httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                SARVAM_STT_URL,
                headers={"api-subscription-key": api_key},
                files={
                    "file": (
                        audio.filename or "audio.webm",
                        audio_bytes,
                        audio.content_type or "audio/webm",
                    )
                },
                data={
                    "language_code": language,
                    "model": "saarika:v2.5",
                    "with_timestamps": "false",
                },
            )
    except _httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Sarvam STT timed out")

    if resp.status_code != 200:
        err_str = resp.text.lower()
        err_type = (
            "auth_error"   if "quota"  in err_str or "billing" in err_str else
            "rate_limit"   if resp.status_code == 429 else
            "server_error"
        )
        await key_manager.mark_key_failed(api_key, "sarvam", err_type)
        logger.error(f"stt.sarvam_error status={resp.status_code} body={resp.text[:200]}")
        raise HTTPException(
            status_code=resp.status_code,
            detail=f"Sarvam STT failed: {resp.text[:200]}",
        )

    result   = resp.json()
    transcript = result.get("transcript", "")
    logger.info(f"stt.transcribe.done language={language} transcript_len={len(transcript)}")
    return {"transcript": transcript, "language": language}


# ── Whisper model singleton (lazy-loaded on first use) ───────────────────────
_whisper_model = None
_whisper_lock  = None  # initialised in _get_whisper_model to avoid event-loop issues


def _get_whisper_model():
    """Return the cached WhisperModel, initialising it on first call.

    Uses WHISPER_MODEL_SIZE from config (default: 'base').  Model files are
    downloaded to ~/.cache/huggingface on first invocation only.
    """
    global _whisper_model
    if _whisper_model is None:
        try:
            from faster_whisper import WhisperModel
            logger.info(f"whisper.loading model={WHISPER_MODEL_SIZE} device=cpu compute=int8")
            _whisper_model = WhisperModel(
                WHISPER_MODEL_SIZE,
                device="cpu",
                compute_type="int8",
            )
            logger.info("whisper.ready")
        except Exception as exc:
            logger.error(f"whisper.load_failed error={exc}")
            raise
    return _whisper_model


async def _transcribe_whisper(audio_bytes: bytes, language: str) -> str:
    """Transcribe audio bytes using faster-whisper in a thread pool.

    Args:
        audio_bytes: Raw audio data (webm/wav/ogg).
        language:    BCP-47 code (e.g. 'kn-IN'); 2-char ISO code extracted
                     automatically for Whisper (e.g. 'kn').

    Returns:
        Transcribed text, or empty string on failure.
    """
    import io
    import tempfile

    # Extract 2-char ISO code from BCP-47 (e.g. 'kn-IN' → 'kn')
    lang_code = LANGUAGE_CONFIG.get(language, {}).get("whisper_code") or language.split("-")[0]

    def _run() -> str:
        model = _get_whisper_model()
        # Write to a named temp file so Whisper can read it
        with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name
        try:
            segments, _info = model.transcribe(
                tmp_path,
                language=lang_code,
                beam_size=5,
                vad_filter=True,          # suppress silence segments
                vad_parameters={"min_silence_duration_ms": 300},
                initial_prompt=(
                    "Hindi Bengali Kannada Tamil Telugu Indian language native script "
                    "namaste kya hai kemon acho nanu neevu enna panra ela unnav"
                ) if lang_code in {"hi", "bn", "kn", "ta", "te"} else None,
            )
            return " ".join(seg.text.strip() for seg in segments).strip()
        finally:
            import os as _os
            try:
                _os.unlink(tmp_path)
            except OSError:
                pass

    return await asyncio.to_thread(_run)


# ── /stt/stream — Raw-body STT endpoint for MediaRecorder audio ───────────────
@app.post("/stt/stream")
async def stt_stream(
    request: Request,
    language: str = Query(default="kn-IN", description="BCP-47 language code, e.g. kn-IN"),
):
    """
    Tier-1 Sarvam ASR → Tier-2 faster-whisper fallback STT endpoint.

    Called by the frontend MediaRecorder path for Indian languages
    (kn-IN, mr-IN, bn-IN, te-IN, ta-IN) that Web Speech API handles poorly.

    Request body: raw audio bytes (audio/webm or audio/wav).
    Response JSON: {"transcript": str, "language": str,
                    "confidence": float, "provider": str,
                    "error": str | None}
    """
    # ── Validate language is in backend-STT list ───────────────────────────────
    if language not in BACKEND_STT_LANGS:
        # Graceful: still attempt Sarvam, just log a warning
        logger.warning(f"stt.stream unexpected language={language}")

    # ── Read raw body ─────────────────────────────────────────────────────────
    audio_bytes = await request.body()

    if not audio_bytes:
        return JSONResponse(
            status_code=200,
            content={"transcript": "", "language": language,
                     "confidence": 0.0, "provider": "none",
                     "error": "no_speech"},
        )

    # Discard very short chunks (< ~0.3 s at 16kHz mono WAV ≈ 9 600 bytes;
    # for webm the container overhead means < 1 000 bytes is definitely noise)
    if len(audio_bytes) < 1000:
        logger.debug(f"stt.stream discarding tiny chunk bytes={len(audio_bytes)}")
        return JSONResponse(
            status_code=200,
            content={"transcript": "", "language": language,
                     "confidence": 0.0, "provider": "none",
                     "error": "chunk_too_short"},
        )

    logger.info(f"stt.stream language={language} bytes={len(audio_bytes)}")

    # ── Tier 1: Sarvam ASR ────────────────────────────────────────────────────
    try:
        api_key = await key_manager.get_next_key("sarvam")
    except Exception:
        logger.warning("stt.stream no_sarvam_keys — skipping to Whisper")
        api_key = None

    if api_key:
        import httpx as _httpx
        # Determine content type for the upload filename hint
        content_type = request.headers.get("content-type", "audio/webm")
        ext = ".wav" if "wav" in content_type else ".webm"
        try:
            # FIX: Increased from 1.5s → 8.0s. The 1.5s cap was too aggressive and silently
            # discarded valid speech on any connection with >1.5s API response time.
            # 8s matches real-world Sarvam API latency including audio upload time.
            async with _httpx.AsyncClient(timeout=8.0) as client:
                resp = await client.post(
                    SARVAM_STT_URL,
                    headers={"api-subscription-key": api_key},
                    files={
                        "file": (f"audio{ext}", audio_bytes, content_type)
                    },
                    data={
                        "language_code": language,
                        "model":          "saarika:v2.5",
                        "with_timestamps": "false",
                    },
                )

            if resp.status_code == 200:
                result     = resp.json()
                transcript = apply_corrections(result.get("transcript", "").strip())
                logger.info(
                    f"stt.stream.sarvam language={language} "
                    f"transcript_len={len(transcript)}"
                )
                return JSONResponse(
                    status_code=200,
                    content={
                        "transcript": transcript,
                        "language":   language,
                        "confidence": 0.92,
                        "provider":   "sarvam",
                        "error":      None if transcript else "no_speech",
                    },
                )

            # Non-200 from Sarvam — mark key and fall through to Whisper
            err_str  = resp.text.lower()
            err_type = (
                "auth_error"   if "quota"  in err_str or "billing" in err_str else
                "rate_limit"   if resp.status_code == 429 else
                "server_error"
            )
            await key_manager.mark_key_failed(api_key, "sarvam", err_type)
            logger.warning(
                f"stt.stream.sarvam_error status={resp.status_code} "
                f"body={resp.text[:200]} — falling through to Whisper"
            )

        except _httpx.TimeoutException:
            logger.warning("stt.stream.sarvam_timeout — falling through to Whisper")
        except Exception as exc:
            logger.warning(f"stt.stream.sarvam_exception error={exc} — falling through to Whisper")

    # ── Tier 2: faster-whisper (local fallback) ────────────────────────────────
    try:
        raw_transcript = await _transcribe_whisper(audio_bytes, language)
        transcript = apply_corrections(raw_transcript)
        logger.info(
            f"stt.stream.whisper language={language} "
            f"transcript_len={len(transcript)}"
        )
        return JSONResponse(
            status_code=200,
            content={
                "transcript": transcript,
                "language":   language,
                "confidence": 0.75,
                "provider":   "whisper",
                "error":      None if transcript else "no_speech",
            },
        )
    except Exception as exc:
        logger.error(f"stt.stream.whisper_failed error={exc}")
        return JSONResponse(
            status_code=200,
            content={
                "transcript": "",
                "language":   language,
                "confidence": 0.0,
                "provider":   "none",
                "error":      "transcription_failed",
            },
        )


# ── /chat — Non-streaming (legacy) ───────────────────────────────────────────
@app.post("/chat", response_model=ChatResponse)
async def chat(payload: ChatRequest) -> ChatResponse:
    """Full non-streaming chat endpoint (fallback for clients without SSE support)."""
    wall_start = time.perf_counter()
    user_text  = apply_corrections(payload.text.strip())
    session_id = payload.session_id or "default"

    _stats["total_requests"] += 1

    if not user_text:
        return ChatResponse(
            response="Please say or type something so I can help.",
            language="English", language_flag="🇬🇧",
            latency=0.0, llm_latency=0.0, tts_latency=0.0,
            model=DEFAULT_MODEL, audio=None, error="empty_input",
        )

    lang_hist            = _get_rolling_lang(session_id)
    from backend.utils import LanguageDetector
    detection_res = LanguageDetector.detect(user_text, lang_hist)
    language = detection_res["lang_name_display"]
    confidence = detection_res["confidence"]
    llm_instruction = detection_res.get("llm_instruction", "")
    
    flag                 = get_flag(language)
    history              = _get_history(session_id)

    t_llm = time.perf_counter()
    try:
        llm_result = await generate_reply(
            user_text=user_text, language=language, history=history, llm_instruction=llm_instruction
        )
    except Exception:
        llm_latency = round(time.perf_counter() - t_llm, 3)
        total       = round(time.perf_counter() - wall_start, 3)
        return ChatResponse(
            response="Sorry, I could not process that right now. Please try again.",
            language=language, language_flag=flag,
            latency=total, llm_latency=llm_latency, tts_latency=0.0,
            model=DEFAULT_MODEL, audio=None, error="llm_failure",
        )

    llm_latency   = round(time.perf_counter() - t_llm, 3)
    response_text = llm_result["text"]
    model_used    = llm_result.get("model", DEFAULT_MODEL)

    _push_history(session_id, "user",      user_text,     language)
    _push_history(session_id, "assistant", response_text, language)

    audio_path:  str | None = None
    audio_error: str | None = None
    t_tts = time.perf_counter()
    try:
        audio_path = await asyncio.create_task(synthesize_speech(response_text, language))
    except Exception:
        audio_error = "tts_failure"
    tts_latency   = round(time.perf_counter() - t_tts, 3)
    total_latency = round(time.perf_counter() - wall_start, 3)

    _stats["total_latency_ms"] += total_latency * 1000

    return ChatResponse(
        response=response_text, language=language, language_flag=flag,
        latency=total_latency, llm_latency=llm_latency, tts_latency=tts_latency,
        model=model_used, audio=audio_path, error=audio_error,
    )


# ── /chat/stream — SSE streaming ─────────────────────────────────────────────
@app.post("/chat/stream")
async def chat_stream(payload: ChatRequest):
    """
    Server-Sent Events stream.
    Events:
      meta   — language, flag, confidence, model info
      ttft   — time-to-first-token latency badge
      text   — streaming token chunk
      audio  — base64 audio chunk (for voice autoplay)
      done   — final stats (stt/llm/tts/total latency, model name)
      error  — error string
    Correct latency: measured from request receipt (server-side).
    """
    user_text  = apply_corrections(payload.text.strip())
    session_id = payload.session_id or "default"

    _stats["total_requests"] += 1

    if not user_text:
        async def empty_gen():
            yield "data: " + json.dumps({"type": "error", "content": "empty_input"}) + "\n\n"
        return StreamingResponse(empty_gen(), media_type="text/event-stream")

    # Cancel any existing stream for this session (interrupt)
    if session_id in _active_tasks:
        _active_tasks[session_id].cancel()

    lang_hist            = _get_rolling_lang(session_id)
    # Use the frontend's script hint to lock language and skip langdetect.
    # IMPORTANT: Only lock if the detected_script is from native Unicode script detection.
    # Do NOT use romanised text hints (that causes Hinglish to be tagged as en-IN).
    _locked = None
    if payload.detected_script and "-" in payload.detected_script:
        # e.g. 'kn-IN' → 'Kannada', 'ta-IN' → 'Tamil' etc.
        _SCRIPT_TO_LANG = {
            "kn-IN": "Kannada", "ta-IN": "Tamil", "te-IN": "Telugu",
            "bn-IN": "Bengali", "mr-IN": "Marathi", "gu-IN": "Gujarati",
            "ml-IN": "Malayalam", "pa-IN": "Punjabi", "hi-IN": "Hindi",
        }
        _locked = _SCRIPT_TO_LANG.get(payload.detected_script)
        
    from backend.utils import LanguageDetector
    detection_res = LanguageDetector.detect(user_text, lang_hist, locked_lang=_locked)
    language = detection_res["lang_name_display"]
    confidence = detection_res["confidence"]
    llm_instruction = detection_res.get("llm_instruction", "")
    
    flag                 = get_flag(language)

    async def event_generator():
        tts_engine = (
            "Sarvam Neural" if language in SARVAM_LANGS else "Edge Neural"
        )

        # ── Meta event ─────────────────────────────────────────────────────────
        yield "data: " + json.dumps({
            "type":       "meta",
            "language":   language,
            "flag":       flag,
            "confidence": confidence,
            "asr_model":  "Web Speech API",
            "tts_model":  tts_engine,
            "session_id": session_id,
        }) + "\n\n"

        llm_to_client_q: asyncio.Queue = asyncio.Queue()
        llm_to_tts_q:    asyncio.Queue = asyncio.Queue()
        shared_stats: dict = {"model": DEFAULT_MODEL}

        # ── LLM producer task ─────────────────────────────────────────────────
        async def llm_producer():
            """Consumes LLM stream and fans out to client queue and TTS queue."""
            history    = _get_history(session_id)
            full_reply = ""
            import re as _re
            _lang_tag_re = _re.compile(r'^\s*\[LANG:\s*[a-z]{2}-[A-Z]{2}\]\s*')
            first_chunk_processed = False
            try:
                # Pass llm_instruction through language param or create a new param
                async for chunk in stream_reply(user_text, language, history, llm_instruction=llm_instruction):
                    if isinstance(chunk, dict) and "model" in chunk:
                        shared_stats["model"] = chunk["model"]
                        await llm_to_client_q.put({"model": chunk["model"]})
                        continue
                    if isinstance(chunk, str):
                        # Strip [LANG: xx-XX] tag from the FIRST chunk if AI echoes it
                        if not first_chunk_processed:
                            chunk = _lang_tag_re.sub('', chunk)
                            first_chunk_processed = True
                        full_reply += chunk
                        if chunk:  # don't send empty chunks after stripping
                            await llm_to_client_q.put(chunk)
                            await llm_to_tts_q.put(chunk)
            except Exception as exc:
                logger.error(f"llm.stream_error session={session_id} error={exc}")
                await llm_to_client_q.put({"error": str(exc)})
            finally:
                await llm_to_client_q.put(None)
                await llm_to_tts_q.put(None)
                # Strip tag from full_reply before saving to history
                full_reply = full_reply.strip()
                _push_history(session_id, "user",      user_text,  language)
                _push_history(session_id, "assistant", full_reply, language)
                _active_tasks.pop(session_id, None)

        async def tts_input_gen():
            """Bridge TTS queue → async generator for stream_tts()."""
            while True:
                token = await llm_to_tts_q.get()
                if token is None:
                    break
                if isinstance(token, str):
                    yield token

        producer_task = asyncio.create_task(llm_producer())
        _active_tasks[session_id] = producer_task

        # ── Text streamer ─────────────────────────────────────────────────────
        async def text_streamer():
            """Yields SSE text events from LLM queue."""
            while True:
                token = await llm_to_client_q.get()
                if token is None:
                    break
                if isinstance(token, dict):
                    if "model" in token:
                        yield "data: " + json.dumps({"type": "model", "content": token["model"]}) + "\n\n"
                        continue
                    yield "data: " + json.dumps({"type": "error", "content": token.get("error", "")}) + "\n\n"
                    break
                yield "data: " + json.dumps({"type": "text", "content": token}) + "\n\n"

        # ── Audio streamer ────────────────────────────────────────────────────
        async def audio_streamer():
            """Yields SSE audio events from TTS provider."""
            try:
                async for audio_b64 in stream_tts(tts_input_gen(), language):
                    yield "data: " + json.dumps({"type": "audio", "content": audio_b64}) + "\n\n"
            except Exception as exc:
                logger.error(f"tts.stream_error session={session_id} error={exc}")

        # ── Merge both streams ─────────────────────────────────────────────────
        gen_text  = text_streamer()
        gen_audio = audio_streamer()

        pending: dict[asyncio.Task, str] = {
            asyncio.create_task(gen_text.__anext__()):  "text",
            asyncio.create_task(gen_audio.__anext__()): "audio",
        }

        t_llm_first    = 0.0
        t_tts_first    = 0.0
        internal_start = time.perf_counter()
        first_token_sent = False

        while pending:
            done, _ = await asyncio.wait(pending.keys(), return_when=asyncio.FIRST_COMPLETED)
            for task in done:
                stream_type = pending.pop(task)
                try:
                    val = await task
                    if val:
                        now = time.perf_counter()

                        # ── TTFT badge ─────────────────────────────────────────
                        if stream_type == "text" and not first_token_sent:
                            t_llm_first = (now - internal_start) * 1000
                            first_token_sent = True
                            yield "data: " + json.dumps({
                                "type":       "ttft",
                                "latency_ms": round(t_llm_first),
                            }) + "\n\n"

                        if stream_type == "audio" and not t_tts_first:
                            t_tts_first = (now - internal_start) * 1000

                        yield val

                    # Re-schedule the generator
                    if stream_type == "text":
                        pending[asyncio.create_task(gen_text.__anext__())]  = "text"
                    else:
                        pending[asyncio.create_task(gen_audio.__anext__())] = "audio"

                except (StopAsyncIteration, asyncio.CancelledError):
                    continue  # Generator exhausted — don't re-schedule

        # ── Done event with final latencies ───────────────────────────────────
        total_ms = (time.perf_counter() - internal_start) * 1000
        _stats["total_latency_ms"] += total_ms

        mdl_lower = shared_stats["model"].lower()
        if "offline" in mdl_lower or "llama" in mdl_lower or "ollama" in mdl_lower:
            fallback_provider = "Ollama"
        else:
            fallback_provider = "Gemini"  # sole cloud LLM — OpenAI removed

        yield "data: " + json.dumps({
            "type":     "done",
            "model":    shared_stats["model"],
            "language": language,
            "provider": fallback_provider,
            "latency": {
                "stt":   f"{payload.stt_latency_ms:.0f} ms",
                "llm":   f"{t_llm_first:.0f} ms",
                "tts":   f"{t_tts_first:.0f} ms",
                "total": f"{(payload.stt_latency_ms + total_ms):.0f} ms",
            },
        }) + "\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


# ── WebSocket /ws/chat — Real-time bidirectional ──────────────────────────────
@app.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    """
    WebSocket endpoint with 25-second keepalive ping to prevent idle timeout.
    Handles ping/pong frames.
    """
    await websocket.accept()
    logger.info("ws.connected")

    async def keepalive():
        """Send ping every 25 seconds to keep connection alive."""
        while True:
            await asyncio.sleep(25)
            try:
                await websocket.send_json({"type": "ping"})
            except Exception:
                break

    ping_task = asyncio.create_task(keepalive())

    try:
        while True:
            raw = await websocket.receive_text()
            data = json.loads(raw)

            # Handle pong response
            if data.get("type") == "pong":
                continue

            # Handle chat message
            if data.get("type") == "chat":
                text       = data.get("text", "").strip()
                session_id = data.get("session_id", "default")

                if not text:
                    await websocket.send_json({"type": "error", "content": "empty_input"})
                    continue

                lang_hist            = _get_rolling_lang(session_id)
                language, confidence = detect_language(text, lang_hist)
                history              = _get_history(session_id)
                full_reply           = ""

                await websocket.send_json({
                    "type":       "meta",
                    "language":   language,
                    "flag":       get_flag(language),
                    "confidence": confidence,
                })

                async for chunk in stream_reply(text, language, history):
                    if isinstance(chunk, dict):
                        continue
                    full_reply += chunk
                    await websocket.send_json({"type": "token", "content": chunk})

                _push_history(session_id, "user",      text,       language)
                _push_history(session_id, "assistant", full_reply, language)
                await websocket.send_json({"type": "done"})

    except WebSocketDisconnect:
        logger.info("ws.disconnected")
    except Exception as exc:
        logger.error(f"ws.error {exc}")
    finally:
        ping_task.cancel()


# ── Entrypoint ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
