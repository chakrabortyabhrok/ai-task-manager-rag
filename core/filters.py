import django_filters
from .models import Task


class TaskFilter(django_filters.FilterSet):
    """Custom filter for Task model supporting status and category name filtering."""

    category = django_filters.CharFilter(
        field_name="category__name", lookup_expr="icontains"
    )

    class Meta:
        model = Task
        fields = ["status", "category"]
