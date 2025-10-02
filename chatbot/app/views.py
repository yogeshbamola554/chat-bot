from django.shortcuts import render
from .state_machine import ChatStateMachine
from .models import User
from .services.chat_service import get_chat_history


state_machine = ChatStateMachine()

def chat_page(request):
    bot_reply = None
    history = None

    if request.method == "POST":
        user_message = request.POST.get("message", "").strip()
        bot_reply = state_machine.handle_message(request, user_message)

        # ✅ Fetch chat history if user is verified
        phone = request.session.get("phone")
        if phone:
            try:
                user = User.objects.get(phone=phone, is_verified=True)
                history = get_chat_history(user)
            except User.DoesNotExist:
                history = None
    else:
        # ✅ If already logged in and verified, show previous chat
        phone = request.session.get("phone")
        if phone:
            try:
                user = User.objects.get(phone=phone, is_verified=True)
                history = get_chat_history(user)
            except User.DoesNotExist:
                history = None

    return render(request, "chat.html", {
        "bot_reply": bot_reply, 
        "history": history
    })
