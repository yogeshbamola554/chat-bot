from ..models import ChatHistory, User, ConversationSummary


def save_chat(user: User, sender: str, message: str):
    """Save chat to history"""
    ChatHistory.objects.create(user=user, sender=sender, message=message)


def get_chat_history(user: User):
    """Retrieve full chat history for a user"""
    return ChatHistory.objects.filter(user=user).order_by("timestamp")

# def get_recent_chat_context(user, limit=5):
#     """
#     Fetch last `limit` pairs of user-bot messages (total 10 messages max).
#     Returns a formatted string usable as context for the LLM.
#     """
#     messages = ChatHistory.objects.filter(user=user).order_by('-timestamp')[:limit * 2]
#     messages = list(reversed(messages))  # chronological order
    

#     context = ""
#     for msg in messages:
#         speaker = "User" if msg.sender == "user" else "Bot"
#         context += f"{speaker}: {msg.message}\n"
#         print(context)

#     return context.strip()

def get_recent_chat_context(user, limit=5):
    chats = ChatHistory.objects.filter(user=user).order_by('-timestamp')[:limit * 2]
    chats = list(reversed(chats))

    lines = []
    for msg in chats:
        text = msg.message.strip()
        # Avoid prefixing again if already includes "Bot:" or "User:"
        if not text.lower().startswith(("bot:", "user:")):
            prefix = "User:" if msg.sender == "user" else "Bot:"
            text = f"{prefix} {text}"
        lines.append(text)

    return "\n".join(lines).strip()

def update_conversation_summary(user, limit=200):
    from .llm_service import summarize_text
    """
    Rebuild or update the conversation summary for the user.
    Keeps summary within ~200 words (or given limit).
    """
    # Get last 15–20 messages for context
    messages = ChatHistory.objects.filter(user=user).order_by("-timestamp")[:20]
    messages = list(reversed(messages))

    full_conversation = "\n".join([f"{m.sender}: {m.message}" for m in messages])

    # Get previous summary (if any)
    prev_summary = ""
    summary_obj, _ = ConversationSummary.objects.get_or_create(user=user)
    if summary_obj.summary_text:
        prev_summary = summary_obj.summary_text

    # Generate new summary
    updated_summary = summarize_text(full_conversation, existing_summary=prev_summary, word_limit=limit)

    # Save updated summary
    summary_obj.summary_text = updated_summary
    summary_obj.save()
