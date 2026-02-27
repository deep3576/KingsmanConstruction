from flask import jsonify, request
from sqlalchemy import text
from werkzeug.security import check_password_hash, generate_password_hash

from db import engine
from . import api_bp

API_PREFIX = "/api/kingsman/v1"


@api_bp.get("/health")
def health_check():
    return jsonify(service="construction-backend", status="ok", api_prefix=API_PREFIX)


@api_bp.get("/services")
def services():
    payload = [
        {
            "key": "adus-additions",
            "title": "Additions & ADUs",
            "description": "From concept to permit to build — we expand spaces that feel like home.",
        },
        {
            "key": "permits",
            "title": "Permits & Drawings",
            "description": "Ontario-compliant drawings and permit support to keep projects moving.",
        },
        {
            "key": "interiors",
            "title": "Kitchens • Baths • Basements",
            "description": "Transformative interior work with durable materials and clean finishes.",
        },
    ]
    return jsonify(items=payload)


@api_bp.get("/jobs")
def list_jobs():
    limit = min(max(request.args.get("limit", default=20, type=int), 1), 100)
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                """
                SELECT id, job_number, title, client_name, client_email, client_phone, status, start_date, updated_at
                FROM jobs
                ORDER BY updated_at DESC
                LIMIT :limit
                """
            ),
            {"limit": limit},
        ).mappings().all()
    return jsonify(items=[dict(r) for r in rows])


@api_bp.get("/jobs/<int:job_id>")
def get_job(job_id: int):
    with engine.connect() as conn:
        job = conn.execute(
            text(
                """
                SELECT id, job_number, title, client_name, client_email, client_phone, status, start_date, created_at, updated_at
                FROM jobs
                WHERE id = :job_id
                LIMIT 1
                """
            ),
            {"job_id": job_id},
        ).mappings().first()
        if not job:
            return jsonify(error="Job not found."), 404

        steps = conn.execute(
            text(
                """
                SELECT id, step_key, step_name, target_date, completed, created_at, updated_at
                FROM job_steps
                WHERE job_id = :job_id
                ORDER BY id
                """
            ),
            {"job_id": job_id},
        ).mappings().all()

    payload = dict(job)
    payload["steps"] = [dict(s) for s in steps]
    return jsonify(item=payload)


@api_bp.post("/contact")
def create_contact_message():
    data = request.get_json(silent=True) or {}

    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip().lower()
    phone = (data.get("phone") or "").strip()
    subject = (data.get("subject") or "General Inquiry").strip()
    message = (data.get("message") or "").strip()

    errors = []
    if not name:
        errors.append("Name is required.")
    if not email:
        errors.append("Email is required.")
    if not message:
        errors.append("Message is required.")

    if errors:
        return jsonify(ok=False, errors=errors), 400

    with engine.begin() as conn:
        res = conn.execute(
            text(
                """
                INSERT INTO contact_messages (name, email, phone, subject, message, created_at)
                VALUES (:name, :email, :phone, :subject, :message, NOW())
                """
            ),
            {
                "name": name,
                "email": email,
                "phone": phone or None,
                "subject": subject or None,
                "message": message,
            },
        )

    return jsonify(ok=True, id=res.lastrowid, message="Thanks! We'll get back to you shortly."), 201


@api_bp.post("/auth/signup")
def signup():
    data = request.get_json(silent=True) or {}

    first_name = (data.get("first_name") or "").strip()
    last_name = (data.get("last_name") or "").strip()
    full_name = f"{first_name} {last_name}".strip()
    email = (data.get("email") or "").strip().lower()
    phone = (data.get("phone") or "").strip()
    password = (data.get("password") or "").strip()

    errors = []
    if not first_name or not last_name:
        errors.append("First and last name are required.")
    if not email:
        errors.append("Email is required.")
    if len(password) < 8:
        errors.append("Password must be at least 8 characters.")
    if errors:
        return jsonify(ok=False, errors=errors), 400

    with engine.connect() as conn:
        exists = conn.execute(text("SELECT 1 FROM users WHERE email = :email"), {"email": email}).first()
        if exists:
            return jsonify(ok=False, errors=["An account with this email already exists."]), 409

    with engine.begin() as conn:
        res = conn.execute(
            text(
                """
                INSERT INTO users (email, password_hash, role, full_name)
                VALUES (:email, :password_hash, 'consumer', :full_name)
                """
            ),
            {"email": email, "password_hash": generate_password_hash(password), "full_name": full_name},
        )
        user_id = res.lastrowid
        conn.execute(
            text(
                """
                INSERT INTO consumer_profiles (user_id, full_name, phone)
                VALUES (:user_id, :full_name, :phone)
                """
            ),
            {"user_id": user_id, "full_name": full_name, "phone": phone or None},
        )

    return jsonify(ok=True, user_id=user_id, email=email, full_name=full_name), 201


@api_bp.post("/auth/login")
def login():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = (data.get("password") or "").strip()

    with engine.connect() as conn:
        user = conn.execute(
            text(
                """
                SELECT u.id, u.email, u.role, u.password_hash, COALESCE(u.full_name, cp.full_name) AS full_name
                FROM users u
                LEFT JOIN consumer_profiles cp ON cp.user_id = u.id
                WHERE u.email = :email
                LIMIT 1
                """
            ),
            {"email": email},
        ).mappings().first()

    if not user or not check_password_hash(user["password_hash"], password):
        return jsonify(ok=False, error="Invalid email or password."), 401

    return jsonify(
        ok=True,
        user={
            "id": user["id"],
            "email": user["email"],
            "role": user["role"],
            "full_name": user["full_name"],
        },
    )


@api_bp.route("/<path:_>", methods=["OPTIONS"])
def options_handler(_):
    return ("", 204)
