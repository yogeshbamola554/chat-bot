from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
import json as pyjson
from .state_machine import ChatStateMachine
from .models import User
from .services.chat_service import get_chat_history, save_chat, update_conversation_summary
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
    user = None

    # ✅ Step 1: Get user object if exists
    if phone:
        try:
            user = User.objects.get(phone=phone)
        except User.DoesNotExist:
            user = None

    # ✅ Step 2: Logout case
    if user_message.lower() == "logout":
        if user:
            user.is_verified = False
            user.save()
        request.session.flush()
        reply = "✅ You have been logged out."

    # ✅ Step 3: Skip messages (OTP, verification etc.)
    elif not should_send_to_llm(user_message):
        reply = state_machine.handle_message(request, user_message)
        if "Verified" in reply:
            refresh_history = True

    # ✅ Step 4: Normal AI conversation
    else:
        # Save user message first
        if user:
            save_chat(user, "user", user_message)

        # Let Gemini handle the response (skip state machine here)
        llm_raw = process_user_message(user_message, user=user)

        # Clean markdown fences if present
        if llm_raw.startswith("```"):
            llm_raw = llm_raw.strip("`").replace("json", "").strip()

        # Try JSON parse → fallback to text
        try:
            parsed = pyjson.loads(llm_raw)
            reply = parsed.get("reply", llm_raw)
        except Exception:
            reply = llm_raw

        # 🧹 Clean reply — remove redundant "Bot:" prefixes or context
        import re
        clean_reply = re.sub(r"^(🤖\s*)?(Bot:|FitnessBot:)\s*", "", reply.strip(), flags=re.IGNORECASE)

        reply = clean_reply

    # ✅ Step 5: Save bot reply and update memory summary
    if user and reply:
        save_chat(user, "bot", reply)
        update_conversation_summary(user, limit=200)

    return JsonResponse({"reply": reply, "refresh_history": refresh_history})


# @csrf_exempt
# def chat_api(request):
#     """
#     Handle AJAX chat messages (user + bot exchange).
#     Returns JSON with the bot's reply.
#     """
#     if request.method != "POST":
#         return JsonResponse({"error": "Invalid request"}, status=405)

#     data = pyjson.loads(request.body)
#     user_message = data.get("message", "").strip()
#     reply = None
#     refresh_history = False

#     phone = request.session.get("phone")
#     user = None

#     # ✅ Step 1: Try to get the user object if phone is available
#     if phone:
#         try:
#             user = User.objects.get(phone=phone)
#         except User.DoesNotExist:
#             user = None

#     # Case 1: Logout
#     if user_message.lower() == "logout":
#         if user:
#             user.is_verified = False
#             user.save()
#         request.session.flush()
#         reply = "✅ You have been logged out."

#     # Case 2: Messages we skip sending to Gemini (OTP, registration flow, etc.)
#     elif not should_send_to_llm(user_message):
#         reply = state_machine.handle_message(request, user_message)

#         # Detect OTP verification success → refresh history in frontend
#         if "Verified" in reply:
#             refresh_history = True

#     # Case 3: Normal chat (state machine + LLM)
#     else:
#         # Handle state logic (if any)
#         bot_reply = state_machine.handle_message(request, user_message)

#         # ✅ Step 2: Send message + user (for memory) to Gemini
#         llm_raw = process_user_message(user_message, user=user)

#         # ✅ Step 3: Clean markdown fences
#         if llm_raw.startswith("```"):
#             llm_raw = llm_raw.strip("`").replace("json", "").strip()

#         # ✅ Step 4: Try parsing JSON reply safely
#         try:
#             parsed = pyjson.loads(llm_raw)
#             llm_reply = parsed.get("reply", bot_reply)
#         except Exception:
#             llm_reply = llm_raw

#         reply = llm_reply or bot_reply
#         clean_reply = reply.strip()

#     # ✅ Step 5: Save bot reply
#     if user and reply:
#         save_chat(user, "bot", reply)
#         update_conversation_summary(user, limit=200)  # 🧠 refresh summary

#     return JsonResponse({"reply": reply, "refresh_history": refresh_history})


# @csrf_exempt
# def chat_api(request):
#     """
#     Handle AJAX chat messages (user + bot exchange).
#     Returns JSON with the bot's reply.
#     """
#     if request.method != "POST":
#         return JsonResponse({"error": "Invalid request"}, status=405)

#     data = pyjson.loads(request.body)
#     user_message = data.get("message", "").strip()
#     reply = None
#     refresh_history = False

#     phone = request.session.get("phone")

#     # Case 1: Logout
#     if user_message.lower() == "logout":
#         if phone:
#             try:
#                 user = User.objects.get(phone=phone)
#                 user.is_verified = False
#                 user.save()
#             except User.DoesNotExist:
#                 pass
#         request.session.flush()
#         reply = "✅ You have been logged out."

#     # Case 2: Messages we skip sending to Gemini (OTP, registration flow, etc.)
#     elif not should_send_to_llm(user_message):
#         reply = state_machine.handle_message(request, user_message)

#         # Detect OTP verification success → refresh history in frontend
#         if "Verified" in reply:
#             refresh_history = True

#     # Case 3: Normal chat (state machine + LLM)
#     else:
#         bot_reply = state_machine.handle_message(request, user_message)

#         llm_raw = process_user_message(user_message, user=user)
#         if llm_raw.startswith("```"):
#             llm_raw = llm_raw.strip("`").replace("json", "").strip()

#         try:
#             parsed = pyjson.loads(llm_raw)
#             llm_reply = parsed.get("reply", bot_reply)
#         except Exception:
#             llm_reply = llm_raw

#         reply = llm_reply or bot_reply

#     # Save bot reply
#     if phone and reply:
#         try:
#             user = User.objects.get(phone=phone, is_verified=True)
#             save_chat(user, "bot", reply)
#         except User.DoesNotExist:
#             pass

#     return JsonResponse({"reply": reply, "refresh_history": refresh_history})


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
