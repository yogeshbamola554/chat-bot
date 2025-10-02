from django.shortcuts import render
from .state_machine import ChatStateMachine
from .models import User
from .services.chat_service import get_chat_history
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from .services.llm.service import process_user_message

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

@csrf_exempt
def llm_query(request):
    if request.method == "POST":
        data = json.loads(request.body)
        user_message = data.get("message", "")
        response = process_user_message(user_message)
        return JsonResponse({"response": response})
    return JsonResponse({"error": "Only POST allowed"}, status=405)