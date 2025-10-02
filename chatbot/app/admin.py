from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User


class CustomUserAdmin(UserAdmin):
    model = User
    list_display = ("phone", "is_verified", "is_staff", "is_superuser")
    list_filter = ("is_staff", "is_superuser", "is_verified")
    search_fields = ("phone",)
    ordering = ("phone",)
    fieldsets = (
        (None, {"fields": ("phone", "password")}),
        ("Permissions", {"fields": ("is_staff", "is_superuser", "is_verified")}),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("phone", "password1", "password2", "is_staff", "is_superuser", "is_verified"),
        }),
    )


admin.site.register(User, CustomUserAdmin)
