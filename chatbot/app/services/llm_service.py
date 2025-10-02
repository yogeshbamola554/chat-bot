import os
import json as pyjson
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import ChatPromptTemplate
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

if not GOOGLE_API_KEY:
    raise ValueError("⚠️ GOOGLE_API_KEY not found. Add it to .env")

# Initialize Gemini model
llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-pro",  # ✅ make sure this matches ListModels result
    temperature=0
)

# Structured prompt to enforce JSON output
structured_prompt = ChatPromptTemplate.from_messages([
    ("system", """You are a friendly fitness chatbot.
    Always reply in JSON format with:
    - intent: (what the user wants)
    - code: (any code you generate or extract, else null)
    - reply: (a natural first-person reply you would say directly to the user)
    """),
    ("human", "{user_input}")
])


def process_user_message(user_message: str) -> str:
    """
    Send user message to Gemini and return only the 'reply' field
    (first-person bot answer). Falls back to raw response if parsing fails.
    """
    messages = structured_prompt.format_messages(user_input=user_message)
    response = llm(messages)
    llm_raw = response.content.strip()

    # ✅ Clean markdown fences if present
    if llm_raw.startswith("```"):
        llm_raw = llm_raw.strip("`").replace("json", "").strip()

    # ✅ Parse JSON safely
    try:
        parsed = pyjson.loads(llm_raw)
        if isinstance(parsed, dict):
            return parsed.get("reply", llm_raw)  # default to reply
    except Exception:
        pass

    # If not JSON → return raw
    return llm_raw


def should_send_to_llm(message: str) -> bool:
    """
    Decide if a user message should be forwarded to the LLM.
    Certain control-flow messages (OTP, registration, etc.) should NOT go.
    """
    skip_messages = [
        "yes", "no",                # registration responses
        "edit number",
        "resend otp",
        "retry",
        "logout"
    ]

    # Any message that is exactly one of these should not go to LLM
    if message.lower().strip() in skip_messages:
        return False

    # Also: 10-digit numbers (phone) or 6-digit numbers (OTP)
    if message.isdigit() and (len(message) == 10 or len(message) == 6):
        return False

    return True
