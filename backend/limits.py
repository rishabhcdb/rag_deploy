# from flask import request, jsonify
# import time


# # in-memory (v1 only)
# USER_LIMITS = {}
# MAX_UPLOADS = 5
# MAX_QUESTIONS = 5


# def check_limits(user_id, action):
#     now = time.time()
#     record = USER_LIMITS.get(user_id, {"uploads": 0, "questions": 0})

#     if action == "upload":
#         if record["uploads"] >= MAX_UPLOADS:
#             raise Exception("Upload limit exceeded")
#         record["uploads"] += 1

#     if action == "ask":
#         if record["questions"] >= MAX_QUESTIONS:
#             raise Exception("Question limit exceeded")
#         record["questions"] += 1

#     USER_LIMITS[user_id] = record

# def get_questions_used(user_id):
#     record = USER_LIMITS.get(user_id, {"questions": 0})
#     return record.get("questions", 0)


# def get_questions_limit():
#     return MAX_QUESTIONS


from backend.supabase_client import supabase
from datetime import date

MAX_QUESTIONS = 5
MAX_UPLOADS = 3


def ensure_user_row(user_id):
    res = supabase.table("usage_limits") \
        .select("*") \
        .eq("user_id", user_id) \
        .execute()

    if not res.data:
        supabase.table("usage_limits").insert({
            "user_id": user_id,
            "questions_used": 0,
            "uploads_used": 0,
            "last_reset": date.today().isoformat()
        }).execute()


def reset_if_new_day(row, user_id):
    today = date.today().isoformat()

    if row["last_reset"] != today:
        supabase.table("usage_limits").update({
            "questions_used": 0,
            "uploads_used": 0,
            "last_reset": today
        }).eq("user_id", user_id).execute()

        row["questions_used"] = 0
        row["uploads_used"] = 0
        row["last_reset"] = today

    return row


def check_limits(user_id, action):
    ensure_user_row(user_id)

    row = supabase.table("usage_limits") \
        .select("*") \
        .eq("user_id", user_id) \
        .single() \
        .execute() \
        .data

    row = reset_if_new_day(row, user_id)

    if action == "ask":
        if row["questions_used"] >= MAX_QUESTIONS:
            return False

        supabase.table("usage_limits").update({
            "questions_used": row["questions_used"] + 1
        }).eq("user_id", user_id).execute()

    if action == "upload":
        if row["uploads_used"] >= MAX_UPLOADS:
            return False

        supabase.table("usage_limits").update({
            "uploads_used": row["uploads_used"] + 1
        }).eq("user_id", user_id).execute()

    return True


def get_user_limits(user_id):
    ensure_user_row(user_id)

    row = supabase.table("usage_limits") \
        .select("*") \
        .eq("user_id", user_id) \
        .single() \
        .execute() \
        .data

    row = reset_if_new_day(row, user_id)

    return {
        "questions_used": row["questions_used"],
        "questions_limit": MAX_QUESTIONS
    }

