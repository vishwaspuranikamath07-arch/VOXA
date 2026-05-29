import asyncio
import httpx
import time
import os

async def main():
    wav_path = "input.wav"
    if not os.path.exists(wav_path):
        print(f"File {wav_path} not found.")
        return

    with open(wav_path, "rb") as f:
        audio_data = f.read()

    print(f"Testing STT stream endpoint 10 times with {len(audio_data)} bytes...")
    
    async with httpx.AsyncClient(timeout=30) as client:
        for i in range(1, 11):
            t0 = time.time()
            try:
                resp = await client.post(
                    "http://127.0.0.1:8000/stt/stream?language=en-IN",
                    content=audio_data,
                    headers={"Content-Type": "audio/wav"}
                )
                dt = time.time() - t0
                if resp.status_code == 200:
                    data = resp.json()
                    print(f"[{i}/10] {dt:.2f}s | Provider: {data.get('provider')} | Transcript: {data.get('transcript')}")
                    if data.get('error'):
                        print(f"   -> Error: {data.get('error')}")
                else:
                    print(f"[{i}/10] {dt:.2f}s | HTTP {resp.status_code} | {resp.text}")
            except Exception as e:
                print(f"[{i}/10] {(time.time()-t0):.2f}s | Exception: {e}")

if __name__ == "__main__":
    asyncio.run(main())
