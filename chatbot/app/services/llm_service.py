import os
import json as pyjson
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import ChatPromptTemplate
from dotenv import load_dotenv
from .chat_service import get_recent_chat_context

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


def process_user_message(user_message: str, user=None) -> str:
    """
    Send message + short-term memory + long-term summary to Gemini.
    """
    memory_context = ""
    long_term_summary = ""

    if user:
        memory_context = get_recent_chat_context(user, limit=5)
        try:
            long_term_summary = user.summary.summary_text or ""
        except Exception:
            long_term_summary = ""

    combined_prompt = f"{long_term_summary}\n\n{memory_context}"

    print(combined_prompt)

    messages = structured_prompt.format_messages(user_input=combined_prompt)
    response = llm(messages)
    llm_raw = response.content.strip()

    if llm_raw.startswith("```"):
        llm_raw = llm_raw.strip("`").replace("json", "").strip()

    try:
        parsed = pyjson.loads(llm_raw)
        if isinstance(parsed, dict):
            return parsed.get("reply", llm_raw)
    except Exception:
        pass

    return llm_raw


# def process_user_message(user_message: str, user=None) -> str:
#     """
#     Send user message + recent chat context to Gemini
#     and return only the 'reply' field.
#     """
#     # 🧠 Step 1: Build memory context
#     memory_context = ""
#     if user:
#         memory_context = get_recent_chat_context(user, limit=5)

#     # 🧠 Step 2: Combine context + new input
#     combined_prompt = f"{memory_context}\nUser: {user_message}\nBot:"
 
#     # 🧠 Step 3: Send to LLM
#     messages = structured_prompt.format_messages(user_input=combined_prompt)
#     response = llm(messages)
#     llm_raw = response.content.strip()

#     # ✅ Clean markdown fences
#     if llm_raw.startswith("```"):
#         llm_raw = llm_raw.strip("`").replace("json", "").strip()

#     # ✅ Try parsing JSON
#     try:
#         parsed = pyjson.loads(llm_raw)
#         if isinstance(parsed, dict):
#             return parsed.get("reply", llm_raw)
#     except Exception:
#         pass

#     return llm_raw

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

def summarize_text(chat_text, existing_summary=None, word_limit=200):
    """
    Use Gemini to update conversation summary in <= `word_limit` words.
    """
    if not chat_text.strip():
        return existing_summary or ""

    system_prompt = (
        f"You are an assistant that summarizes a user's conversation history in under {word_limit} words. "
        "Keep it concise but preserve key context, goals, and preferences. "
        "If an existing summary is provided, update and refine it instead of repeating details."
    )

    prompt = f"{system_prompt}\n\n"
    if existing_summary:
        prompt += f"Current summary:\n{existing_summary}\n\n"
    prompt += f"New chat segment:\n{chat_text}\n\nReturn the updated summary only."

    try:
        
        response = llm.invoke(prompt)
        return response.content.strip()
    except Exception as e:
        print(f"[Summary Error] {e}")
        return existing_summary or ""
