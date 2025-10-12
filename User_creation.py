from werkzeug.security import generate_password_hash
from app import create_app
from models import db, User
app = create_app()
with app.app_context():
    u = User(email="harpreet@kingsmanrenovations.ca", password_hash=generate_password_hash("admin123"))
    db.session.add(u)
    db.session.commit()
    print("User created:", u.email)