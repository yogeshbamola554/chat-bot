from .models import User
from .services.otp_service import generate_otp, verify_otp
from .services.chat_service import save_chat, get_chat_history


# -------------------------
# Base State
# -------------------------
class State:
    def handle(self, request, message):
        raise NotImplementedError


# -------------------------
# Individual States
# -------------------------
class PhoneState(State):
    def handle(self, request, message):
        if not (message.isdigit() and len(message) == 10):
            return "⚠️ Kindly enter a valid 10-digit phone number.", "phone"

        phone = message
        request.session["phone"] = phone

        try:
            user = User.objects.get(phone=phone)
            otp = generate_otp(user)
            return f"📱 Welcome back! Enter OTP sent to {phone}. (Dev OTP: {otp.code})", "otp_existing"
        except User.DoesNotExist:
            return "❌ You are not registered. Would you like to register? (Yes/No)", "register_prompt"


class RegisterPromptState(State):
    def handle(self, request, message):
        if message.lower() == "yes":
            phone = request.session.get("phone")
            user, _ = User.objects.get_or_create(phone=phone, is_verified=False)
            otp = generate_otp(user)
            return f"📱 Enter OTP sent to {phone} to complete registration. (Dev OTP: {otp.code})", "otp_new"
        return "🚫 Registration cancelled. Start again with your number.", "phone"


class OTPNewState(State):
    def handle(self, request, message):
        phone = request.session.get("phone")
        user = User.objects.get(phone=phone)

        if verify_otp(user, message):
            return "🎉 Registration complete! Welcome to FitnessBot 💪", "chat"

        # If wrong OTP
        request.session["last_otp_state"] = "otp_new"
        return "❌ Wrong OTP. Would you like to edit your number or resend the OTP?", "otp_failed"



class OTPExistingState(State):
    def handle(self, request, message):
        phone = request.session.get("phone")
        user = User.objects.get(phone=phone)

        if verify_otp(user, message):
            return "✅ Verified! Resuming your chat session.", "chat_with_history"

        # If wrong OTP
        request.session["last_otp_state"] = "otp_existing"
        return "❌ Wrong OTP. Would you like to edit your number or resend the OTP?", "otp_failed"

class ChatState(State):
    def handle(self, request, message):
        phone = request.session.get("phone")
        user = User.objects.get(phone=phone, is_verified=True)
        bot_reply = f"🤖 FitnessBot: You said '{message}'"
        save_chat(user, "user", message)
        save_chat(user, "bot", bot_reply)
        return bot_reply, "chat"


class ChatWithHistoryState(State):
    def handle(self, request, message):
        phone = request.session.get("phone")
        user = User.objects.get(phone=phone, is_verified=True)
        history = get_chat_history(user)
        bot_reply = "📜 Previous chat loaded. Now you can continue chatting."
        save_chat(user, "user", message)
        request.session["show_history"] = True
        return bot_reply, "chat"
    
class OtpFailedState(State):
    def handle(self, request, message):
        # If user chooses to edit number
        if message.lower() == "edit number":
            return "🔄 Please enter your phone number again:", "phone"

        # If user chooses to resend OTP
        elif message.lower() == "resend otp":
            phone = request.session.get("phone")
            user = User.objects.get(phone=phone)
            otp = generate_otp(user)
            return (
                f"📱 A new OTP has been sent to {phone}. (Dev OTP: {otp.code})",
                request.session.get("last_otp_state", "otp_existing"),
            )

        # ✅ If user chooses to retry entering OTP
        elif message.lower() == "retry":
            return "🔁 Please enter the OTP again:", request.session.get("last_otp_state", "otp")

        # If user types something else
        return "⚠️ Please choose one of the options below.", "otp_failed"



# -------------------------
# State Machine Controller
# -------------------------
class ChatStateMachine:
    def __init__(self):
        self.states = {
            "phone": PhoneState(),
            "register_prompt": RegisterPromptState(),
            "otp_new": OTPNewState(),
            "otp_existing": OTPExistingState(),
            "otp_failed": OtpFailedState(),
            "chat": ChatState(),
            "chat_with_history": ChatWithHistoryState(),
        }

    def handle_message(self, request, message):
        # ✅ Global Exit / Logout Command
        if message.strip().lower() in ["exit", "logout"]:
            phone = request.session.get("phone")
            if phone:
                from .models import User
                try:
                    user = User.objects.get(phone=phone)
                    user.is_verified = False
                    user.save()
                except User.DoesNotExist:
                    pass

            # Clear session
            request.session.flush()
            request.session["step"] = "phone"
            

            return "👋 You have been logged out. Please enter a new phone number to start again.", "phone"

        # Normal flow
        current_state = request.session.get("step", "phone")
        state_handler = self.states[current_state]
        bot_reply, next_state = state_handler.handle(request, message)
        request.session["step"] = next_state
        return bot_reply

