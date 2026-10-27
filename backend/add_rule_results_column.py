from app.database.connection import get_db_connection

def migrate_database():
    connection = get_db_connection()

    try:
        columns = connection.execute(
            "PRAGMA table_info(workflows)"
        ).fetchall()

        column_names = [column["name"] for column in columns]

        if "rule_results" not in column_names:
            connection.execute(
                "ALTER TABLE workflows ADD COLUMN rule_results TEXT"
            )
            connection.commit()
            print("SUCCESS: rule_results column added.")
        else:
            print("INFO: rule_results column already exists.")

    finally:
        connection.close()

if __name__ == "__main__":
    migrate_database()
