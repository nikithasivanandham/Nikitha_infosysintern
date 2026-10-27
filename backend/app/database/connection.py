import sqlite3
from pathlib import Path

from app.logger import logger


# Project root directory
BASE_DIR = Path(__file__).resolve().parents[2]

# Database file location
DATABASE_DIR = BASE_DIR / "data"
DATABASE_PATH = DATABASE_DIR / "airport_operations.db"


def get_db_connection():
    try:
        # Create the data directory if it does not exist
        DATABASE_DIR.mkdir(
            parents=True,
            exist_ok=True
        )

        # Connect to the SQLite database
        connection = sqlite3.connect(
            DATABASE_PATH,
            timeout=10
        )

        # Return rows as dictionary-like objects
        connection.row_factory = sqlite3.Row

        logger.info("SQLite database connection established")

        return connection

    except sqlite3.Error:
        logger.exception("Failed to connect to SQLite database")
        raise