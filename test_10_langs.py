import asyncio
import httpx
import uuid
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

async def test_10_langs():
    session_id = uuid.uuid4().hex
    
    phrases = [
        ("English", "Hello, I want to order some food. What do you recommend?"),
        ("Tamil", "unnakku enna saapidu pidikkum?"), # What food do you like?
        ("Telugu", "nenu em tinali"), # What should I eat
        ("Kannada", "nange oota beku"), # I want food
        ("Malayalam", "enikku enthenkilum kazhikkanam"), # I want to eat something
        ("Hindi", "mujhe kuch achha khana hai"), # I want to eat something good
        ("Bengali", "ami kichu misti khete chai"), # I want to eat something sweet
        ("Marathi", "mala kahi tari tikhat khaychay"), # I want to eat something spicy
        ("Gujarati", "mare kaik khavu che"), # I want to eat something
        ("Punjabi", "mainu bhukh lagi hai"), # I am hungry
    ]

    print(f"Starting test with Session ID: {session_id}")
    
    async with httpx.AsyncClient(timeout=30) as client:
        for lang_name, text in phrases:
            print(f"\n--- Expected Input Lang: {lang_name} ---")
            print(f"User: {text}")
            
            payload = {
                "text": text,
                "session_id": session_id,
            }
            
            try:
                response = await client.post("http://127.0.0.1:8000/chat", json=payload)
                if response.status_code == 200:
                    data = response.json()
                    print(f"Voxa (Detected: {data['language']}): {data['response']}")
                else:
                    print(f"Error: HTTP {response.status_code} - {response.text}")
            except Exception as e:
                print(f"Request failed: {e}")

asyncio.run(test_10_langs())
