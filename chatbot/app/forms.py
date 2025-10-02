from django import forms

class PhoneForm(forms.Form):
    phone = forms.CharField(max_length=15, label="Phone Number")

class OTPForm(forms.Form):
    otp = forms.CharField(max_length=6, label="OTP")
