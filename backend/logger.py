from backend.supabase_client import supabase

def log_qa(user_id, document_name, question, answer, sources=None):
    supabase.table("qa_logs").insert({
        "user_id": user_id,
        "document_name": document_name,
        "question": question,
        "answer": answer,
        "sources": sources or []
    }).execute()
    print("QA logged for user:", user_id)

