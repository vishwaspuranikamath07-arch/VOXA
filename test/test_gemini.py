from google import genai
import os
from dotenv import load_dotenv

# 🔐 Load API key
load_dotenv()
API_KEY = os.getenv("AIzaSyBlHvvqZze8nwmX1dL_FEbCAw4vZ33uJqc")

# 🚀 Initialize client
client = genai.Client(api_key=API_KEY)

# 🧠 Models to test (fallback list)
MODELS = [
    "gemini-flash-latest",
    "gemini-pro-latest",
    "gemini-2.0-flash-lite",
]


# 🔍 Step 1: List available models
print("🔍 Available Models:\n")

try:
    models = client.models.list()
    for m in models:
        print("-", m.name)
except Exception as e:
    print("❌ Error listing models:", e)


# 🧪 Step 2: Test models one by one
print("\n🧪 Testing Models:\n")

prompt = "Hello, explain AI in one sentence."

for model in MODELS:
    try:
        print(f"➡️ Trying: {model}")

        response = client.models.generate_content(
            model=model,
            contents=prompt
        )

        if response.text:
            print("✅ SUCCESS with:", model)
            print("Response:", response.text)
            break

        else:
            print("⚠️ Empty response")

    except Exception as e:
        print(f"❌ Failed ({model}):", e)

else:
    print("\n❌ All models failed (quota or access issue)")