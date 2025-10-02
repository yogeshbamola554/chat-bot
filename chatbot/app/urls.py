from django.urls import path
from . import views

urlpatterns = [
    path("chat/", views.chat_page, name="chat_page"),
    path("chat_api/", views.chat_api, name="chat_api"),  # new API endpoint
    path("chat_history_api/", views.chat_history_api, name="chat_history_api"),
]
