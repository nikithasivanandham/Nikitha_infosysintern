import json

from app.database.connection import get_db_connection


def log_audit_event(
    user_id: str,
    action: str,
    resource_type: str,
    resource_id: str | None = None,
    details: dict | None = None,
):
    connection = get_db_connection()

    try:
        details_json = (
            json.dumps(details)
            if details is not None
            else None
        )

        connection.execute(
            """
            INSERT INTO audit_logs (
                user_id,
                action,
                resource_type,
                resource_id,
                details
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                user_id,
                action,
                resource_type,
                resource_id,
                details_json,
            ),
        )

        connection.commit()

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()