
import sqlite3
import sys
from pathlib import Path

# Add src to path to import config
current_dir = Path(__file__).resolve().parent
sys.path.append(str(current_dir))

from hamal.core.config import get_database_path


def migrate():
    db_path = get_database_path()
    print(f"Migrating database at: {db_path}")

    if not db_path.exists():
        print("Database not found. Nothing to migrate.")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Get existing columns
        cursor.execute("PRAGMA table_info(projects)")
        columns = [info[1] for info in cursor.fetchall()]
        print(f"Existing columns: {columns}")

        # Add auto_restart
        if "auto_restart" not in columns:
            print("Adding auto_restart column...")
            cursor.execute("ALTER TABLE projects ADD COLUMN auto_restart BOOLEAN NOT NULL DEFAULT 0")

        # Add schedule_start
        if "schedule_start" not in columns:
            print("Adding schedule_start column...")
            cursor.execute("ALTER TABLE projects ADD COLUMN schedule_start TEXT")

        # Add schedule_stop
        if "schedule_stop" not in columns:
            print("Adding schedule_stop column...")
            cursor.execute("ALTER TABLE projects ADD COLUMN schedule_stop TEXT")

        # Add custom_scripts
        if "custom_scripts" not in columns:
            print("Adding custom_scripts column...")
            cursor.execute("ALTER TABLE projects ADD COLUMN custom_scripts TEXT")

        conn.commit()
        print("Migration complete.")

    except Exception as e:
        print(f"Migration failed: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
