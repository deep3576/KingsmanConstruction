from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from datetime import datetime, date
from calendar import monthrange
from flask import Flask, render_template, request, jsonify, redirect, url_for, abort
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash, generate_password_hash
from sqlalchemy import text

from config import Config
from db import engine, ensure_schema


def _require_admin():
    if not current_user.is_authenticated or getattr(current_user, "role", None) != "admin":
        abort(403)


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

    # ---------- Admin Portal & Tabs (with Employees subtabs) ----------
    @app.get("/admin-portal")
    @login_required
    def admin_portal():
        if not getattr(current_user, "is_admin", False):
            return abort(403)

        tab = (request.args.get("tab") or "dashboard").lower()
        if tab not in ("dashboard", "employees", "jobs"):
            tab = "dashboard"

        # NEW: handle employees subtabs
        subtab = None
        if tab == "employees":
            subtab = (request.args.get("subtab") or "manage").lower()
            allowed_subtabs = {"manage", "timesheet", "dashboard", "payments"}
            if subtab not in allowed_subtabs:
                subtab = "manage"

        employees = None
        employees_metrics = None

        if tab == "employees":
            # Load employees for manage & timesheet views (handy for selectors)
            with engine.connect() as conn:
                employees = conn.execute(text(
                    """
                    SELECT id, full_name, job_title, email, phone, daily_rate, status, start_date, created_at, updated_at
                    FROM employees
                    ORDER BY created_at DESC
                    """
                )).mappings().all()

                # Simple metrics for the Employees->Dashboard subtab
                if subtab == "dashboard":
                    employees_metrics = conn.execute(text(
                        """
                        SELECT
                          COUNT(*)                                   AS total,
                          SUM(CASE WHEN status='active' THEN 1 ELSE 0 END)   AS active_count,
                          SUM(CASE WHEN status='inactive' THEN 1 ELSE 0 END) AS inactive_count,
                          ROUND(AVG(daily_rate), 2)                   AS avg_daily_rate
                        FROM employees
                        """
                    )).mappings().first()

        return render_template(
            "admin_portal.html",
            cfg=Config,
            tab=tab,
            subtab=subtab,                 # <-- pass to template
            employees=employees,
            employees_metrics=employees_metrics,
            form_error=None,
            form_data=None
        )

    @app.get("/admin-portal/employees")
    @login_required
    def admin_portal_employees():
        if not getattr(current_user, "is_admin", False):
            return abort(403)
        # Preserve subtab if provided, default to 'manage'
        subtab = (request.args.get("subtab") or "manage").lower()
        return redirect(url_for("admin_portal", tab="employees", subtab=subtab))

    # NEW: convenience redirect /admin-portal/employees/<subtab>
    @app.get("/admin-portal/employees/<string:subtab>")
    @login_required
    def admin_portal_employees_subtab(subtab: str):
        if not getattr(current_user, "is_admin", False):
            return abort(403)
        return redirect(url_for("admin_portal", tab="employees", subtab=subtab.lower()))

    @app.get("/admin-portal/jobs")
    @login_required
    def admin_portal_jobs():
        if not getattr(current_user, "is_admin", False):
            return abort(403)
        return redirect(url_for("admin_portal", tab="jobs"))

    # Create employee (HTML form submit)
    @app.post("/admin-portal/employees")
    @login_required
    def admin_portal_employees_post():
        if not getattr(current_user, "is_admin", False):
            return abort(403)
        f = request.form
        full_name = (f.get("full_name") or "").strip()
        job_title = (f.get("job_title") or "").strip()
        email = (f.get("email") or "").strip()
        phone = (f.get("phone") or "").strip()
        day_rate_raw = (f.get("daily_rate") or "").strip()
        start_date_raw = (f.get("start_date") or "").strip()
        status = (f.get("status") or "active").strip().lower()
        if status not in ("active", "inactive"):
            status = "active"

        errors = []
        if not full_name:
            errors.append("Full name is required.")
        try:
            daily_rate = Decimal(day_rate_raw)
            if daily_rate <= 0:
                errors.append("Daily rate must be greater than 0.")
        except (InvalidOperation, TypeError):
            errors.append("Daily rate must be a number.")

        start_date = None
        if start_date_raw:
            try:
                start_date = datetime.strptime(start_date_raw, "%Y-%m-%d").date()
            except ValueError:
                errors.append("Start date must be YYYY-MM-DD.")

        if errors:
            with engine.connect() as conn:
                employees = conn.execute(text(
                    "SELECT id, full_name, job_title, email, phone, daily_rate, status, start_date, created_at, updated_at FROM employees ORDER BY created_at DESC"
                )).mappings().all()
            return render_template(
                "admin_portal.html",
                cfg=Config,
                tab="employees",
                subtab="manage",   # ensure subtab context on error
                employees=employees,
                form_error=" ".join(errors),
                form_data=f,
            ), 400

        with engine.begin() as conn:
            conn.execute(text(
                """
                INSERT INTO employees (full_name, job_title, email, phone, daily_rate, start_date, status)
                VALUES (:n, :t, :e, :p, :r, :sd, :st)
                """
            ), {
                "n": full_name,
                "t": job_title or None,
                "e": email or None,
                "p": phone or None,
                "r": str(daily_rate),
                "sd": start_date,
                "st": status,
            })
        # Land back on Employees -> Manage
        return redirect(url_for("admin_portal", tab="employees", subtab="manage"))

    # -------- Attendance API (Admin only) --------
    @app.get("/admin-portal/attendance-data")
    @login_required
    def attendance_data():
        if not getattr(current_user, "is_admin", False):
            return abort(403)
        try:
            employee_id = int(request.args.get("employee_id") or 0)
            year = int(request.args.get("year") or date.today().year)
            month = int(request.args.get("month") or date.today().month)
        except ValueError:
            return jsonify({"ok": False, "error": "Invalid parameters."}), 400
        if not employee_id:
            return jsonify({"ok": True, "days": {}, "year": year, "month": month})
        first_day = date(year, month, 1)
        last_day = date(year, month, monthrange(year, month)[1])
        with engine.connect() as conn:
            rows = conn.execute(text(
                """
                SELECT work_date, status,
                       TIME_FORMAT(sign_in, '%H:%i') AS sign_in,
                       TIME_FORMAT(sign_out, '%H:%i') AS sign_out,
                       notes
                FROM employee_status_log
                WHERE employee_id=:eid AND work_date BETWEEN :d1 AND :d2
                ORDER BY work_date
                """
            ), {"eid": employee_id, "d1": first_day, "d2": last_day}).mappings().all()
        days = {r["work_date"].isoformat(): {"status": r["status"], "sign_in": r["sign_in"], "sign_out": r["sign_out"], "notes": r["notes"]} for r in rows}
        return jsonify({"ok": True, "days": days, "year": year, "month": month})

    @app.post("/admin-portal/attendance-save")
    @login_required
    def attendance_save():
        if not getattr(current_user, "is_admin", False):
            return abort(403)
        data = request.get_json(silent=True) or {}
        try:
            employee_id = int(data.get("employee_id") or 0)
            work_date = data.get("date")  # YYYY-MM-DD
            status = (data.get("status") or "present").lower()
            if status not in ("present", "absent", "half-day", "leave"):
                status = "present"
            sin = (data.get("sign_in_time") or "").strip()  # HH:MM
            sout = (data.get("sign_out_time") or "").strip()  # HH:MM
            notes = (data.get("notes") or "").strip() or None
        except Exception:
            return jsonify({"ok": False, "error": "Invalid payload."}), 400
        if not employee_id or not work_date:
            return jsonify({"ok": False, "error": "employee_id and date are required."}), 400

        sign_in_dt = None
        sign_out_dt = None
        try:
            if sin:
                datetime.strptime(sin, "%H:%M")
                sign_in_dt = f"{work_date} {sin}:00"
            if sout:
                datetime.strptime(sout, "%H:%M")
                sign_out_dt = f"{work_date} {sout}:00"
        except ValueError:
            return jsonify({"ok": False, "error": "Time must be HH:MM."}), 400

        with engine.begin() as conn:
            conn.execute(text(
                """
                INSERT INTO employee_status_log (employee_id, work_date, status, sign_in, sign_out, notes)
                VALUES (:eid, :d, :st, :si, :so, :n)
                ON DUPLICATE KEY UPDATE
                  status=VALUES(status), sign_in=VALUES(sign_in), sign_out=VALUES(sign_out), notes=VALUES(notes)
                """
            ), {"eid": employee_id, "d": work_date, "st": status, "si": sign_in_dt, "so": sign_out_dt, "n": notes})
        return jsonify({"ok": True})

    @app.get("/portal")
    @login_required
    def portal():
        return render_template("portal.html", cfg=Config)

    # ---------- Employees: Create (JSON) ----------
    @app.route("/admin-portal/employees/create", methods=["POST"])
    @login_required
    def admin_portal_employees_create():
        _require_admin()
        data = request.get_json() or request.form
        full_name = (data.get("full_name") or "").strip()
        daily_rate = data.get("daily_rate")
        if not full_name or not daily_rate:
            return jsonify(ok=False, error="Full name and daily rate are required."), 400

        job_title = (data.get("job_title") or "").strip() or None
        email = (data.get("email") or "").strip() or None
        phone = (data.get("phone") or "").strip() or None
        start_date = (data.get("start_date") or "").strip() or None
        status = (data.get("status") or "active").strip()
        if status not in ("active", "inactive"): status = "active"

        with engine.begin() as conn:
            conn.execute(text("""
                INSERT INTO employees (full_name, job_title, email, phone, daily_rate, start_date, status)
                VALUES (:full_name, :job_title, :email, :phone, :daily_rate, :start_date, :status)
            """), {
                "full_name": full_name,
                "job_title": job_title,
                "email": email,
                "phone": phone,
                "daily_rate": daily_rate,
                "start_date": start_date,
                "status": status
            })
            new_id = conn.execute(text("SELECT LAST_INSERT_ID()")).scalar()
            row = conn.execute(text("""
                SELECT id, full_name, job_title, email, phone, daily_rate, start_date, status, updated_at
                FROM employees WHERE id=:id
            """), {"id": new_id}).mappings().first()

        return jsonify(ok=True, employee=dict(row))

    # Update employee status (JSON)
    @app.route("/admin-portal/employees/<int:emp_id>/status", methods=["POST"])
    @login_required
    def admin_portal_employee_status(emp_id):
        _require_admin()
        data = request.get_json() or {}
        status = (data.get("status") or "").strip()
        if status not in ("active", "inactive"):
            return jsonify(ok=False, error="Invalid status."), 400
        with engine.begin() as conn:
            res = conn.execute(text("UPDATE employees SET status=:s WHERE id=:i"), {"s": status, "i": emp_id})
            if res.rowcount == 0:
                return jsonify(ok=False, error="Employee not found."), 404
        return jsonify(ok=True)

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

    @app.route("/status/403")
    def status_403():
        return render_template("403.html", cfg=Config), 403

    return app


app = create_app()
