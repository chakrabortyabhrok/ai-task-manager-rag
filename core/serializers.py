from rest_framework import serializers
from .models import Task, Category
from core.ai_utils import (
    generate_task_summary,
    add_task_to_vectorstore,
    auto_categorize_task,
)
from django.contrib.auth import get_user_model

User = get_user_model()


class TaskSerializer(serializers.ModelSerializer):
    """Serializer for Task model with custom category handling and AI summary and Vector Embeddings."""

    category = serializers.CharField(write_only=True, required=False, allow_null=True)

    class Meta:
        model = Task
        fields = [
            "id",
            "title",
            "description",
            "status",
            "category",
            "due_date",
            "created_at",
            "updated_at",
            "ai_summary",
        ]

    def create(self, validated_data):
        """Get title and description"""
        title = validated_data.get("title", "")
        description = validated_data.get("description", "")

        """ Get AI suggestion """
        suggestion = auto_categorize_task(title, description)

        category_name = None

        """ Safely extract category from AI response """
        if suggestion:
            try:
                """Expected format: (Category: Work, Priority: High)"""
                parts = suggestion.split(",")
                for part in parts:
                    if "Category:" in part:
                        category_name = part.split("Category:")[1].strip()
                        break
            except Exception:
                category_name = None

        """ If AI gave a category, use it """
        if category_name:
            category, created = Category.objects.get_or_create(
                name=category_name,
                defaults={"slug": category_name.lower().replace(" ", "-")},
            )
            validated_data["category"] = category

        """ Create the task """
        task = super().create(validated_data)

        """ Generate AI summary (keep your existing logic) """
        try:
            task.ai_summary = generate_task_summary(task)
            task.save(update_fields=["ai_summary"])

        except Exception as e:
            print(f"AI Summary failed: {e}")

        add_task_to_vectorstore(task)
        return task

    def update(self, instance, validated_data):
        """Handle category update + regenerate AI summary after task is updated."""
        category_name = validated_data.pop("category", None)

        if category_name:
            category, created = Category.objects.get_or_create(
                name=category_name,
                defaults={"slug": category_name.lower().replace(" ", "-")},
            )
            validated_data["category"] = category

        """ Update the task """
        task = super().update(instance, validated_data)

        """ Regenerate summary after update """
        try:
            task.ai_summary = generate_task_summary(task)
            task.save(update_fields=["ai_summary"])

        except Exception as e:
            print(f"AI Summary failed for task {task.id}: {e}")

        # task.ai_summary = generate_task_summary(task)
        # task.save(update_fields=['ai_summary'])
        add_task_to_vectorstore(task)
        return task

    def to_representation(self, instance):
        """Show category name instead of ID in response."""
        representation = super().to_representation(instance)
        if instance.category:
            representation["category"] = instance.category.name
        else:
            representation["category"] = None
        return representation


# ------ AUTH SERIALIZERS ------
class AuthSerializer(serializers.ModelSerializer):

    password = serializers.CharField(
        write_only=True, required=True, style={"input_type": "password"}
    )

    password2 = serializers.CharField(
        write_only=True, required=True, style={"input_type": "password"}
    )

    class Meta:
        model = User
        fields = ["username", "email", "password", "password2"]

    def validate(self, attrs):
        """To Ensure password matches password2"""
        if attrs["password"] != attrs["password2"]:
            raise serializers.ValidationError({"password": "Password does not match. "})

        return attrs

    def create(self, validated_data):
        """User creatio and password hashing"""
        validated_data.pop("password2")

        password = validated_data.pop("password")

        user = User.objects.create_user(password=password, **validated_data)
        return user
