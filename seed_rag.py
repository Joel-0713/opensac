import os
import json
import hashlib
from dotenv import load_dotenv
import psycopg
from psycopg_pool import ConnectionPool
from langchain_google_genai import GoogleGenerativeAIEmbeddings

load_dotenv()

# Sample Runbooks
RUNBOOKS = [
    {
        "content": "Auth service 504 timeouts are usually caused by stale Redis connections. To remediate, restart the auth pods and flush the Redis connection pool.",
        "metadata": {"service": "auth"}
    },
    {
        "content": "Database high latency might occur during backup windows. If latency exceeds 500ms outside windows, check active queries and kill idle transactions.",
        "metadata": {"service": "database"}
    },
    {
        "content": "Payment gateway failures with upstream timeouts indicate external provider issues. Switch routing to the secondary provider in the config.",
        "metadata": {"service": "payments"}
    }
]

def seed_database():
    db_url = os.environ["DATABASE_URL"]
    
    embeddings = GoogleGenerativeAIEmbeddings(
        model="models/text-embedding-004",
        task_type="RETRIEVAL_DOCUMENT",
    )

    with ConnectionPool(db_url, min_size=1, max_size=2) as pool:
        with pool.connection() as conn:
            for rb in RUNBOOKS:
                content = rb["content"]
                metadata = rb["metadata"]
                
                # We'll use md5 constraint in DB for idempotency, or we can just do ON CONFLICT DO NOTHING
                vector = embeddings.embed_query(content)
                
                conn.execute(
                    """
                    INSERT INTO incident_docs (content, metadata, embedding)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (md5(content)) DO NOTHING;
                    """,
                    (content, json.dumps(metadata), str(vector))
                )
            conn.commit()

if __name__ == "__main__":
    seed_database()
    print("Database seeded.")
