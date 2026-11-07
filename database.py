import sqlite3
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATABASE = Path(
    os.environ.get("DATABASE_PATH", BASE_DIR / "nextgen.db")
)

def get_db_connection():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    return connection

def initialize_database():
    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            guardian_name TEXT NOT NULL,
            address TEXT NOT NULL,
            dob TEXT NOT NULL,
            applying_class TEXT NOT NULL,
            student_phone TEXT,
            guardian_phone TEXT NOT NULL,
            student_email TEXT,
            guardian_email TEXT NOT NULL,
            submitted_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            public_token TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS queries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            email TEXT NOT NULL,
            phone TEXT NOT NULL,
            message TEXT NOT NULL,
            submitted_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    columns = {
        row["name"]
        for row in connection.execute(
            "PRAGMA table_info(applications)"
        )
    }
    if "public_token" not in columns:
        cursor.execute(
            "ALTER TABLE applications ADD COLUMN public_token TEXT"
        )
    cursor.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS
        idx_applications_public_token
        ON applications(public_token)
        WHERE public_token IS NOT NULL
    """)
    connection.commit()
    connection.close()