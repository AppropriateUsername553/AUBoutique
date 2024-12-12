# create_wishlist_table.py

import sqlite3
import os

DATABASE = 'auboutique.db'  # Ensure this path matches your project's database path

def create_wishlist_table():
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    
    # Create wishlist table
    c.execute('''
        CREATE TABLE IF NOT EXISTS wishlist (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_username TEXT NOT NULL,
            product_id INTEGER NOT NULL,
            added_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_username) REFERENCES users(username),
            FOREIGN KEY (product_id) REFERENCES products(id),
            UNIQUE(user_username, product_id)
        )
    ''')
    
    conn.commit()
    conn.close()
    print("Ensured 'wishlist' table exists.")

if __name__ == "__main__":
    if os.path.exists(DATABASE):
        create_wishlist_table()
    else:
        print(f"Database '{DATABASE}' does not exist. Please run the main application to create the database first.")
