import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "taskmanager_api.settings")
django.setup()

from django.contrib.auth import get_user_model
from core.ai_utils import ask_ai_about_tasks, handle_aggregate, classify_intent

User = get_user_model()

def run_tests():
    # - Grab an active user from the database
    user = User.objects.first()
    if not user:
        print("ERROR: No user found in the database. Create a user first.")
        return

    print(f"Testing AI logic for user: '{user.username}' (ID: {user.id})")
    print("=" * 60)

    # 1- Direct tests for handle_aggregate SQL queries
    print("1. DIRECT AGGREGATE TESTS (SQL Queries)")
    print("=" * 60)
    
    aggregate_queries = [
        "How many total tasks do I have?",
        "How many tasks are in progress?",
        "How many completed tasks do I have?",
        "How many pending tasks exist?",
        "How many tasks are in Work category?", 
    ]

    for q in aggregate_queries:
        response = handle_aggregate(q, user)
        print(f"Query:    '{q}'")
        print(f"Response:  {response}\n")

    # 2- End-to-end tests through ask_ai_about_tasks
    print("=" * 60)
    print("2. END-TO-END RAG & ROUTING TESTS")
    print("=" * 60)

    e2e_queries = [
        ("Aggregate Route", "Count of tasks in progress"),
        ("Semantic Search Route", "What do I need to fix around the home?"),
        ("Out-of-Domain Route", "Are there any tasks related to quantum physics?"),
    ]

    for label, query in e2e_queries:
        print(f"\n--- [{label}] ---")
        print(f"User Query: {query}")
        intent = classify_intent(query)
        print(f"Intent:     {intent}")
        response = ask_ai_about_tasks(query, user)
        print(f"AI Output:  {response}")

if __name__ == "__main__":
    run_tests()