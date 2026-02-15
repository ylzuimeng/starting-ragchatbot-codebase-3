"""
Database migration script to migrate from custom auth to FastAPI Users.

This script:
1. Backs up the existing database
2. Adds required FastAPI Users columns (is_superuser, is_verified)
3. Renames password_hash to hashed_password
4. Sets default values for existing users
"""
import sqlite3
import shutil
from pathlib import Path
from datetime import datetime


def migrate_database(db_path: str = "./users.db"):
    """
    Migrate the database to FastAPI Users format.

    Args:
        db_path: Path to the SQLite database file
    """
    db_path = Path(db_path)

    if not db_path.exists():
        print(f"❌ Database not found at {db_path}")
        return False

    # Create backup
    backup_path = db_path.with_suffix(f'.db.backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}')
    print(f"📦 Creating backup at {backup_path}")
    shutil.copy2(db_path, backup_path)
    print("✅ Backup created")

    # Connect to database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Check current schema
        cursor.execute("PRAGMA table_info(users)")
        columns = [row[1] for row in cursor.fetchall()]
        print(f"📋 Current columns: {columns}")

        # Check if migration already done
        if "hashed_password" in columns and "is_superuser" in columns:
            print("⚠️  Database already migrated")
            return True

        # Begin transaction
        conn.execute("BEGIN TRANSACTION")

        # Add new columns for FastAPI Users
        if "is_superuser" not in columns:
            print("➕ Adding is_superuser column")
            cursor.execute("ALTER TABLE users ADD COLUMN is_superuser BOOLEAN DEFAULT 0")

        if "is_verified" not in columns:
            print("➕ Adding is_verified column")
            cursor.execute("ALTER TABLE users ADD COLUMN is_verified BOOLEAN DEFAULT 1")

        # Rename password_hash to hashed_password
        # SQLite doesn't support ALTER TABLE RENAME COLUMN directly in older versions
        # So we need to recreate the table
        print("🔄 Renaming password_hash to hashed_password")

        # Get current data
        cursor.execute("SELECT * FROM users")
        rows = cursor.fetchall()
        column_names = [description[0] for description in cursor.description]

        # Create new table with updated schema
        cursor.execute("DROP TABLE IF EXISTS users_new")
        cursor.execute("""
            CREATE TABLE users_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email VARCHAR(100) UNIQUE NOT NULL,
                hashed_password VARCHAR(255) NOT NULL,
                username VARCHAR(50) UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP,
                is_active BOOLEAN DEFAULT 1,
                is_superuser BOOLEAN DEFAULT 0,
                is_verified BOOLEAN DEFAULT 1
            )
        """)

        # Migrate data
        for row in rows:
            row_dict = dict(zip(column_names, row))
            cursor.execute("""
                INSERT INTO users_new (
                    id, email, hashed_password, username, created_at,
                    last_login, is_active, is_superuser, is_verified
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                row_dict.get("id"),
                row_dict.get("email"),
                row_dict.get("password_hash"),  # Map password_hash to hashed_password
                row_dict.get("username"),
                row_dict.get("created_at"),
                row_dict.get("last_login"),
                row_dict.get("is_active", 1),
                row_dict.get("is_superuser", 0),  # Default to False
                row_dict.get("is_verified", 1)    # Default to True
            ))

        # Drop old table and rename new one
        cursor.execute("DROP TABLE users")
        cursor.execute("ALTER TABLE users_new RENAME TO users")

        # Recreate indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_username ON users(username)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_email ON users(email)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_session ON conversation_history(user_id, session_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_session_id ON user_sessions(session_id)")

        # Commit transaction
        conn.commit()
        print("✅ Migration completed successfully")

        # Verify migration
        cursor.execute("PRAGMA table_info(users)")
        new_columns = [row[1] for row in cursor.fetchall()]
        print(f"📋 New columns: {new_columns}")

        # Show user data
        cursor.execute("SELECT id, username, email, is_superuser, is_verified FROM users")
        users = cursor.fetchall()
        print(f"👥 Migrated {len(users)} users:")
        for user in users:
            print(f"   - ID: {user[0]}, Username: {user[1]}, Email: {user[2]}, Superuser: {user[3]}, Verified: {user[4]}")

        return True

    except Exception as e:
        conn.rollback()
        print(f"❌ Migration failed: {e}")

        # Restore from backup
        print(f"🔄 Restoring from backup...")
        shutil.copy2(backup_path, db_path)
        print("✅ Database restored")

        return False

    finally:
        conn.close()


if __name__ == "__main__":
    print("🚀 Starting database migration to FastAPI Users format...")
    print("=" * 60)

    success = migrate_database()

    print("=" * 60)
    if success:
        print("✅ Migration completed successfully!")
        print("\n📝 Next steps:")
        print("   1. Update backend/app.py to use FastAPI Users")
        print("   2. Update frontend endpoints")
        print("   3. Test the authentication flow")
    else:
        print("❌ Migration failed. Please check the errors above.")
