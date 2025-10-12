from sqlalchemy import create_engine, text
from config import Config

# pooled engine
engine = create_engine(
    Config.SQLALCHEMY_DATABASE_URI,
    pool_pre_ping=True,
    future=True,
)


def ensure_schema():
    """Create/upgrade tables using plain MySQL DDL. All IDs are SIGNED INT.
    Also ensures a `role` column on `users` (admin/consumer)."""
    sql_users = """
    CREATE TABLE IF NOT EXISTS users (
        id INT NOT NULL AUTO_INCREMENT,
        email VARCHAR(200) NOT NULL UNIQUE,
        password_hash VARCHAR(255) NOT NULL,
        role ENUM('admin','consumer') NOT NULL DEFAULT 'consumer',
        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (id),
        INDEX idx_users_email (email)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """

    sql_consumer_profiles = """
    CREATE TABLE IF NOT EXISTS consumer_profiles (
        id INT NOT NULL AUTO_INCREMENT,
        user_id INT NOT NULL UNIQUE,
        full_name VARCHAR(200) NOT NULL,
        phone VARCHAR(40),
        address1 VARCHAR(200),
        address2 VARCHAR(200),
        city VARCHAR(100),
        province VARCHAR(100),
        postal_code VARCHAR(20),
        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (id),
        CONSTRAINT fk_consumer_user
          FOREIGN KEY (user_id) REFERENCES users(id)
          ON DELETE CASCADE ON UPDATE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """

    sql_contact_messages = """
    CREATE TABLE IF NOT EXISTS contact_messages (
        id INT NOT NULL AUTO_INCREMENT,
        name VARCHAR(120) NOT NULL,
        email VARCHAR(200) NOT NULL,
        phone VARCHAR(40),
        subject VARCHAR(200),
        message TEXT NOT NULL,
        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (id),
        INDEX idx_contact_email (email),
        INDEX idx_contact_created (created_at)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """

    with engine.begin() as conn:
        # Base tables
        conn.execute(text(sql_users))
        # Ensure role column exists for older deployments
        role_exists = conn.execute(text("""
            SELECT 1 FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE()
              AND TABLE_NAME = 'users'
              AND COLUMN_NAME = 'role'
            LIMIT 1
        """)).first()
        if not role_exists:
            conn.execute(text(
                "ALTER TABLE users ADD COLUMN role ENUM('admin','consumer') NOT NULL DEFAULT 'consumer' AFTER password_hash"
            ))
        conn.execute(text(sql_consumer_profiles))
        conn.execute(text(sql_contact_messages))