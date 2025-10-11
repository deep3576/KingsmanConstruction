from flask import Flask, render_template, request, jsonify
from config import Config
from models import db, ContactMessage


def create_app(config_override: dict | None = None):
    app = Flask(__name__, static_folder="static", template_folder="templates")
    app.config.from_object(Config)
    if config_override:
        app.config.update(config_override)

    # init db
    db.init_app(app)

    @app.route("/")
    def index():
        return render_template("index.html", cfg=Config)

    @app.route("/login")
    def login():
        return render_template("login.html", cfg=Config)

    @app.errorhandler(404)
    def page_not_found(e):
        return render_template("404.html", cfg=Config), 404

    @app.errorhandler(403)
    def page_not(e):
        return render_template("403.html", cfg=Config), 403

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

    return app


app = create_app()