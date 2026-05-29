import asyncio
from backend.tts.router import call_elevenlabs_tts, call_edge_tts
from backend.llm.key_manager import key_manager

async def test():
    try:
        await key_manager.initialize()
        
        print("--- Testing ElevenLabs ---")
        try:
            key = await key_manager.get_next_key("elevenlabs")
            print(f"Got key: {key}")
            audio = await call_elevenlabs_tts("Hello, this is a test.", "en")
            print(f"ElevenLabs SUCCESS: {len(audio)} bytes")
        except Exception as e:
            print(f"ElevenLabs FAILED: {e}")
            import traceback
            traceback.print_exc()
            
        print("\n--- Testing Edge TTS ---")
        try:
            audio = await call_edge_tts("Hello, this is a test.", "en")
            print(f"Edge TTS SUCCESS: {len(audio)} bytes")
        except Exception as e:
            print(f"Edge TTS FAILED: {e}")
            import traceback
            traceback.print_exc()

    except Exception as e:
        print(f"Overall Error: {e}")

if __name__ == "__main__":
    asyncio.run(test())
