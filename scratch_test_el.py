import requests

url = "https://api.elevenlabs.io/v1/text-to-speech/IKne3meq5aSn9XLyUdCD"
headers = {
    "xi-api-key": "sk_ed8cc04558d09079955d8ea07a769181387957d04cd07475",
    "Content-Type": "application/json"
}
data = {
    "text": "Hello, this is Charlie.",
    "model_id": "eleven_multilingual_v2"
}

resp = requests.post(url, headers=headers, json=data)
print(f"Status: {resp.status_code}")
if resp.status_code != 200:
    print(resp.text)
else:
    print(f"Success: {len(resp.content)} bytes")
