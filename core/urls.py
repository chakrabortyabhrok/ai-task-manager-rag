from rest_framework.routers import DefaultRouter
from django.urls import path
from .views import TaskViewSet, AskAIView, vectorstore_status, CreateSuperUserView

router = DefaultRouter()
router.register(r"tasks", TaskViewSet, basename="task")

urlpatterns = [
    path("tasks/ask_ai/", AskAIView.as_view(), name="ask-ai"),
    path("create-superuser/", CreateSuperUserView.as_view(), name="create-superuser"),
    path("vectorstore-status/", vectorstore_status, name="vectorstore-status"),
] + router.urls
