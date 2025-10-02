import random
from ..models import OTP, User


def generate_otp(user: User) -> OTP:
    """Generate and store a new OTP for a user"""
    code = str(random.randint(100000, 999999))
    otp = OTP.objects.create(user=user, code=code)
    return otp


def verify_otp(user: User, code: str) -> bool:
    """Verify OTP correctness and expiry"""
    try:
        otp = OTP.objects.filter(user=user, code=code).latest("created_at")
    except OTP.DoesNotExist:
        return False

    if otp.is_expired():
        return False

    user.is_verified = True
    user.save()
    return True
