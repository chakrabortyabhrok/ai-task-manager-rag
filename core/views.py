import os
from .models import Task
from .serializers import TaskSerializer, AuthSerializer
from .filters import TaskFilter
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status
from rest_framework.viewsets import ModelViewSet
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.pagination import PageNumberPagination
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import api_view
from django.db import connection
from django.contrib.auth import get_user_model
from .ai_utils import ask_ai_about_tasks, get_vectorstore
from rest_framework.permissions import AllowAny


class AskAIView(APIView):
    """
    API endpoint to ask questions about tasks using natural language.
    """

    def post(self, request):
        question = request.data.get('question', '').strip()

        if not question:
            return Response(
                {"error": "Question is required."},
                status = status.HTTP_400_BAD_REQUEST
            )

        #Get answer from OpenAI
        answer = ask_ai_about_tasks(question, request.user)

        return Response({"answer": answer}, status=status.HTTP_200_OK)

# class StandardPagination(PageNumberPagination):
#     page_size = 50
#     page_size_query_param = 'page_size'
#     max_page_size = 100

class TaskViewSet(ModelViewSet):
    """ API ViewSet for managing tasks with filtering, searching, and pagination. """
    queryset = Task.objects.all()
    serializer_class = TaskSerializer 
    lookup_field = 'pk'
    search_fields = ['title', 'description']

    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = TaskFilter
    # pagination_class = StandardPagination
    ordering_fields = ['due_date', 'created_at', 'title']
     
    def get_serializer(self, *args, **kwargs):
        
        if isinstance(kwargs.get('data'), list):
            kwargs['many'] = True
        return super().get_serializer(*args, **kwargs)

@api_view(['GET'])
def vectorstore_status(request):
    """
    Check the current vector store and how many tasks are embedded.
    """
    try:
        vectorstore = get_vectorstore()
        store_type = "pgvector" if os.environ.get("DATABASE_URL") else "no store type"

        # Count documents
        try:
            docs = vectorstore.similarity_search("task", k=1000)
            count = len(docs)
        except Exception:
            count = 0

        return Response({
            "status": "active",
            "vector_store": store_type,
            "tasks_in_vectorstore": count,
            "message": f"Currently {count} tasks are embedded in {store_type}"
        })

    except Exception as e:
        return Response({
            "status": "error",
            "message": str(e),
            "tasks_in_vectorstore": 0
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
User = get_user_model()

class CreateSuperUserView(APIView):
    """
    Temporary view to create a superuser on production.
    Delete this after creating the superuser.
    """
    def post(self, request):
        secret_key = request.data.get("secret_key", "")
        
        # Change this secret key to something only you know
        if secret_key != "create-superuser-2026":
            return Response({"error": "Invalid secret key"}, status=status.HTTP_403_FORBIDDEN)

        username = request.data.get("username")
        password = request.data.get("password")
        email = request.data.get("email", "")

        if not username or not password:
            return Response({"error": "username and password are required"}, status=status.HTTP_400_BAD_REQUEST)

        if User.objects.filter(username=username).exists():
            return Response({"error": "User already exists"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.create_superuser(
                username=username,
                email=email,
                password=password
            )
            return Response({
                "message": f"Superuser '{username}' created successfully",
                "username": user.username
            }, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        

class RegisterView(APIView):
    # Overriding global IsAuthenticated setting so anyone can register
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = AuthSerializer(data=request.data)

        if serializer.is_valid():
            user = serializer.save()

            return Response(
                {
                    "message": "User registered successfully. ",
                    "user": {
                        "id": user.id,
                        "username": user.username,
                        "email": user.email
                    }
                },
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)



#class DeleteAllTasksView(APIView):
    #"""
#    Temporary view to delete ALL tasks from the database.
#    DELETE this view after you are done using it.
#    """
#    def post(self, request):
#        secret_key = request.data.get("secret_key", "")

#        # Change this secret key to something only you know
#        if secret_key != "delete-all-2026":
#            return Response({"error": "Invalid secret key"}, status=status.HTTP_403_FORBIDDEN)

#        from core.models import Task
#        deleted_count, _ = Task.objects.all().delete()

#        return Response({
#            "message": f"Successfully deleted {deleted_count} tasks",
#            "deleted_count": deleted_count
#        }, status=status.HTTP_200_OK)
    
#class ClearVectorstoreView(APIView):
#    """
#    Temporary view to completely clear the pgvector collection.
#    DELETE this view after use.
#    """
#    def post(self, request):
#        secret_key = request.data.get("secret_key", "")

#        if secret_key != "clear-vectorstore-2026":
#            return Response({"error": "Invalid secret key"}, status=status.HTTP_403_FORBIDDEN)

#        from core.ai_utils import clear_vectorstore

#        success = clear_vectorstore()

#        if success:
#            return Response({
#                "message": "Vector store cleared successfully",
#                "status": "cleared"
#            }, status=status.HTTP_200_OK)
#        else:
#            return Response({
#                "message": "Failed to clear vector store (maybe running on SQLite or error occurred)",
#                "status": "failed"
#            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)