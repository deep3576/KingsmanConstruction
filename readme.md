# KingsmanRenovations.ca — Flask Single Page (PythonAnywhere)

**Company:** Kingsman Construction & Renovations Inc.  
**Domain:** kingsmanrenovations.ca  
**DB:** PythonAnywhere MySQL `deep3576$ProductionDB`

## 1) Single source of truth: `instance/config.ini`

Create from sample and edit secrets/DB:

```
cp instance/config_example.ini instance/config.ini
```

### Example `instance/config.ini`
```ini
[app]
env = production
secret_key = change_this_to_a_very_random_long_value
company_name = Kingsman Construction & Renovations Inc.
company_domain = kingsmanrenovations.ca
primary_color = #0f172a
accent_color = #dc2626

[database]
engine = mysql
driver = pymysql
user = deep3576
password = YOUR_DB_PASSWORD
host = deep3576.mysql.pythonanywhere-services.com
name = deep3576$ProductionDB
charset = utf8mb4
```

> For local-only dev, switch to SQLite:
> ```ini
> [database]
> engine = sqlite
> path = instance/app.db
> ```

## 2) Local run

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python create_db.py
flask --app app run --debug
```

## 3) Deploy on PythonAnywhere

- Upload project to `/home/deep3576/KingsmanRenovations/`.
- Place your **instance/config.ini** at `/home/deep3576/KingsmanRenovations/instance/config.ini`.
- On the **Web** tab: set source to the folder and WSGI to `wsgi.py`.
- Point the virtualenv and `pip install -r requirements.txt`.
- **Reload** the app.
- Open a Bash console and run:
```bash
python create_db.py
```

## 4) Troubleshooting

- **Missing DB URI:** Ensure `instance/config.ini` exists and `[database]` is correctly filled. The app will fall back to SQLite only if you explicitly set `engine = sqlite`.
- **Inspect config at runtime:** temporarily call `Config.debug_print()` inside `create_app()` while debugging.

## 5) Notes
- The contact form stores messages in `contact_messages`.
- Images in `static/img/` are placeholders—swap with real photos.
- Brand text/colors come from `config.ini` → `Config` → templates.
```

cp instance/config_example.ini instance/config.ini
```

Edit values:

```ini
[app]
env = production
secret_key = change_this_to_a_very_random_long_value
company_name = Kingsman Construction & Renovations Inc.
company_domain = kingsmanrenovations.ca

[database]
engine = mysql
driver = pymysql
user = deep3576
password = YOUR_DB_PASSWORD
host = deep3576.mysql.pythonanywhere-services.com
name = deep3576$ProductionDB
charset = utf8mb4
```

> Local dev? Use SQLite by switching the database section to:
>
> ```ini
> [database]
> engine = sqlite
> path = instance/app.db
> ```

## 2) Local setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python create_db.py
flask --app app run --debug
```

## 3) PythonAnywhere deployment

- Upload to `/home/deep3576/KingsmanRenovations/`.
- Place your `config.ini` at `/home/deep3576/KingsmanRenovations/instance/config.ini`.
- (Optional) You can set env vars instead of INI, but INI is recommended.
- In **Virtualenv**, point to your venv and `pip install -r requirements.txt`.
- Click **Reload**; then open a Bash console and run:

```bash
python create_db.py
```

## 4) Troubleshooting

- Error: `Either 'SQLALCHEMY_DATABASE_URI' or 'SQLALCHEMY_BINDS' must be set` → The app didn’t find a DB URI. Ensure `instance/config.ini` exists **or** environment variables are set.
- To verify what URI is used, temporarily call `Config.debug_print()` inside `create_app()` during a test run.

## 5) Alternatives

- `.env` still works if you prefer environment variables.
- A full URI via `SQLALCHEMY_DATABASE_URI` overrides everything.
```
bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with DB password (and optionally other DB pieces)
python create_db.py
flask --app app run --debug
```

> If you see `RuntimeError: Either 'SQLALCHEMY_DATABASE_URI' or 'SQLALCHEMY_BINDS' must be set`, it means the app couldn't find a DB URI. Fix by:
> 1) Ensure `.env` exists and includes `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_NAME` **or** a full `SQLALCHEMY_DATABASE_URI`.
> 2) On PythonAnywhere, set these as **Environment variables** on the Web tab, then **Reload**.
> 3) You can also run locally with the built‑in SQLite fallback if no MySQL vars are present.

Visit http://127.0.0.1:5000

## 2) PythonAnywhere deployment

1. Upload the whole `KingsmanRenovations/` folder to `/home/deep3576/`.
2. On the **Web** tab, create a new Flask app (Manual config). Set **Source code** to `/home/deep3576/KingsmanRenovations` and **WSGI file** to `/home/deep3576/KingsmanRenovations/wsgi.py`.
3. In the **Virtualenv** section, point to `/home/deep3576/KingsmanRenovations/.venv` (create and `pip install -r requirements.txt`).
4. In the **Environment variables** section, set:
   - `SECRET_KEY`
   - `DB_USER=deep3576`
   - `DB_PASSWORD=YOUR_DB_PASSWORD`
   - `DB_HOST=deep3576.mysql.pythonanywhere-services.com`
   - `DB_NAME=deep3576$ProductionDB`
   *(Alternatively, set a single `SQLALCHEMY_DATABASE_URI` string.)*
5. **Reload** the web app. Run `python create_db.py` once on the **Consoles** tab → Bash to create tables.

## 3) Custom domain (kingsmanrenovations.ca)

1. In PythonAnywhere **Web → Add a custom domain**, enter `kingsmanrenovations.ca` (and optionally `www.kingsmanrenovations.ca`).
2. In your domain DNS (at your registrar), add the required **A**/**CNAME** records that PA shows.
3. Back on PA, enable **HTTPS** (Let’s Encrypt) and request a certificate.

## 4) Database connection string examples

- **Built from parts (recommended):** handled automatically by `config.py` when the four `DB_*` vars are present.
- **Explicit full URI:**

```
mysql+pymysql://deep3576:YOUR_DB_PASSWORD@deep3576.mysql.pythonanywhere-services.com/deep3576$ProductionDB?charset=utf8mb4
```

## 5) Notes
- The contact form writes to `contact_messages` table. Retrieve via a simple admin route later or directly from MySQL.
- Images in `static/img/` are placeholders — replace with real photos.
- Colors and copy are controlled via `config.py` and templates.
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with DB password
python create_db.py
flask --app app run --debug
```

Visit http://127.0.0.1:5000

## 2) PythonAnywhere deployment

1. Upload the whole `KingsmanRenovations/` folder to `/home/deep3576/`.
2. On the **Web** tab, create a new Flask app (Manual config). Set **Source code** to `/home/deep3576/KingsmanRenovations` and **WSGI file** to `/home/deep3576/KingsmanRenovations/wsgi.py`.
3. In the **Virtualenv** section, point to `/home/deep3576/KingsmanRenovations/.venv` (create and `pip install -r requirements.txt`).
4. In the **Environment variables** section, set these to match `.env`:
   - `SECRET_KEY`
   - `SQLALCHEMY_DATABASE_URI`
5. **Reload** the web app. Run `python create_db.py` once on the **Consoles** tab → Bash to create tables.

## 3) Custom domain (kingsmanrenovations.ca)

1. In PythonAnywhere **Web → Add a custom domain**, enter `kingsmanrenovations.ca` (and optionally `www.kingsmanrenovations.ca`).
2. In your domain DNS (at your registrar), add the required **A**/**CNAME** records that PA shows.
3. Back on PA, enable **HTTPS** (Let’s Encrypt) and request a certificate.

## 4) Database connection string

```
mysql+pymysql://deep3576:YOUR_DB_PASSWORD@deep3576.mysql.pythonanywhere-services.com/deep3576$ProductionDB?charset=utf8mb4
```

## 5) Notes
- The contact form writes to `contact_messages` table. Retrieve via a simple admin route later or directly from MySQL.
- Images in `static/img/` are placeholders — replace with real photos.
- Colors and copy are controlled via `config.py` and templates.
