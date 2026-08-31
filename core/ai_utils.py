import os
from dotenv import load_dotenv
from openai import OpenAI
from langchain_openai import OpenAIEmbeddings
from langchain_core.documents import Document
from langchain_postgres import PGVector
from urllib import parse

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

    page_content = (
        f"Task Title: {task.title}. "
        f"Description: {task.description or 'No description provided'}. "
        f"Current Status: {task.status}. "
        f"Category: {task.category.name if task.category else 'No category'}."
    )

    metadata = {
        "task_id": task.id,
        "title": task.title,
        "status": task.status,
        "category": task.category.name if task.category else "None"
    }

    document = Document(page_content=page_content, metadata=metadata)
    vectorstore.add_documents([document], ids=[str(task.id)])

def ask_ai_about_tasks(question: str) -> str:
    try:
        vectorstore = get_vectorstore()

        if vectorstore is None:
            return "AI search is only available in production (PostgreSQL + pgvector)."

        retriever = vectorstore.as_retriever(search_kwargs={"k": 15})
        relevant_docs = retriever.invoke(question)

        if not relevant_docs:
            return "I couldn't find any relevant tasks for your question."

        context = "\n\n".join([doc.page_content for doc in relevant_docs])

        prompt = f"""
        You are a helpful assistant that answers questions about the user's tasks.

        Important Rules:
        - You are given only a partial list of the user's tasks (not all of them).
        - Base your answer only on the tasks provided below.
        - If the user asks for a count and you don't have all tasks, say so clearly.
        - If no question given, say so politely.
        - Do not make up information.

        Relevant tasks:
        {context}

        User's Question: {question}

        Answer clearly and concisely.
        """
        return get_ai_response(prompt)

    except Exception as e:
        print("Error in ask_ai_about_tasks:", e)
        return f"Sorry, something went wrong. Error: {str(e)}"

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
    # 1. Delete the old collection from Postgres using a temporary reference
    temp_store = get_vectorstore()
    try:
        temp_store.delete_collection()
    except Exception as e:
        print(f"Collection reset warning: {e}")

    # 2. Get a FRESH vectorstore instance (re-creates the collection in Postgres with a new valid ID)
    vectorstore = get_vectorstore()

    if not tasks:
        print("No tasks to sync.")
        return

    documents = []
    ids = []

    for task in tasks:
        page_content = (
            f"Task Title: {task.title}. "
            f"Description: {task.description or 'No description provided'}. "
            f"Current Status: {task.status}. "
            f"Category: {task.category.name if task.category else 'No category'}."
        )
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

          
# def sync_all_tasks_to_vectorstore(tasks):
#     """
#     Wipes stale vectors and re-embeds only active DB tasks.
#     """
#     vectorstore = get_vectorstore()
#     try:
#         vectorstore.delete_collection()
#     except Exception as e:
#         print(f"collection reset warning: {e}")
        
#     for task in tasks:
#         add_task_to_vectorstore(task)
        

"""
def clear_vectorstore():
    
    "Completely clears all documents from the pgvector collection.To be used only if needed ."
    
    vectorstore = get_vectorstore()

    if vectorstore is None:
        print("Vector store is not available (running on SQLite).")
        return False

    try:
        # This deletes the entire collection and recreates it empty
        vectorstore.delete_collection()
        print("Successfully cleared the vector store.")
        return True
    except Exception as e:
        print(f"Error while clearing vector store: {e}")
        return False
"""