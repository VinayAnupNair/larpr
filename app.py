#!/usr/bin/env python3
import json
import os
import re
from pathlib import Path

import anthropic
from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request, send_file

from src import track_cost
from src.export import export_pdf
from src.tailor import tailor_resume

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
OUTPUT_DIR = ROOT / "output"
BASE_RESUME_PATH = DATA_DIR / "base_resume.json"

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 2 * 1024 * 1024


def slugify(value):
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")


def infer_application_details(job_description):
    def find_value(labels, fallback):
        pattern = rf"^\s*(?:{'|'.join(labels)})\s*:\s*(.+?)\s*$"
        match = re.search(pattern, job_description, re.IGNORECASE | re.MULTILINE)
        return match.group(1).strip() if match else fallback

    company = find_value(("company", "employer", "organization"), "Company")
    role = find_value(("role", "position", "title", "job title"), "Position")
    return company, role


def get_client():
    load_dotenv(ROOT / ".env")
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY is not configured. Add it to .env first.")
    return anthropic.Anthropic(api_key=api_key), os.getenv("ANTHROPIC_MODEL", "claude-sonnet-5-5")


@app.get("/")
def index():
    return render_template("index.html")


REQUIRED_KEYS = ("header", "education", "skills", "experience", "projects")


def validate_resume(data):
    if not isinstance(data, dict):
        raise ValueError("Resume must be a JSON object.")
    missing = [k for k in REQUIRED_KEYS if k not in data]
    if missing:
        raise ValueError(f"Missing required section(s): {', '.join(missing)}")
    if not isinstance(data["header"], dict) or not data["header"].get("name"):
        raise ValueError("header.name is required.")
    for skill in data["skills"]:
        if not isinstance(skill.get("category"), str) or not isinstance(skill.get("items"), list):
            raise ValueError("Each skill needs a category (string) and items (list).")
    for entry in data["experience"]:
        for key in ("company", "role", "date", "bullets"):
            if key not in entry:
                raise ValueError(f"Each experience entry needs '{key}'.")


@app.get("/profile")
def profile():
    return render_template("profile.html")


@app.get("/api/profile")
def get_profile():
    return jsonify(json.loads(BASE_RESUME_PATH.read_text()))


@app.put("/api/profile")
def save_profile():
    data = request.get_json(silent=True)
    try:
        validate_resume(data)
        for project in data["projects"]:
            if not project.get("name") or not isinstance(project.get("bullets"), list):
                raise ValueError("Each project needs a name and bullets.")
        for entry in data["education"]:
            if not entry.get("institution") or not entry.get("date"):
                raise ValueError("Each education entry needs an institution and date.")
    except ValueError as exc:
        return jsonify(error=str(exc)), 400
    backup = BASE_RESUME_PATH.with_suffix(".json.bak")
    backup.write_text(BASE_RESUME_PATH.read_text())
    BASE_RESUME_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    return jsonify(ok=True)


@app.post("/tailor")
def tailor():
    job_description = request.form.get("job_description", "").strip()
    if not job_description:
        return jsonify(error="Paste a job description before generating your resume."), 400

    try:
        company, role = infer_application_details(job_description)
        client, model = get_client()
        base_resume = json.loads(BASE_RESUME_PATH.read_text())
        infer_skills = bool(request.form.get("infer_skills"))
        with track_cost() as total_cost:
            tailored = tailor_resume(base_resume, job_description, company, role, client, model, infer_skills)
        return jsonify(resume=tailored, company=company, role=role, cost=round(total_cost(), 4))
    except Exception as exc:
        app.logger.exception("Tailoring failed")
        return jsonify(error=f"Could not tailor the resume: {exc}"), 500


@app.post("/render")
def render():
    payload = request.get_json(silent=True) or {}
    try:
        resume = payload.get("resume")
        validate_resume(resume)
        client, model = get_client()
        with track_cost() as total_cost:
            pdf_path = export_pdf(
                resume, payload.get("company") or "Company", payload.get("role") or "Position",
                client, model, str(OUTPUT_DIR),
            )
        response = send_file(pdf_path, as_attachment=True)
        response.headers["X-Cost-USD"] = f"{total_cost():.4f}"
        response.headers["Access-Control-Expose-Headers"] = "X-Cost-USD, Content-Disposition"
        return response
    except ValueError as exc:
        return jsonify(error=str(exc)), 400
    except Exception as exc:
        app.logger.exception("Render failed")
        return jsonify(error=f"Could not render the PDF: {exc}"), 500


if __name__ == "__main__":
    app.run(debug=True, port=int(os.getenv("PORT", "5000")))
