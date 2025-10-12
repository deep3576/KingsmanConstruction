from flask import Flask, render_template, request, jsonify, redirect, url_for
from config import Config
from models import db, ContactMessage, User
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash


login_manager = LoginManager()
login_manager.login_view = "login"


def create_app(config_override: dict | None = None):
    app = Flask(__name__, static_folder="static", template_folder="templates")
    app.config.from_object(Config)
    if config_override:
        app.config.update(config_override)

    # init db + login manager
    db.init_app(app)
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        try:
            return User.query.get(int(user_id))
        except Exception:
            return None

    @app.route("/")
    def index():
        return render_template("index.html", cfg=Config)

    # ---------- Auth ----------
    @app.get("/login")
    def login():
        if getattr(current_user, "is_authenticated", False):
            return redirect(url_for("portal"))
        return render_template("login.html", cfg=Config, error=None)

    @app.post("/login")
    def login_post():
        email = (request.form.get("email") or "").strip().lower()
        password = (request.form.get("password") or "").strip()
        user = User.query.filter_by(email=email).first()
        if not user or not check_password_hash(user.password_hash, password):
            # Re-render with error message
            return render_template("login.html", cfg=Config, error="Invalid email or password."), 401
        login_user(user)
        next_url = request.args.get("next") or url_for("portal")
        return redirect(next_url)

    @app.get("/logout")
    @login_required
    def logout():
        logout_user()
        return redirect(url_for("index"))

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

        cm = ContactMessage(name=name, email=email, phone=phone, subject=subject, message=message)
        db.session.add(cm)
        db.session.commit()
        return jsonify({"ok": True})

    # ---------- Custom pages / error handlers ----------
    @app.errorhandler(404)
    def page_not_found(e):
        # Render your custom 404 template
        return render_template("404.html", cfg=Config), 404

    @app.route("/status/203")
    def status_203():
        # Serve a custom informational page with HTTP 203 status
        return render_template("203.html", cfg=Config), 203

    return app


app = create_app()