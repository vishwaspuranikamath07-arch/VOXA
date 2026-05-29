import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import requests
import json
import time

API = "http://127.0.0.1:8000/chat/stream"

def test_stream():
    payload = {"text": "Hello, how are you today? Tell me a short story.", "session_id": "test_streaming"}
    
    print("Connecting to stream...")
    with requests.post(API, json=payload, stream=True) as r:
        r.raise_for_status()
        for line in r.iter_lines():
            if line:
                decoded = line.decode('utf-8')
                if decoded.startswith("data: "):
                    content = json.loads(decoded.replace("data: ", ""))
                    ctype = content.get("type")
                    if ctype == "text":
                        print(content.get("content"), end="", flush=True)
                    elif ctype == "audio":
                        print(f"\n[Audio Chunk Received: {len(content.get('content'))} bytes]", end="")
                    elif ctype == "meta":
                        print(f"Meta: {content}")
                    elif ctype == "done":
                        print("\nStream finished.")

if __name__ == "__main__":
    test_stream()
