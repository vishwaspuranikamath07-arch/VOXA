from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from backend.llm.router import generate_reply
from backend.utils import LanguageDetector

app = FastAPI()


class ChatRequest(BaseModel):
    text: str = Field(default="", max_length=1000)
    session_id: str = "default"


@app.post("/chat")
async def chat(req: ChatRequest):
    user_text = req.text.strip()

    if not user_text:
        return {"error": "Empty input"}

    detection = LanguageDetector.detect(user_text)
    language = detection["lang_name_display"]

    try:
        result = await generate_reply(
            user_text=user_text,
            language=language,
            history=[],
            llm_instruction=detection.get("llm_instruction", ""),
        )
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"LLM unavailable: {exc}") from exc

    return {
        "user": user_text,
        "response": result["text"],
        "lang": language,
        "model": result.get("model"),
    }
