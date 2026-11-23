import httpx
from datetime import datetime
import json
from pathlib import Path

import config

GROQ_API_KEY = config.GROQ_API_KEY
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama3-70b-8192"

UNKNOWN_QUERIES_PATH = Path(__file__).resolve().parents[2] / "data" / "unknown_queries.json"

SYSTEM_PROMPT = """You are a support assistant for a Discord tournament bot.
Reply ONLY in Hinglish (mix of Hindi and English).
Help users with: slot availability, waiting room info, slot cancel, slot claiming, registration help.
If the question is not related to these topics, reply with: [unknown] (Sorry, main sirf slot aur registration se related madad kar sakta hoon.)
please do not use any bot commands in response like /claim, /cancel, etc.
"""

async def ask_ai(user_query: str, db_context: str = "") -> str:
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"{user_query}\n\nContext:\n{db_context}"}
    ]
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": GROQ_MODEL,
        "messages": messages,
        "temperature": 0.3
    }
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(GROQ_API_URL, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"].strip()
    except Exception:
        return "[unknown] (Sorry, main sirf slot aur registration se related madad kar sakta hoon.)"

async def log_unknown_query(query: str, user_id: int):
    UNKNOWN_QUERIES_PATH.parent.mkdir(parents=True, exist_ok=True)
    with UNKNOWN_QUERIES_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps({
            "timestamp": datetime.utcnow().isoformat(),
            "user_id": user_id,
            "query": query
        }) + "\n")
