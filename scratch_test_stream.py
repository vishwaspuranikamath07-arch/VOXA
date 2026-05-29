import requests
import json
import traceback

try:
    resp = requests.post(
        "http://localhost:8000/chat/stream",
        json={"text": "What are you doing?", "session_id": "test_session_123"},
        stream=True
    )
    print(f"Status Code: {resp.status_code}")
    if resp.status_code != 200:
        print(f"Error: {resp.text}")
        
    for line in resp.iter_lines():
        if line:
            line_str = line.decode('utf-8')
            if line_str.startswith("data: "):
                try:
                    data = json.loads(line_str[6:])
                    print(f"Type: {data.get('type')}")
                    if data.get("type") == "error":
                        print(f"Error: {data.get('content')}")
                    elif data.get("type") == "audio":
                        print(f"Audio chunk: {len(data.get('content', ''))} chars")
                except Exception as e:
                    print(f"JSON Parse Error: {e} - Line: {line_str}")
except Exception as e:
    print(f"Request Error: {e}")
    traceback.print_exc()
