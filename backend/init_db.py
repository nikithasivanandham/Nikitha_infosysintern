from app.database.database import (
    initialize_database,
    initialize_workflow_table,
    initialize_permission_requests_table,
    initialize_audit_logs_table,
)


if __name__ == "__main__":
    initialize_database()
    initialize_workflow_table()
    initialize_permission_requests_table()
    initialize_audit_logs_table()

    print("Database initialized successfully.")