print(">>> APP.PY LOADED <<<")

from flask import Flask, request, jsonify, send_from_directory
from backend.rag import ChatPDF
from backend.auth import require_auth
from backend.limits import check_limits
import os
import tempfile

from backend.limits import check_limits, get_user_limits
from backend.logger import log_qa
import nltk
import os

import nltk
import os

NLTK_DATA_PATH = "/opt/render/nltk_data"
os.makedirs(NLTK_DATA_PATH, exist_ok=True)
nltk.data.path.append(NLTK_DATA_PATH)

required_packages = [
    "punkt",
    "punkt_tab",
    "averaged_perceptron_tagger",
    "averaged_perceptron_tagger_eng"
]

for pkg in required_packages:
    try:
        nltk.data.find(pkg)
    except LookupError:
        nltk.download(pkg, download_dir=NLTK_DATA_PATH)


# ⬇️ IMPORTANT CHANGE HERE
app = Flask(__name__, static_folder="frontend", static_url_path=None)

chatpdf = ChatPDF()

# =========================
# API ROUTES (FIRST)
# =========================


# @app.route("/api/upload", methods=["POST"])
# @require_auth
# def upload(user):
#     check_limits(user["id"], "upload")

#     if "file" not in request.files:
#         return jsonify({"error": "No file uploaded"}), 400

#     file = request.files["file"]

#     with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
#         file.save(tmp.name)
#         tmp_path = tmp.name

#     chatpdf.ingest(tmp_path)

#     return jsonify({"status": "PDF processed"})

@app.route("/api/upload", methods=["POST"])
@require_auth
def upload(user):
    # 🔒 limit check FIRST
    allowed = check_limits(user["id"], "upload")
    if not allowed:
        return jsonify({"error": "Upload limit reached"}), 429

    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files["file"]

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        file.save(tmp.name)
        tmp_path = tmp.name

    chatpdf.ingest(tmp_path)

    return jsonify({"status": "PDF processed"})


# @app.route("/api/ask", methods=["POST"])
# @require_auth
# def ask(user):
#     try:
#         check_limits(user["id"], "ask")
#     except Exception as e:
#         return jsonify({"error": str(e)}), 429

#     data = request.json or {}
#     question = data.get("question")

#     if not question:
#         return jsonify({"error": "Question missing"}), 400

#     answer = chatpdf.ask(question)
#     return jsonify({"answer": answer})

@app.route("/api/ask", methods=["POST"])
@require_auth
def ask(user):
    # 🔒 limit check FIRST
    allowed = check_limits(user["id"], "ask")
    if not allowed:
        return jsonify({"error": "Question limit reached"}), 429

    data = request.json or {}
    question = data.get("question")

    if not question:
        return jsonify({"error": "Question missing"}), 400

    # 🧠 generate answer
    answer = chatpdf.ask(question)

    # 🧾 log question + answer
    log_qa(
        user_id=user["id"],
        document_name="current_document.pdf",  # replace later
        question=question,
        answer=answer,
        sources=[]  # will add citations later
    )

    return jsonify({"answer": answer})



@app.route("/api/reset", methods=["POST"])
@require_auth
def reset(user):
    chatpdf.clear()
    return jsonify({"status": "Session cleared"})


# @app.route("/api/limits", methods=["GET"])
# @require_auth
# def get_limits(user):
#     return jsonify({
#         "questions_used": get_questions_used(user["id"]),
#         "questions_limit": get_questions_limit()
#     })

from backend.limits import get_user_limits

@app.route("/api/limits", methods=["GET"])
@require_auth
def get_limits(user):
    return jsonify(get_user_limits(user["id"]))



# =========================
# SPA FALLBACK (LAST)
# =========================

@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def spa(path):
    file_path = os.path.join(app.static_folder, path)

    # Serve actual files (js, css, etc.)
    if path and os.path.exists(file_path):
        return send_from_directory(app.static_folder, path)

    # Serve index.html for ALL frontend routes
    return send_from_directory(app.static_folder, "index.html")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
