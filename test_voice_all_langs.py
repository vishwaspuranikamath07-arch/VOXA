import asyncio
import httpx
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

async def test_voice_all_langs():
    phrases = [
        ("English", "en-IN", "Hello, I want to order some food. What do you recommend?"),
        ("Tamil", "ta-IN", "உனக்கு என்ன சாப்பிட பிடிக்கும்?"), 
        ("Telugu", "te-IN", "నేను ఏం తినాలి"), 
        ("Kannada", "kn-IN", "ನನಗೆ ಊಟ ಬೇಕು"), 
        ("Malayalam", "ml-IN", "എനിക്ക് എന്തെങ്കിലും കഴിക്കണം"), 
        ("Hindi", "hi-IN", "मुझे कुछ अच्छा खाना है"), 
        ("Bengali", "bn-IN", "আমি কিছু মিষ্টি খেতে চাই"), 
        ("Marathi", "mr-IN", "मला काही तरी तिखट खायचंय"), 
        ("Gujarati", "gu-IN", "મારે કંઈક ખાવું છે"), 
        ("Punjabi", "pa-IN", "ਮੈਨੂੰ ਭੁੱਖ ਲੱਗੀ ਹੈ"), 
    ]

    print("Starting Voice Input STT test for all 10 languages...")
    
    async with httpx.AsyncClient(timeout=60) as client:
        for lang_name, lang_code, text in phrases:
            print(f"\n======================================")
            print(f"--- Testing {lang_name} ({lang_code}) ---")
            print(f"Target Text: {text}")
            
            # 1. Get TTS Audio
            print(f"-> Generating TTS audio...")
            try:
                tts_resp = await client.post(
                    "http://127.0.0.1:8000/tts/generate",
                    json={"text": text, "language": lang_name}
                )
                
                if tts_resp.status_code != 200:
                    print(f"[ERROR] TTS HTTP {tts_resp.status_code}: {tts_resp.text}")
                    continue
                    
                if "application/json" in tts_resp.headers.get("content-type", ""):
                    print(f"[ERROR] TTS Failed (JSON returned): {tts_resp.json()}")
                    continue
                    
                audio_bytes = tts_resp.content
                print(f"   Generated {len(audio_bytes)} bytes of audio (Provider: {tts_resp.headers.get('x-tts-provider')})")
                
                # 2. Test STT
                print(f"-> Testing STT endpoint (/stt/stream)...")
                stt_resp = await client.post(
                    f"http://127.0.0.1:8000/stt/stream?language={lang_code}",
                    content=audio_bytes,
                    headers={"Content-Type": "audio/wav"}
                )
                
                if stt_resp.status_code == 200:
                    data = stt_resp.json()
                    print(f"   [STT Output] Transcript: {data.get('transcript')}")
                    print(f"   [STT Stats] Provider: {data.get('provider')} | Confidence: {data.get('confidence')}")
                    if data.get('error'):
                        print(f"   [STT Error] {data.get('error')}")
                else:
                    print(f"   [ERROR] STT HTTP {stt_resp.status_code}: {stt_resp.text}")
            
            except Exception as e:
                print(f"[EXCEPTION] Failed during test for {lang_name}: {e}")

if __name__ == "__main__":
    asyncio.run(test_voice_all_langs())
