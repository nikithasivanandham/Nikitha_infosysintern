from app.database.connection import get_db_connection
from app.logger import logger


def initialize_database():
    connection = get_db_connection()

    try:
        cursor = connection.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT UNIQUE NOT NULL,
                username TEXT UNIQUE NOT NULL,
                hashed_password TEXT NOT NULL,
                role TEXT NOT NULL
                    CHECK (role IN ('admin', 'operator', 'pilot')),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        connection.commit()

        logger.info("Users table initialized successfully")

    except Exception:
        connection.rollback()
        logger.exception("Failed to initialize database")
        raise

    finally:
        connection.close()

from app.core.security import hash_password

def create_user(
    user_id: str,
    username: str,
    password: str,
    role: str
) -> bool:

    connection = get_db_connection()

    try:
        hashed_password = hash_password(password)

        connection.execute(
            """
            INSERT INTO users (
                user_id,
                username,
                hashed_password,
                role
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                user_id,
                username,
                hashed_password,
                role
            )
        )

        connection.commit()

        logger.info("User created successfully: %s", username)

        return True

    except Exception:
        connection.rollback()
        logger.exception("Failed to create user")
        raise

    finally:
        connection.close()
def get_user_by_username(username: str) -> dict | None:

    connection = get_db_connection()

    try:
        row = connection.execute(
            """
            SELECT
                user_id,
                username,
                hashed_password,
                role
            FROM users
            WHERE username = ?
            """,
            (username,)
        ).fetchone()

        if row is None:
            return None

        return dict(row)

    finally:
        connection.close()

def get_user_by_id(user_id: str) -> dict | None:
    connection = get_db_connection()

    try:
        row = connection.execute(
            """
            SELECT user_id, username, role
            FROM users
            WHERE user_id = ?
            """,
            (user_id,)
        ).fetchone()

        if row is None:
            return None

        return dict(row)

    finally:
        connection.close()

def initialize_workflow_table():
    connection = get_db_connection()

    try:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS workflows (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                workflow_id TEXT UNIQUE NOT NULL,
                workflow_type TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                requested_by TEXT NOT NULL,
                input_data TEXT NOT NULL,
                decision TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        connection.commit()
        logger.info("Workflows table initialized successfully")

    except Exception:
        connection.rollback()
        logger.exception("Failed to initialize workflows table")
        raise

    finally:
        connection.close()

def initialize_permission_requests_table():
    connection = get_db_connection()

    try:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS permission_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                request_id TEXT UNIQUE NOT NULL,
                pilot_user_id TEXT NOT NULL,
                flight_number TEXT NOT NULL,
                requested_action TEXT NOT NULL,
                reason TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending'
                    CHECK (status IN ('pending', 'approved', 'rejected')),
                reviewed_by TEXT,
                review_comment TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        connection.commit()
        logger.info("Permission requests table initialized successfully")

    except Exception:
        connection.rollback()
        logger.exception("Failed to initialize permission requests table")
        raise

    finally:
        connection.close()

def initialize_audit_logs_table():
    connection = get_db_connection()

    try:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                action TEXT NOT NULL,
                resource_type TEXT NOT NULL,
                resource_id TEXT,
                details TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        connection.commit()

        logger.info("Audit logs table initialized successfully")

    except Exception:
        connection.rollback()
        logger.exception("Failed to initialize audit logs table")
        raise

    finally:
        connection.close()