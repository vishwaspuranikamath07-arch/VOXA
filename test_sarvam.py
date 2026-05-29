import asyncio
import httpx
import base64
import os
from dotenv import load_dotenv

load_dotenv()

async def test_sarvam():
    sarvam_keys = os.getenv("SARVAM_API_KEYS").split(",")
    key = sarvam_keys[0]
    
    # Just a dummy payload to trigger auth or validation error
    dummy_audio = b"RIFF$" + b"\x00"*40  # dummy wave header
    
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://api.sarvam.ai/speech-to-text",
            headers={"api-subscription-key": key},
            files={"file": ("audio.wav", dummy_audio, "audio/wav")},
            data={"language_code": "hi-IN", "model": "saarika:v2"}
        )
        print(f"Status: {resp.status_code}")
        print(f"Response: {resp.text}")

asyncio.run(test_sarvam())
