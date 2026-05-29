"""
backend/config.py
Centralized configuration — all env-based settings with defaults.
"""

import os

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None  # type: ignore

if load_dotenv is not None:
    load_dotenv()

# ── LLM Keys ─────────────────────────────────────────────────────────────────────
GEMINI_API_KEYS: list[str] = [
    k.strip() for k in os.getenv("GEMINI_API_KEYS", "").split(",") if k.strip()
]
ELEVENLABS_API_KEYS: list[str] = [
    k.strip() for k in os.getenv("ELEVENLABS_API_KEYS", "").split(",") if k.strip()
]
ELEVENLABS_TTS_URL: str = os.getenv("ELEVENLABS_TTS_URL", "https://api.elevenlabs.io/v1/text-to-speech")
ELEVENLABS_MODEL: str = os.getenv("ELEVENLABS_MODEL", "eleven_multilingual_v2")

# OpenAI removed — kept as empty list so any stale import doesn't raise AttributeError
OPENAI_API_KEYS: list[str] = []

# ── TTS Keys ──────────────────────────────────────────────────────────────────
SARVAM_API_KEYS: list[str] = [
    k.strip() for k in os.getenv("SARVAM_API_KEYS", "").split(",") if k.strip()
]
SARVAM_TTS_URL: str = os.getenv("SARVAM_TTS_URL", "https://api.sarvam.ai/text-to-speech")
SARVAM_STT_URL: str = os.getenv("SARVAM_STT_URL", "https://api.sarvam.ai/speech-to-text")
SARVAM_CHAT_URL: str = os.getenv("SARVAM_CHAT_URL", "https://api.sarvam.ai/v1/chat")
SARVAM_WS_URL: str = os.getenv("SARVAM_WS_URL", "wss://api.sarvam.ai/text-to-speech/ws")

# ── Provider Settings ────────────────────────────────────────────────────────────────────
# OpenAI removed: PRIMARY_LLM_PROVIDER is always 'gemini'
PRIMARY_LLM_PROVIDER: str = "gemini"
PRIMARY_TTS_PROVIDER: str = os.getenv("PRIMARY_TTS_PROVIDER", "sarvam")
LLM_PROVIDER_TIMEOUT_MS: int = int(os.getenv("LLM_PROVIDER_TIMEOUT_MS", "1500"))
TTS_PROVIDER_TIMEOUT_MS: int = int(os.getenv("TTS_PROVIDER_TIMEOUT_MS", "3000"))

# ── Key Manager ───────────────────────────────────────────────────────────────
KEY_RATE_LIMIT_COOLDOWN_SECONDS: int = int(
    os.getenv("KEY_RATE_LIMIT_COOLDOWN_SECONDS", "60")
)
KEY_MAX_FAIL_COUNT: int = int(os.getenv("KEY_MAX_FAIL_COUNT", "3"))
KEY_RECOVERY_CHECK_INTERVAL_SECONDS: int = int(
    os.getenv("KEY_RECOVERY_CHECK_INTERVAL_SECONDS", "30")
)

# ── Performance ───────────────────────────────────────────────────────────────
RESPONSE_CACHE_TTL_SECONDS: int = int(os.getenv("RESPONSE_CACHE_TTL_SECONDS", "300"))
MAX_CONVERSATION_MEMORY_TURNS: int = int(os.getenv("MAX_CONVERSATION_MEMORY_TURNS", "10"))
SESSION_TTL_MINUTES: int = int(os.getenv("SESSION_TTL_MINUTES", "30"))

# ── Server ────────────────────────────────────────────────────────────────────
HOST: str = os.getenv("HOST", "0.0.0.0")
PORT: int = int(os.getenv("PORT", "8000"))
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

# ── Model ─────────────────────────────────────────────────────────────────────
DEFAULT_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite")

# ── Whisper ASR (Tier 2 fallback + WebSocket /ws/stt) ────────────────────────
# large-v3      → highest accuracy, ~3GB VRAM (GPU) / very slow on CPU
# large-v3-turbo→ 4× faster, similar accuracy — recommended for CPU
# medium        → good balance ~600MB RAM
# base          → fastest, ~150MB RAM, lower Indian language accuracy
# Override via .env: WHISPER_MODEL=medium
WHISPER_MODEL_SIZE: str = os.getenv("WHISPER_MODEL", "large-v3")

# ── Per-language STT/TTS routing config ───────────────────────────────────────
# stt="sarvam"   → MediaRecorder path → /stt/stream (Sarvam ASR + Whisper fallback)
# stt="webspeech"→ existing Web Speech API path (unchanged)
LANGUAGE_CONFIG: dict[str, dict] = {
    "kn-IN": {"name": "Kannada",   "stt": "sarvam",    "tts": "sarvam", "script": "kannada",    "whisper_code": "kn"},
    "mr-IN": {"name": "Marathi",   "stt": "sarvam",    "tts": "sarvam", "script": "devanagari", "whisper_code": "mr"},
    "bn-IN": {"name": "Bengali",   "stt": "sarvam",    "tts": "sarvam", "script": "bengali",    "whisper_code": "bn"},
    "te-IN": {"name": "Telugu",    "stt": "sarvam",    "tts": "sarvam", "script": "telugu",     "whisper_code": "te"},
    "ta-IN": {"name": "Tamil",     "stt": "sarvam",    "tts": "sarvam", "script": "tamil",      "whisper_code": "ta"},
    "hi-IN": {"name": "Hindi",     "stt": "sarvam",    "tts": "sarvam", "script": "devanagari", "whisper_code": "hi"},
    "en-IN": {"name": "English",   "stt": "webspeech", "tts": "edge",   "script": "latin",      "whisper_code": "en"},
    "gu-IN": {"name": "Gujarati",  "stt": "sarvam",    "tts": "sarvam", "script": "gujarati",   "whisper_code": "gu"},
    "ml-IN": {"name": "Malayalam", "stt": "sarvam",    "tts": "sarvam", "script": "malayalam",  "whisper_code": "ml"},
    "pa-IN": {"name": "Punjabi",   "stt": "sarvam",    "tts": "sarvam", "script": "gurmukhi",   "whisper_code": "pa"},
}

# Languages that must use the backend ASR path (not Web Speech API)
BACKEND_STT_LANGS: list[str] = [
    code for code, cfg in LANGUAGE_CONFIG.items() if cfg["stt"] == "sarvam"
]  # → ["kn-IN", "mr-IN", "bn-IN", "te-IN", "ta-IN"]
