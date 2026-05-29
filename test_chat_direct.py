import asyncio
import sys
import os
from pathlib import Path

# Add project root
root = Path(__file__).resolve().parent
sys.path.append(str(root))

import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from backend.llm.key_manager import key_manager
from backend.main import chat, ChatRequest

async def main():
    await key_manager.initialize()
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
    
    session_id = "test_10"
    passed = 0
    
    for i, (expected_lang, text) in enumerate(phrases):
        print(f"\n--- Turn {i+1} ---")
        try:
            req = ChatRequest(text=text, session_id=session_id)
            res = await chat(req)
            print(f"User: {text}")
            print(f"Detected: {res.language}")
            print(f"Voxa: {res.response}")
            if res.error:
                print(f"Error: {res.error}")
            else:
                passed += 1
        except Exception as e:
            print(f"Exception: {e}")

if __name__ == "__main__":
    asyncio.run(main())
