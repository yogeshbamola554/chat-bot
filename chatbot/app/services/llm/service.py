from .config import llm
from .prompts import structured_prompt

def process_user_message(user_message: str) -> dict:
    messages = structured_prompt.format_messages(user_input=user_message)
    response = llm(messages)
    return response.content
