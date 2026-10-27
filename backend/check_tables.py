from app.database.connection import get_db_connection


conn = get_db_connection()

try:
    query = """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
    """

    tables = conn.execute(query).fetchall()

    print("Tables in database:")

    for table in tables:
        print(table["name"])

finally:
    conn.close()