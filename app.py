"""
app.py  —  AIPE Flask Web Application
"""

import os
import json
import uuid
from flask import (Flask, render_template, request, jsonify,
                   send_file, redirect, url_for)
from dotenv import load_dotenv
from werkzeug.utils import secure_filename

from ocr_pipeline import OCRPipeline
from evaluator import Evaluator
from report_generator import generate_report

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-secret-key")

UPLOAD_FOLDER = "uploads"
OUTPUT_FOLDER = "output"
ALLOWED_EXTENSIONS = {"pdf", "jpg", "jpeg", "png"}
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

API_KEY = os.getenv("GEMINI_API_KEY")


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/upload-answer-key", methods=["POST"])
def upload_answer_key():
    if "answer_key" not in request.files:
        return jsonify({"error": "No file provided"}), 400
    file = request.files["answer_key"]
    try:
        content = file.read().decode("utf-8")
        key_data = json.loads(content)
        save_path = os.path.join(UPLOAD_FOLDER, "answer_key.json")
        with open(save_path, "w", encoding="utf-8") as f:
            json.dump(key_data, f, indent=4)
        return jsonify({"success": True, "message": "Answer key uploaded successfully",
                        "subject": key_data.get("subject", "N/A")})
    except json.JSONDecodeError as e:
        return jsonify({"error": f"Invalid JSON: {str(e)}"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/evaluate", methods=["POST"])
def evaluate():
    if "answer_sheet" not in request.files:
        return jsonify({"error": "No answer sheet uploaded"}), 400
    file = request.files["answer_sheet"]
    if not file or not allowed_file(file.filename):
        return jsonify({"error": "Invalid file type. Upload PDF or image."}), 400

    answer_key_path = os.path.join(UPLOAD_FOLDER, "answer_key.json")
    if not os.path.exists(answer_key_path):
        return jsonify({"error": "Please upload the answer key first."}), 400

    session_id = str(uuid.uuid4())[:8]
    session_dir = os.path.join(OUTPUT_FOLDER, session_id)
    os.makedirs(session_dir, exist_ok=True)

    filename = secure_filename(file.filename)
    file_path = os.path.join(session_dir, filename)
    file.save(file_path)

    try:
        ocr = OCRPipeline(api_key=API_KEY, output_base=OUTPUT_FOLDER)
        if filename.lower().endswith(".pdf"):
            ocr_result = ocr.run(file_path, session_id)
        else:
            text = ocr.extract_text_from_image(file_path)
            ocr_result = {"session_id": session_id, "full_text": text,
                          "pages": [{"page": filename, "text": text}]}
            with open(os.path.join(session_dir, "ocr_result.json"), "w") as f:
                json.dump(ocr_result, f, indent=4)

        evaluator = Evaluator(api_key=API_KEY)
        evaluation = evaluator.evaluate(ocr_result, answer_key_path, session_id, OUTPUT_FOLDER)

        return jsonify({"success": True, "session_id": session_id,
                        "redirect": f"/results/{session_id}"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/results/<session_id>")
def results(session_id):
    eval_path = os.path.join(OUTPUT_FOLDER, session_id, "evaluation.json")
    if not os.path.exists(eval_path):
        return "Session not found", 404
    with open(eval_path, "r", encoding="utf-8") as f:
        evaluation = json.load(f)
    return render_template("results.html", evaluation=evaluation, session_id=session_id)


@app.route("/override", methods=["POST"])
def override():
    data = request.get_json()
    session_id = data.get("session_id")
    overrides = data.get("overrides", {})

    eval_path = os.path.join(OUTPUT_FOLDER, session_id, "evaluation.json")
    if not os.path.exists(eval_path):
        return jsonify({"error": "Session not found"}), 404

    with open(eval_path, "r", encoding="utf-8") as f:
        evaluation = json.load(f)

    for section in ["part_a", "part_b"]:
        for item in evaluation[section]:
            q = item.get("question", "")
            if q in overrides:
                try:
                    new_mark = int(overrides[q])
                    max_mark = item["max_marks"]
                    item["teacher_override"] = max(0, min(new_mark, max_mark))
                    item["marks_awarded"] = item["teacher_override"]
                except ValueError:
                    pass

    evaluator = Evaluator(api_key=API_KEY)
    evaluation["totals"] = evaluator.calculate_totals(evaluation["part_a"], evaluation["part_b"])

    with open(eval_path, "w", encoding="utf-8") as f:
        json.dump(evaluation, f, indent=4, ensure_ascii=False)

    return jsonify({"success": True, "totals": evaluation["totals"]})


@app.route("/report/<session_id>")
def download_report(session_id):
    eval_path = os.path.join(OUTPUT_FOLDER, session_id, "evaluation.json")
    if not os.path.exists(eval_path):
        return "Session not found", 404
    with open(eval_path, "r", encoding="utf-8") as f:
        evaluation = json.load(f)
    report_path = os.path.join(OUTPUT_FOLDER, session_id, "report.pdf")
    generate_report(evaluation, report_path)
    return send_file(report_path, as_attachment=True,
                     download_name=f"evaluation_{session_id}.pdf")


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))