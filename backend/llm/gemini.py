from google import genai
import os
from dotenv import load_dotenv

load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))


def ask_gemini(prompt: str) -> str:
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash-lite",  # ⚡ fastest
            contents=prompt,
        )

        return response.text if response.text else "No response"

    except Exception as e:
        print("Gemini ERROR:", e)
        return "AI busy, try again"