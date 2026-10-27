from app.database.connection import get_db_connection


def migrate_workflow_table():
    connection = get_db_connection()

    try:
        cursor = connection.cursor()

        # Check whether the workflows table exists.
        table = cursor.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
              AND name = 'workflows'
            """
        ).fetchone()

        if table is None:
            raise RuntimeError(
                "The workflows table does not exist. "
                "Migration cancelled."
            )

        # Read the existing table columns.
        columns = {
            row["name"]
            for row in cursor.execute(
                "PRAGMA table_info(workflows)"
            ).fetchall()
        }

        # Add the column only if it does not already exist.
        if "planning_result" not in columns:
            cursor.execute(
                """
                ALTER TABLE workflows
                ADD COLUMN planning_result TEXT
                """
            )

            connection.commit()

            print(
                "Migration successful: "
                "planning_result column added."
            )
        else:
            print(
                "Migration skipped: "
                "planning_result column already exists."
            )

        # Verify the final table structure.
        updated_columns = cursor.execute(
            "PRAGMA table_info(workflows)"
        ).fetchall()

        print("\nUpdated workflows table columns:")

        for column in updated_columns:
            print(
                f"- {column['name']} "
                f"({column['type']})"
            )

        print("\nDatabase migration completed successfully.")

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


if __name__ == "__main__":
    migrate_workflow_table()