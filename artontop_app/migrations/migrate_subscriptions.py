import sqlite3
import os

# Path to your database
db_path = os.path.join(os.path.dirname(__file__), 'database.db')

# Connect to database
conn = sqlite3.connect("/artontop/artontop_app/database.db")
cursor = conn.cursor()

def table_exists(table_name):
    """Check if a table exists"""
    cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}'")
    return cursor.fetchone() is not None

try:
    print("Starting database migration for subscription system...\n")
    
    # Check if tables exist
    if not table_exists('user'):
        print("✗ Error: Database tables don't exist yet!")
        print("\nPlease run the application first to create the initial database:")
        print("  python app.py")
        print("\nThe app will create the database on first run, then you can run this migration.")
        exit(1)
    
    # --- Create Subscription table ---
    if table_exists('subscription'):
        print("✓ Subscription table already exists, skipping creation.")
    else:
        print("Creating Subscription table...")
        cursor.execute('''
            CREATE TABLE subscription (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                follower_id INTEGER NOT NULL,
                following_id INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (follower_id) REFERENCES user (id),
                FOREIGN KEY (following_id) REFERENCES user (id),
                UNIQUE (follower_id, following_id)
            )
        ''')
        print("  ✓ Subscription table created")
    
    # Commit changes
    conn.commit()
    print("\n" + "="*50)
    print("✓ Subscription system migration completed successfully!")
    print("All existing data has been preserved.")
    print("="*50)
    
except sqlite3.Error as e:
    print(f"\n✗ Error during migration: {e}")
    conn.rollback()
    
finally:
    conn.close()
