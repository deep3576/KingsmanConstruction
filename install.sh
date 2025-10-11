cd kingsmanConstruction
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env   # edit DB_* if you have MySQL locally; or use sqlite for quick test if you prefer
# create DB tables (Alembic)
flask --app app db init
flask --app app db migrate -m "init"
flask --app app db upgrade

# create an admin
flask --app app create-admin admin@example.com 'ChangeMe!123' Inderdeep Singh

flask --app app run --debug
