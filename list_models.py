import os
from google import genai
from dotenv import load_dotenv

load_dotenv()

def list_models():
    api_key = "AIzaSyBlHvvqZze8nwmX1dL_FEbCAw4vZ33uJqc"
    try:
        client = genai.Client(api_key=api_key)
        print("AVAILABLE MODELS:")
        for m in client.models.list():
            print(f" - {m.name}")
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    list_models()
