from dataclasses import dataclass
from flask import Flask, render_template, request, jsonify, redirect, url_for, abort
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash, generate_password_hash
from sqlalchemy import text

from config import Config
from db import engine, ensure_schema


# --- Minimal user session object for Flask-Login (no ORM) ---
@dataclass
class UserSession:
    id: int
    email: str
    role: str | None = None

    # Flask-Login requirements
    @property
    def is_authenticated(self) -> bool: return True
    @property
    def is_active(self) -> bool: return True
    @property
    def is_anonymous(self) -> bool: return False
    def get_id(self) -> str: return str(self.id)

    @property
    def is_admin(self) -> bool:
        return (self.role or '').lower() == 'admin'


login_manager = LoginManager()
login_manager.login_view = "login"


def create_app(config_override: dict | None = None):
    app = Flask(__name__, static_folder="static", template_folder="templates")
    app.config.from_object(Config)
    if config_override:
        app.config.update(config_override)

    login_manager.init_app(app)

    # Ensure tables
    with app.app_context():
        ensure_schema()

    @login_manager.user_loader
    def load_user(user_id: str):
        try:
            with engine.connect() as conn:
                row = conn.execute(
                    text("SELECT id, email, role FROM users WHERE id=:id"),
                    {"id": int(user_id)}
                ).mappings().first()
                return UserSession(**row) if row else None
        except Exception:
            return None

    @app.route("/")
    def index():
        return render_template("index.html", cfg=Config)

    # ---------- Auth ----------
    @app.get("/login")
    def login():
        if getattr(current_user, "is_authenticated", False):
            return redirect(url_for("admin_portal" if getattr(current_user, "is_admin", False) else "portal"))
        return render_template("login.html", cfg=Config, error=None)

    @app.post("/login")
    def login_post():
        email = (request.form.get("email") or "").strip().lower()
        password = (request.form.get("password") or "").strip()
        with engine.connect() as conn:
            row = conn.execute(
                text("SELECT id, email, role, password_hash FROM users WHERE email=:e LIMIT 1"),
                {"e": email}
            ).mappings().first()
        if not row or not check_password_hash(row["password_hash"], password):
            return render_template("login.html", cfg=Config, error="Invalid email or password."), 401
        login_user(UserSession(id=row["id"], email=row["email"], role=row["role"]))
        dest = request.args.get("next")
        if not dest:
            dest = url_for("admin_portal") if (row["role"] or "").lower() == "admin" else url_for("portal")
        return redirect(dest)

    @app.get("/logout")
    @login_required
    def logout():
        logout_user()
        return redirect(url_for("index"))

    @app.get("/signup")
    def signup():
        if getattr(current_user, "is_authenticated", False):
            return redirect(url_for("portal"))
        return render_template("signup.html", cfg=Config, error=None, form={})

    @app.post("/signup")
    def signup_post():
        f = request.form
        first = (f.get("first_name") or "").strip()
        last = (f.get("last_name") or "").strip()
        email = (f.get("email") or "").strip().lower()
        phone = (f.get("phone") or "").strip()
        pwd = (f.get("password") or "").strip()
        pwd2 = (f.get("confirm_password") or "").strip()
        address1 = (f.get("address1") or "").strip()
        address2 = (f.get("address2") or "").strip()
        city = (f.get("city") or "").strip()
        province = (f.get("province") or "").strip()
        postal_code = (f.get("postal_code") or "").strip()

        errors = []
        if not first or not last:
            errors.append("First and Last name are required.")
        if not email:
            errors.append("Email is required.")
        if not pwd or not pwd2:
            errors.append("Password and confirmation are required.")
        if pwd and len(pwd) < 8:
            errors.append("Password must be at least 8 characters.")
        if pwd and pwd2 and pwd != pwd2:
            errors.append("Passwords do not match.")

        with engine.connect() as conn:
            exists = conn.execute(text("SELECT 1 FROM users WHERE email=:e"), {"e": email}).first()
            if exists:
                errors.append("An account with this email already exists.")

        if errors:
            return render_template("signup.html", cfg=Config, error=" ".join(errors), form=f)

        # Create user + profile atomically
        pw_hash = generate_password_hash(pwd)
        with engine.begin() as conn:
            res = conn.execute(
                text("INSERT INTO users (email, password_hash, role) VALUES (:e, :p, 'consumer')"),
                {"e": email, "p": pw_hash},
            )
            user_id = res.lastrowid
            conn.execute(
                text(
                    """
                    INSERT INTO consumer_profiles
                    (user_id, full_name, phone, address1, address2, city, province, postal_code)
                    VALUES (:uid, :name, :phone, :a1, :a2, :city, :prov, :pc)
                    """
                ),
                {
                    "uid": user_id,
                    "name": f"{first} {last}".strip(),
                    "phone": phone,
                    "a1": address1,
                    "a2": address2,
                    "city": city,
                    "prov": province,
                    "pc": postal_code,
                },
            )
        login_user(UserSession(id=user_id, email=email, role='consumer'))
        return redirect(url_for("portal"))

    # Example admin-only page (optional)
    @app.get("/admin-portal")
    @login_required
    def admin_portal():
        if not getattr(current_user, "is_admin", False):
            return abort(403)
        return render_template("admin_portal.html", cfg=Config)

    @app.get("/portal")
    @login_required
    def portal():
        return render_template("portal.html", cfg=Config)

    # ---------- Contact API ----------
    @app.post("/contact")
    def contact():
        data = request.form or request.json or {}
        name = (data.get("name") or "").strip()
        email = (data.get("email") or "").strip()
        phone = (data.get("phone") or "").strip()
        subject = (data.get("subject") or "").strip()
        message = (data.get("message") or "").strip()
        if not name or not email or not message:
            return jsonify({"ok": False, "error": "Name, Email and Message are required."}), 400
        with engine.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO contact_messages (name, email, phone, subject, message)
                    VALUES (:n, :e, :p, :s, :m)
                    """
                ),
                {"n": name, "e": email, "p": phone, "s": subject, "m": message},
            )
        return jsonify({"ok": True})

    # ---------- Custom pages / error handlers ----------
    @app.errorhandler(404)
    def page_not_found(e):
        return render_template("404.html", cfg=Config), 404

    @app.route("/status/203")
    def status_203():
        return render_template("203.html", cfg=Config), 203

    return app


app = create_app()