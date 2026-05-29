import os
from google import genai
from dotenv import load_dotenv

load_dotenv()

def test_key():
    api_key = "AIzaSyBlHvvqZze8nwmX1dL_FEbCAw4vZ33uJqc"
    try:
        client = genai.Client(api_key=api_key)
        resp = client.models.generate_content(
            model="gemini-2.5-flash-lite",
            contents="Say 'Key works!'"
        )
        print(f"RESULT: {resp.text}")
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    test_key()
