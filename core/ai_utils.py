import os
from dotenv import load_dotenv
from openai import OpenAI
from langchain_openai import OpenAIEmbeddings
from langchain_core.documents import Document
from langchain_postgres import PGVector
from urllib import parse
from .models import Category, Task

load_dotenv()

def get_ai_response(prompt: str, model: str = "gpt-4o-mini") -> str:
    try:
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=300,
            temperature=0.5
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Error: {str(e)}"

def generate_task_summary(task):
    prompt = f"""
    Summarize this task in 1-2 very short sentences:
    Title: {task.title}
    Description: {task.description or 'No description'}
    Status: {task.status}
    """
    try:
        return get_ai_response(prompt)
    except Exception as e:
        print(f"Error generating summary: {str(e)}")
        return ""

def auto_categorize_task(title, description):
    prompt = f"""
    According to the title and description provided, recommend category for the user:  
    Title: {title}
    Description: {description}

    Rules:
    - return in a fixed format (example: Category: Work)
    - no extra sentenses or words. just in the fixed format
    """
    try:
        return get_ai_response(prompt)
    except Exception as e:
        print(f"Error generating category: {str(e)}")
        return ""

def get_vectorstore():
    """
    Always use PGVector (PostgreSQL) for both local and production.
    """

    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

    connection_string = os.environ.get("DATABASE_URL")

    if not connection_string:
        """ Build local connection string from environment variables"""

        db_name = os.environ.get("DB_NAME", "taskmanager_db")
        db_user = os.environ.get("DB_USER", "newuser123")
        db_password = parse.quote_plus(os.environ.get("DB_PASSWORD", ""))
        db_host = os.environ.get("DB_HOST", "db")
        db_port = os.environ.get("DB_PORT", "5432")

        connection_string = f"postgresql+psycopg://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"

    return PGVector(
        embeddings=embeddings,
        collection_name="task_embeddings",
        connection=connection_string,
        use_jsonb=True,
    )

def add_task_to_vectorstore(task):
    """
    Adds a task to the PGVector store (PostgreSQL).
    """
    print(f">>> Embedding task ID: {task.id} | Title: {task.title}")

    vectorstore = get_vectorstore()

    page_content = f"{task.title}. {task.description or ''}"

    metadata = {
        "task_id": task.id,
        "title": task.title,
        "status": task.status,
        "category": task.category.name if task.category else "None"
    }

    document = Document(page_content=page_content, metadata=metadata)
    vectorstore.add_documents([document], ids=[str(task.id)])


def classify_intent(question: str) -> str:
    prompt = f"""Analyze the user query and decide if it asks for counting/aggregation or searching/listing specific content.
    
    Query: "{question}"

    Respond with EXACTLY one word:
    - "aggregate": if the query asks "how many", "total number", "count", or requests exact counts/totals.
    - "find": if the query asks for specific tasks, content search, descriptions, or general task details.

    Intent:"""


    response = get_ai_response(prompt).strip().lower()
    
    if "aggregate" in response:
        return "aggregate"
    return "find"

def handle_aggregate(question: str, user=None) -> str:
    q = question.lower()

    tasks = Task.objects.all()

    if "pending" in q or "todo" in q or "not started" in q:
        tasks = tasks.filter(status="todo")   # your default is 'todo', not 'pending'
        label = "pending"
    elif "progress" in q or "in_progress" in q or "ongoing" in q:
        tasks = tasks.filter(status="in_progress")
        label = "in progress"
    elif "complete" in q or "done" in q or "finished" in q:
        tasks = tasks.filter(status="done")   # change to 'completed' if that is your choice
        label = "completed"
    else:
        label = "total"

    for cat in Category.objects.all():
        if cat.name and cat.name.lower() in q:
            tasks = tasks.filter(category=cat)
            label = f"{label} in {cat.name}"
            break

    count = tasks.count()
    return f"You have {count} {label} task{'s' if count != 1 else ''}."

def ask_ai_about_tasks(question: str, user) -> str:
    intent = classify_intent(question)
    vectorstore = get_vectorstore()
    THRESHOLD = 0.73

    if intent == "aggregate":
        return handle_aggregate(question, user)

    results = vectorstore.similarity_search_with_score(question, k=10)
    relevant = [(d, s) for d, s in results if s <= THRESHOLD]

    if not relevant:
        return "I couldn't find any tasks related to that in your data."

    # Formating context clearly with title and category metadatas
    context = "\n\n".join(
        f"- Title: {d.metadata.get('title')}\n  Category: {d.metadata.get('category')}\n  Content: {d.page_content}"
        for d, _ in relevant
    )

    prompt = f"""Answer the user's question based on their tasks listed below.
    Use reasonable common-sense connections (for example, fixing a faucet or leak counts as home repair).
    If none of the tasks relate to the question at all, state that you could not find relevant tasks.
    
    User Tasks:
    {context}

    Question: {question}"""

    return get_ai_response(prompt)

def delete_task_from_vectorstore(task_id):
    """
    Removes a deleted task vector from PGVector
    """
    try:
        vectorstore =get_vectorstore()
        vectorstore.delete(ids=[str(task_id)])
    except Exception as e:
        print(f"Error deleting {task_id} vector: {e}")


def sync_all_tasks_to_vectorstore(tasks):
    """
    Wipes old vector data and batch-embeds active tasks cleanly.
    """
    # 1- Deletes the old collection from Postgres using a temporary reference
    temporary_store = get_vectorstore()
    try:
        temporary_store.delete_collection()
    except Exception as e:
        print(f"Collection reset warning: {e}")

    # 2- Gets a FRESH vectorstore instance (re-creates the collection in Postgres with a new valid ID)
    vectorstore = get_vectorstore()

    if not tasks:
        print("No tasks to sync.")
        return

    documents = []
    ids = []

    for task in tasks:

        page_content = f"{task.title}. {task.description or ''}"

        metadata = {
            "task_id": str(task.id),
            "title": task.title,
            "status": task.status,
            "category": task.category.name if task.category else "None"
        }

        documents.append(Document(page_content=page_content, metadata=metadata))
        ids.append(str(task.id))

    print(f">>> Batch embedding {len(documents)} tasks...")
    vectorstore.add_documents(documents, ids=ids)
    print(f">>> Successfully synced {len(documents)} tasks to vectorstore!")


# def clear_vectorstore():
    
#     "Completely clears all documents from the pgvector collection.To be used only if needed ."
    
#     vectorstore = get_vectorstore()

#     if vectorstore is None:
#         print("Vector store is not available (running on SQLite).")
#         return False

#     try:
#         # This deletes the entire collection and recreates it empty
#         vectorstore.delete_collection()
#         print("Successfully cleared the vector store.")
#         return True
#     except Exception as e:
#         print(f"Error while clearing vector store: {e}")
#         return False
