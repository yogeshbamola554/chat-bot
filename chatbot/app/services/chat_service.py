from ..models import ChatHistory, User


def save_chat(user: User, sender: str, message: str):
    """Save chat to history"""
    ChatHistory.objects.create(user=user, sender=sender, message=message)


def get_chat_history(user: User):
    """Retrieve full chat history for a user"""
    return ChatHistory.objects.filter(user=user).order_by("timestamp")
