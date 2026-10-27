from app.database.audit import log_audit_event
from app.database.connection import get_db_connection


log_audit_event(
    user_id="test_user",
    action="AUDIT_TEST",
    resource_type="test",
    resource_id="test_resource_001",
    details={
        "message": "Testing audit logging"
    },
)

connection = get_db_connection()

try:
    row = connection.execute(
        """
        SELECT *
        FROM audit_logs
        WHERE action = ?
        ORDER BY id DESC
        LIMIT 1
        """,
        ("AUDIT_TEST",),
    ).fetchone()

    if row:
        print("Audit log created successfully.")
        print(dict(row))
    else:
        print("Audit log not found.")

finally:
    connection.close()