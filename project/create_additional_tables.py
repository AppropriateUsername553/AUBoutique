# create_additional_tables.py

import sqlite3
import os

DATABASE = 'auboutique.db'  # Update the path if your database is located elsewhere

def add_last_active_and_status_columns():
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    
    # Add last_active column if it doesn't exist
    c.execute("PRAGMA table_info(users)")
    columns = [info[1] for info in c.fetchall()]
    if 'last_active' not in columns:
        c.execute('ALTER TABLE users ADD COLUMN last_active DATETIME')
        c.execute('UPDATE users SET last_active = CURRENT_TIMESTAMP')
        print("Added 'last_active' column to 'users' table and set default values.")
    else:
        print("'last_active' column already exists in 'users' table.")
    
    # Add status column to chats table if it doesn't exist
    c.execute("PRAGMA table_info(chats)")
    columns = [info[1] for info in c.fetchall()]
    if 'status' not in columns:
        c.execute('ALTER TABLE chats ADD COLUMN status TEXT DEFAULT "active"')
        print("Added 'status' column to 'chats' table with default 'active'.")
    else:
        print("'status' column already exists in 'chats' table.")
    
    conn.commit()
    conn.close()
    print("Ensured 'last_active' and 'status' columns exist.")

if __name__ == "__main__":
    if os.path.exists(DATABASE):
        add_last_active_and_status_columns()
    else:
        print(f"Database '{DATABASE}' does not exist. Please run the main application to create the database first.")
