from app.database.connection import get_db_connection

connection = get_db_connection()

try:
    rows = connection.execute(
        """
        SELECT
            id,
            user_id,
            action,
            resource_type,
            resource_id,
            details,
            created_at
        FROM audit_logs
        WHERE action IN (
            'PERMISSION_REQUEST_CREATED',
            'PERMISSION_REQUEST_APPROVED',
            'PERMISSION_REQUEST_REJECTED'
        )
        ORDER BY id DESC
        LIMIT 10
        """
    ).fetchall()

    if not rows:
        print("No matching audit records found.")

    for row in rows:
        print(dict(row))

finally:
    connection.close()