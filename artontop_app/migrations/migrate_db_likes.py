import sqlite3
import os

# Path to your database
db_path = os.path.join(os.path.dirname(__file__), 'database.db')

# Connect to database
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

def column_exists(table_name, column_name):
    """Check if a column exists in a table"""
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = [row[1] for row in cursor.fetchall()]
    return column_name in columns

def table_exists(table_name):
    """Check if a table exists"""
    cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}'")
    return cursor.fetchone() is not None

try:
    print("Starting database migration...\n")
    
    # --- Migrate PublicationLike table ---
    if table_exists('publication_like'):
        print("PublicationLike table exists, checking schema...")
        
        # Check if created_at column exists
        if not column_exists('publication_like', 'created_at'):
            print("  Adding 'created_at' column...")
            cursor.execute('''
                ALTER TABLE publication_like 
                ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            ''')
            print("  ✓ Added 'created_at' column")
        else:
            print("  ✓ Schema is up to date")
    else:
        print("Creating PublicationLike table...")
        cursor.execute('''
            CREATE TABLE publication_like (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pub_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (pub_id) REFERENCES publication (id),
                FOREIGN KEY (user_id) REFERENCES user (id),
                UNIQUE (pub_id, user_id)
            )
        ''')
        print("  ✓ PublicationLike table created")
    
    # --- Migrate RemixLike table ---
    if table_exists('remix_like'):
        print("\nRemixLike table exists, checking schema...")
        
        # Check if created_at column exists
        if not column_exists('remix_like', 'created_at'):
            print("  Adding 'created_at' column...")
            cursor.execute('''
                ALTER TABLE remix_like 
                ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            ''')
            print("  ✓ Added 'created_at' column")
        else:
            print("  ✓ Schema is up to date")
    else:
        print("\nCreating RemixLike table...")
        cursor.execute('''
            CREATE TABLE remix_like (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                remix_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (remix_id) REFERENCES remix (id),
                FOREIGN KEY (user_id) REFERENCES user (id),
                UNIQUE (remix_id, user_id)
            )
        ''')
        print("  ✓ RemixLike table created")
    
    # Commit changes
    conn.commit()
    print("\n" + "="*50)
    print("✓ Database migration completed successfully!")
    print("All existing data has been preserved.")
    print("="*50)
    
except sqlite3.Error as e:
    print(f"\n✗ Error during migration: {e}")
    conn.rollback()
    
finally:
    conn.close()
