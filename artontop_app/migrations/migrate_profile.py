import sqlite3
import os

# Path to your database
db_path = os.path.join(os.path.dirname(__file__), 'database.db')

# Connect to database
conn = sqlite3.connect("/artontop/artontop_app/database.db")
cursor = conn.cursor()

def column_exists(table_name, column_name):
    """Check if a column exists in a table"""
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = [row[1] for row in cursor.fetchall()]
    return column_name in columns

try:
    print("Starting database migration for profile system...\n")
    
    # --- Update User table ---
    print("Updating User table...")
    
    if not column_exists('user', 'avatar'):
        print("  Adding 'avatar' column...")
        cursor.execute('''
            ALTER TABLE user 
            ADD COLUMN avatar VARCHAR(200) DEFAULT 'default_avatar.svg'
        ''')
        print("  ✓ Added 'avatar' column")
    
    if not column_exists('user', 'bio'):
        print("  Adding 'bio' column...")
        cursor.execute('''
            ALTER TABLE user 
            ADD COLUMN bio TEXT
        ''')
        print("  ✓ Added 'bio' column")
    
    if not column_exists('user', 'rating'):
        print("  Adding 'rating' column...")
        cursor.execute('''
            ALTER TABLE user 
            ADD COLUMN rating INTEGER DEFAULT 0
        ''')
        print("  ✓ Added 'rating' column")
    
    if not column_exists('user', 'subscribers_count'):
        print("  Adding 'subscribers_count' column...")
        cursor.execute('''
            ALTER TABLE user 
            ADD COLUMN subscribers_count INTEGER DEFAULT 0
        ''')
        print("  ✓ Added 'subscribers_count' column")
    
    # --- Update Publication table ---
    print("\nUpdating Publication table...")
    
    if not column_exists('publication', 'pinned'):
        print("  Adding 'pinned' column...")
        cursor.execute('''
            ALTER TABLE publication 
            ADD COLUMN pinned BOOLEAN DEFAULT 0
        ''')
        print("  ✓ Added 'pinned' column")
    
    if not column_exists('publication', 'created_at'):
        print("  Adding 'created_at' column...")
        cursor.execute('''
            ALTER TABLE publication 
            ADD COLUMN created_at TIMESTAMP
        ''')
        # Update existing rows with current timestamp
        cursor.execute('''
            UPDATE publication 
            SET created_at = CURRENT_TIMESTAMP 
            WHERE created_at IS NULL
        ''')
        print("  ✓ Added 'created_at' column")
    
    # Commit changes
    conn.commit()
    print("\n" + "="*50)
    print("✓ Profile system migration completed successfully!")
    print("All existing data has been preserved.")
    print("="*50)
    
except sqlite3.Error as e:
    print(f"\n✗ Error during migration: {e}")
    conn.rollback()
    
finally:
    conn.close()
