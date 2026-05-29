"""
End-to-end test: calls the live /chat endpoint with multiple languages
and verifies that language detection + LLM + TTS all work together.
"""
import asyncio, json, urllib.request, urllib.error, time, sys, os, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

API = "http://127.0.0.1:8000"

def post_chat(text, session_id="test"):
    payload = json.dumps({"text": text, "session_id": session_id}).encode("utf-8")
    req = urllib.request.Request(
        f"{API}/chat",
        data=payload,
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))

probes = [
    ("Hello! What can you do for me?",   "English",  "en"),
    ("Hola! Como puedo ayudarte?",        "Spanish",  "es"),
    ("Bonjour, vous allez bien?",         "French",   "fr"),
    ("Hello yaar, kya haal hai bhai?",    "Hinglish", "hi-mix"),
]

print("=" * 65)
print("  Voxa AI — End-to-End API Test")
print("=" * 65)

all_ok = True
for text, expected_lang, tag in probes:
    t0 = time.perf_counter()
    try:
        data = post_chat(text, session_id=f"test-{tag}")
        elapsed = round(time.perf_counter() - t0, 2)

        lang  = data.get("language", "?")
        model = data.get("model", "?")
        llm   = data.get("llm_latency", 0)
        tts   = data.get("tts_latency", 0)
        audio = data.get("audio") or "(none)"
        reply = (data.get("response") or "")[:80]

        lang_ok = lang == expected_lang
        audio_ok = bool(audio) and audio.startswith("/audio/")
        resp_ok = bool(reply)
        if not lang_ok or not resp_ok or not audio_ok:
            all_ok = False

        print(f"\n[{'OK' if (lang_ok and resp_ok) else 'FAIL'}] '{text[:45]}'")
        print(f"     Lang     : {lang} {'OK' if lang_ok else 'EXPECTED '+expected_lang}")
        print(f"     Reply    : {reply}")
        print(f"     Model    : {model}")
        print(f"     LLM      : {llm}s  |  TTS: {tts}s  |  Total: {elapsed}s")
        print(f"     Audio    : {audio}")
    except Exception as exc:
        all_ok = False
        print(f"\n[ERROR] '{text[:45]}' -> {exc}")

print()
print("=" * 65)
print(f"  Result: {'ALL TESTS PASSED' if all_ok else 'SOME TESTS FAILED'}")
print("=" * 65)
sys.exit(0 if all_ok else 1)
