import asyncio
import sys
import os
from pathlib import Path

# Add project root
root = Path(__file__).resolve().parent
sys.path.append(str(root))

from backend.llm.key_manager import key_manager, sarvam_keys
from backend.tts.router import generate_tts_with_fallback
from backend.main import _transcribe_whisper

async def main():
    await key_manager.initialize()
    await sarvam_keys.initialize()
    
    # Test TTS 10 times
    print("Testing TTS 10 times (Kannada)...")
    for i in range(1, 11):
        try:
            res = await generate_tts_with_fallback(f"Hello, this is test number {i}", "Kannada")
            print(f"[{i}/10] TTS Success: {res.success}, Provider: {res.provider}, Audio: {len(res.audio) if res.audio else 0} bytes")
            if not res.success:
                print(f"[{i}/10] TTS Error: {res.error}")
        except Exception as e:
            print(f"[{i}/10] Exception in TTS: {e}")
            
    # Test STT 10 times with input.wav if exists
    if os.path.exists("input.wav"):
        with open("input.wav", "rb") as f:
            audio_data = f.read()
        print("\nTesting Whisper STT 10 times...")
        for i in range(1, 11):
            try:
                res = await _transcribe_whisper(audio_data, "kn-IN")
                print(f"[{i}/10] STT: {res}")
            except Exception as e:
                print(f"[{i}/10] Exception in STT: {e}")

if __name__ == "__main__":
    asyncio.run(main())
