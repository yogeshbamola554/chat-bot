from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
import json as pyjson

from .state_machine import ChatStateMachine
from .models import User
from .services.chat_service import get_chat_history, save_chat
from .services.llm_service import process_user_message, should_send_to_llm

state_machine = ChatStateMachine()


def chat_page(request):
    """
    Render chat template with history (GET only).
    All conversation is handled via AJAX (chat_api).
    """
    history = None
    phone = request.session.get("phone")
    if phone:
        try:
            user = User.objects.get(phone=phone, is_verified=True)
            history = get_chat_history(user)
        except User.DoesNotExist:
            pass

    return render(request, "chat.html", {"history": history})


@csrf_exempt
def chat_api(request):
    """
    Handle AJAX chat messages (user + bot exchange).
    Returns JSON with the bot's reply.
    """
    if request.method != "POST":
        return JsonResponse({"error": "Invalid request"}, status=405)

    data = pyjson.loads(request.body)
    user_message = data.get("message", "").strip()
    reply = None
    refresh_history = False

    phone = request.session.get("phone")

    # Case 1: Logout
    if user_message.lower() == "logout":
        if phone:
            try:
                user = User.objects.get(phone=phone)
                user.is_verified = False
                user.save()
            except User.DoesNotExist:
                pass
        request.session.flush()
        reply = "✅ You have been logged out."

    # Case 2: Messages we skip sending to Gemini (OTP, registration flow, etc.)
    elif not should_send_to_llm(user_message):
        reply = state_machine.handle_message(request, user_message)

        # Detect OTP verification success → refresh history in frontend
        if "Verified" in reply:
            refresh_history = True

    # Case 3: Normal chat (state machine + LLM)
    else:
        bot_reply = state_machine.handle_message(request, user_message)

        llm_raw = process_user_message(user_message)
        if llm_raw.startswith("```"):
            llm_raw = llm_raw.strip("`").replace("json", "").strip()

        try:
            parsed = pyjson.loads(llm_raw)
            llm_reply = parsed.get("reply", bot_reply)
        except Exception:
            llm_reply = llm_raw

        reply = llm_reply or bot_reply

    # Save bot reply
    if phone and reply:
        try:
            user = User.objects.get(phone=phone, is_verified=True)
            save_chat(user, "bot", reply)
        except User.DoesNotExist:
            pass

    return JsonResponse({"reply": reply, "refresh_history": refresh_history})


@csrf_exempt
def chat_history_api(request):
    """
    Return chat history for the logged-in/verified user.
    """
    phone = request.session.get("phone")
    if phone:
        try:
            user = User.objects.get(phone=phone, is_verified=True)
            history = get_chat_history(user)
            return JsonResponse({
                "history": [
                    {"sender": chat.sender, "message": chat.message}
                    for chat in history
                ]
            })
        except User.DoesNotExist:
            pass
    return JsonResponse({"history": []})
