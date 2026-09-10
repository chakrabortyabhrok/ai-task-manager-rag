from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import Task
from .ai_utils import add_task_to_vectorstore, delete_task_from_vectorstore


@receiver(post_save, sender=Task)
def embed_task_after_save(sender, instance, **kwargs):
    try:
        add_task_to_vectorstore(instance)
    except Exception as e:
        print(f"Vector store embedding failed for task {instance.id}: {e}")


@receiver(post_delete, sender=Task)
def remove_task_after_delete(sender, instance, **kwargs):
    try:
        delete_task_from_vectorstore(instance.id)
    except Exception as e:
        print(f"Vector store deletion failed for task {instance.id}: {e}")
