from fastapi import APIRouter, Depends

from app.core.permissions import require_roles
from app.database.connection import get_db_connection

router = APIRouter(
    prefix="/audit",
    tags=["Audit Logs"],
)


@router.get("/")
def get_audit_logs(
    current_user: dict = Depends(require_roles("admin")),
):
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
            ORDER BY id DESC
            LIMIT 100
            """
        ).fetchall()

        return [dict(row) for row in rows]

    finally:
        connection.close()