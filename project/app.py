# app.py

from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
import os
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Replace with a strong secret key

DATABASE = 'auboutique.db'

def init_database():
    if not os.path.exists(DATABASE):
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()

        # Create users table
        c.execute('''CREATE TABLE IF NOT EXISTS users
                    (username TEXT PRIMARY KEY,
                     password TEXT NOT NULL,
                     name TEXT NOT NULL,
                     email TEXT NOT NULL,
                     last_active DATETIME DEFAULT CURRENT_TIMESTAMP)''')

        # Create products table
        c.execute('''CREATE TABLE IF NOT EXISTS products
                    (id INTEGER PRIMARY KEY AUTOINCREMENT,
                     name TEXT NOT NULL,
                     description TEXT NOT NULL,
                     price REAL NOT NULL,
                     currency TEXT NOT NULL,
                     image TEXT,
                     seller TEXT NOT NULL,
                     buyer TEXT,
                     sold BOOLEAN DEFAULT 0,
                     quantity INTEGER DEFAULT 1,
                     category TEXT,
                     FOREIGN KEY (seller) REFERENCES users(username))''')

        # Create ratings table
        c.execute('''CREATE TABLE IF NOT EXISTS ratings
                    (id INTEGER PRIMARY KEY AUTOINCREMENT,
                     product_id INTEGER,
                     rating INTEGER,
                     FOREIGN KEY (product_id) REFERENCES products(id))''')

        # Create chat_requests table
        c.execute('''CREATE TABLE IF NOT EXISTS chat_requests
                    (id INTEGER PRIMARY KEY AUTOINCREMENT,
                     from_user TEXT NOT NULL,
                     to_user TEXT NOT NULL,
                     status TEXT DEFAULT 'pending',
                     timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                     FOREIGN KEY (from_user) REFERENCES users(username),
                     FOREIGN KEY (to_user) REFERENCES users(username))''')

        # Create chats table
        c.execute('''CREATE TABLE IF NOT EXISTS chats
                    (id INTEGER PRIMARY KEY AUTOINCREMENT,
                     user1 TEXT NOT NULL,
                     user2 TEXT NOT NULL,
                     status TEXT DEFAULT 'active',
                     FOREIGN KEY (user1) REFERENCES users(username),
                     FOREIGN KEY (user2) REFERENCES users(username))''')

        # Create messages table
        c.execute('''CREATE TABLE IF NOT EXISTS messages
                    (id INTEGER PRIMARY KEY AUTOINCREMENT,
                     chat_id INTEGER NOT NULL,
                     sender TEXT NOT NULL,
                     content TEXT NOT NULL,
                     timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                     FOREIGN KEY (chat_id) REFERENCES chats(id),
                     FOREIGN KEY (sender) REFERENCES users(username))''')

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
        print("[DB] Database initialized with all tables, including wishlist.")
    else:
        print("[DB] Database already exists.")

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

@app.before_request
def update_last_active():
    if 'username' in session:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute('UPDATE users SET last_active = CURRENT_TIMESTAMP WHERE username = ?', (session['username'],))
        conn.commit()
        conn.close()

@app.route('/')
def home():
    if 'username' in session:
        return redirect(url_for('marketplace'))
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name'].strip()
        email = request.form['email'].strip()
        username = request.form['username'].strip()
        password = request.form['password'].strip()

        if not name or not email or not username or not password:
            flash("Please fill in all fields.", "danger")
            return render_template('register.html')

        hashed_password = generate_password_hash(password)

        conn = get_db_connection()
        c = conn.cursor()
        try:
            c.execute('INSERT INTO users (username, password, name, email) VALUES (?, ?, ?, ?)',
                      (username, hashed_password, name, email))
            conn.commit()
            flash("Registration successful! Please log in.", "success")
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash("Username already exists.", "danger")
            return render_template('register.html')
        finally:
            conn.close()

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password'].strip()

        if not username or not password:
            flash("Please fill in all fields.", "danger")
            return render_template('login.html')

        conn = get_db_connection()
        c = conn.cursor()
        c.execute('SELECT * FROM users WHERE username = ?', (username,))
        user = c.fetchone()
        conn.close()

        if user and check_password_hash(user['password'], password):
            session['username'] = username
            flash("Login successful!", "success")
            return redirect(url_for('marketplace'))
        else:
            flash("Invalid credentials.", "danger")
            return render_template('login.html')

    return render_template('login.html')

@app.route('/logout')
def logout():
    if 'username' in session:
        username = session['username']
        conn = get_db_connection()
        c = conn.cursor()
        # End all active chats involving the user
        c.execute('UPDATE chats SET status = "ended" WHERE user1 = ? OR user2 = ?', (username, username))
        # Set last_active to a past time to indicate offline
        c.execute('UPDATE users SET last_active = "1970-01-01 00:00:00" WHERE username = ?', (username,))
        conn.commit()
        conn.close()
        session.pop('username', None)
        flash("Logged out and all active chats ended.", "info")
    return redirect(url_for('login'))

@app.route('/marketplace', methods=['GET'])
def marketplace():
    if 'username' not in session:
        return redirect(url_for('login'))

    currency = request.args.get('currency', 'USD')
    search_query = request.args.get('search', '')

    conn = get_db_connection()
    c = conn.cursor()

    if search_query:
        c.execute('''SELECT * FROM products 
                     WHERE sold = 0 
                     AND (name LIKE ? OR description LIKE ? OR category LIKE ?)''',
                  (f'%{search_query}%', f'%{search_query}%', f'%{search_query}%'))
    else:
        c.execute('SELECT * FROM products WHERE sold = 0')

    products = c.fetchall()

    product_list = []
    for p in products:
        product_id = p['id']
        c.execute('SELECT AVG(rating) as avg_rating FROM ratings WHERE product_id = ?', (product_id,))
        avg_rating = c.fetchone()['avg_rating']
        avg_rating = round(avg_rating, 2) if avg_rating else "No ratings"

        # Currency conversion
        converted_price = convert_currency(p['price'], p['currency'], currency)

        product_list.append({
            "id": product_id,
            "name": p['name'],
            "description": p['description'],
            "price": f"{currency} {converted_price:.2f}",
            "original_currency": p['currency'],
            "seller": p['seller'],
            "quantity": p['quantity'],
            "category": p['category'],
            "average_rating": avg_rating
        })

    conn.close()
    return render_template('marketplace.html', products=product_list, currency=currency, search=search_query)

@app.route('/add_product', methods=['GET', 'POST'])
def add_product():
    if 'username' not in session:
        flash("Please log in to add products.", "danger")
        return redirect(url_for('login'))

    if request.method == 'POST':
        name = request.form['name'].strip()
        price = request.form['price'].strip()
        currency = request.form['currency']
        quantity = request.form['quantity']
        category = request.form['category'].strip()
        description = request.form['description'].strip()
        image = request.form.get('image', '')  # For simplicity, handling image as a URL or base64 string

        if not name or not price or not category or not description:
            flash("Please fill in all required fields.", "danger")
            return render_template('add_product.html')

        try:
            price = float(price)
            quantity = int(quantity)
            if price <= 0 or quantity <= 0:
                flash("Price and quantity must be greater than 0.", "danger")
                return render_template('add_product.html')
        except ValueError:
            flash("Invalid price or quantity format.", "danger")
            return render_template('add_product.html')

        conn = get_db_connection()
        c = conn.cursor()
        try:
            c.execute('''INSERT INTO products 
                         (name, description, price, currency, image, seller, quantity, category, sold)
                         VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0)''',
                      (name, description, price, currency, image, session['username'], quantity, category))
            conn.commit()
            flash("Product added successfully.", "success")
            return redirect(url_for('marketplace'))
        except sqlite3.Error as e:
            flash(str(e), "danger")
            return render_template('add_product.html')
        finally:
            conn.close()

    return render_template('add_product.html')

@app.route('/buy_product/<int:product_id>', methods=['POST'])
def buy_product(product_id):
    if 'username' not in session:
        flash("Please log in to buy products.", "danger")
        return redirect(url_for('login'))

    buyer = session['username']
    conn = get_db_connection()
    c = conn.cursor()
    try:
        c.execute('SELECT seller, sold, quantity FROM products WHERE id = ?', (product_id,))
        result = c.fetchone()

        if not result:
            flash("Product not found.", "danger")
            return redirect(url_for('marketplace'))

        seller, sold, quantity = result['seller'], result['sold'], result['quantity']

        if sold or quantity <= 0:
            flash("Product is not available.", "danger")
            return redirect(url_for('marketplace'))

        if seller == buyer:
            flash("Cannot buy your own product.", "danger")
            return redirect(url_for('marketplace'))

        new_quantity = quantity - 1
        if new_quantity == 0:
            c.execute('''UPDATE products 
                         SET sold = 1, buyer = ?, quantity = ?
                         WHERE id = ?''',
                      (buyer, new_quantity, product_id))
        else:
            c.execute('''UPDATE products 
                         SET buyer = ?, quantity = ?
                         WHERE id = ?''',
                      (buyer, new_quantity, product_id))

        if c.rowcount > 0:
            conn.commit()
            flash("Purchase successful! Check your email for collection details.", "success")
        else:
            flash("Product no longer available.", "danger")
    except sqlite3.Error as e:
        flash(f"Database error: {str(e)}", "danger")
    finally:
        conn.close()

    return redirect(url_for('marketplace'))

@app.route('/rate_product/<int:product_id>', methods=['POST'])
def rate_product(product_id):
    if 'username' not in session:
        flash("Please log in to rate products.", "danger")
        return redirect(url_for('login'))

    rating = request.form.get('rating')
    username = session['username']

    if not rating:
        flash("Missing rating value.", "danger")
        return redirect(url_for('marketplace'))

    try:
        rating = int(rating)
        if rating < 1 or rating > 5:
            flash("Rating must be between 1 and 5.", "danger")
            return redirect(url_for('marketplace'))
    except ValueError:
        flash("Invalid rating value.", "danger")
        return redirect(url_for('marketplace'))

    conn = get_db_connection()
    c = conn.cursor()
    try:
        c.execute('SELECT id FROM products WHERE id = ?', (product_id,))
        if not c.fetchone():
            flash("Product not found.", "danger")
            return redirect(url_for('marketplace'))

        c.execute('INSERT INTO ratings (product_id, rating) VALUES (?, ?)', (product_id, rating))
        conn.commit()
        flash("Rating submitted successfully.", "success")
    except sqlite3.Error as e:
        flash(f"Database error: {str(e)}", "danger")
    finally:
        conn.close()

    return redirect(url_for('marketplace'))

# Wishlist Routes

@app.route('/add_to_wishlist/<int:product_id>', methods=['POST'])
def add_to_wishlist(product_id):
    if 'username' not in session:
        flash("Please log in to add products to your wishlist.", "danger")
        return redirect(url_for('login'))
    
    username = session['username']
    conn = get_db_connection()
    c = conn.cursor()
    
    try:
        # Check if product exists and is not already in wishlist
        c.execute('SELECT * FROM products WHERE id = ?', (product_id,))
        product = c.fetchone()
        if not product:
            flash("Product does not exist.", "danger")
            return redirect(url_for('marketplace'))
        
        c.execute('INSERT INTO wishlist (user_username, product_id) VALUES (?, ?)', (username, product_id))
        conn.commit()
        flash("Product added to your wishlist.", "success")
    except sqlite3.IntegrityError:
        flash("Product is already in your wishlist.", "info")
    finally:
        conn.close()
    
    return redirect(url_for('marketplace'))

@app.route('/wishlist')
def view_wishlist():
    if 'username' not in session:
        flash("Please log in to view your wishlist.", "danger")
        return redirect(url_for('login'))
    
    username = session['username']
    conn = get_db_connection()
    c = conn.cursor()
    
    c.execute('''
        SELECT products.*, ratings.avg_rating FROM products
        JOIN wishlist ON products.id = wishlist.product_id
        LEFT JOIN (
            SELECT product_id, AVG(rating) as avg_rating FROM ratings GROUP BY product_id
        ) as ratings ON products.id = ratings.product_id
        WHERE wishlist.user_username = ?
    ''', (username,))
    
    wishlist_items = c.fetchall()
    conn.close()
    
    rates = {
        "USD": 1.0,
        "EUR": 0.85,
        "GBP": 0.75,
        "JPY": 110.0
    }
    
    return render_template('wishlist.html', wishlist_items=wishlist_items, rates=rates)

@app.route('/remove_from_wishlist/<int:product_id>', methods=['POST'])
def remove_from_wishlist(product_id):
    if 'username' not in session:
        flash("Please log in to modify your wishlist.", "danger")
        return redirect(url_for('login'))
    
    username = session['username']
    conn = get_db_connection()
    c = conn.cursor()
    
    c.execute('DELETE FROM wishlist WHERE user_username = ? AND product_id = ?', (username, product_id))
    conn.commit()
    conn.close()
    
    flash("Product removed from your wishlist.", "info")
    return redirect(url_for('view_wishlist'))

# Chat Functionality Routes

@app.route('/users')
def users():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    current_user = session['username']
    threshold = datetime.utcnow() - timedelta(minutes=5)  # Users active in last 5 minutes
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''
        SELECT username, name FROM users 
        WHERE username != ? AND last_active >= ?
    ''', (current_user, threshold.strftime('%Y-%m-%d %H:%M:%S')))
    online_users = c.fetchall()
    conn.close()
    return render_template('users.html', users=online_users)

@app.route('/active_chats')
def active_chats():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    current_user = session['username']
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''
        SELECT * FROM chats
        WHERE (user1 = ? OR user2 = ?) AND status = "active"
    ''', (current_user, current_user))
    chats = c.fetchall()
    conn.close()
    return render_template('active_chats.html', chats=chats)

@app.route('/start_chat/<to_username>', methods=['POST'])
def start_chat(to_username):
    if 'username' not in session:
        return redirect(url_for('login'))

    from_username = session['username']
    if from_username == to_username:
        flash("You cannot start a chat with yourself.", "danger")
        return redirect(url_for('users'))

    conn = get_db_connection()
    c = conn.cursor()

    # Check if a chat already exists and is active
    c.execute('''SELECT chats.id FROM chats
                 WHERE ((user1 = ? AND user2 = ?) OR (user1 = ? AND user2 = ?))
                 AND status = "active"''',
              (from_username, to_username, to_username, from_username))
    chat = c.fetchone()

    if chat:
        chat_id = chat['id']
        flash("Active chat already exists.", "info")
        conn.close()
        return redirect(url_for('chat_room', chat_id=chat_id))

    # Check if a pending chat request exists
    c.execute('''SELECT * FROM chat_requests
                 WHERE from_user = ? AND to_user = ? AND status = "pending"''',
              (from_username, to_username))
    existing_request = c.fetchone()

    if existing_request:
        flash("Chat request already sent.", "info")
        conn.close()
        return redirect(url_for('users'))

    # Create a new chat request
    c.execute('''INSERT INTO chat_requests (from_user, to_user)
                 VALUES (?, ?)''',
              (from_username, to_username))
    conn.commit()
    conn.close()

    flash("Chat request sent.", "success")
    return redirect(url_for('users'))

@app.route('/end_chat/<int:chat_id>', methods=['POST'])
def end_chat(chat_id):
    if 'username' not in session:
        return redirect(url_for('login'))

    username = session['username']
    conn = get_db_connection()
    c = conn.cursor()

    # Verify chat exists and user is a participant
    c.execute('SELECT * FROM chats WHERE id = ? AND (user1 = ? OR user2 = ?)', (chat_id, username, username))
    chat = c.fetchone()

    if not chat or chat['status'] != 'active':
        flash("Chat not found or already ended.", "danger")
        conn.close()
        return redirect(url_for('active_chats'))

    # End the chat by updating its status
    c.execute('UPDATE chats SET status = "ended" WHERE id = ?', (chat_id,))
    conn.commit()
    conn.close()

    flash("Chat ended successfully.", "info")
    return redirect(url_for('active_chats'))

@app.route('/chat_requests')
def chat_requests():
    if 'username' not in session:
        return redirect(url_for('login'))

    username = session['username']
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM chat_requests WHERE to_user = ? AND status = "pending"', (username,))
    requests = c.fetchall()
    conn.close()
    return render_template('chat_requests.html', requests=requests)

@app.route('/accept_chat/<int:request_id>', methods=['POST'])
def accept_chat(request_id):
    if 'username' not in session:
        return redirect(url_for('login'))

    username = session['username']
    conn = get_db_connection()
    c = conn.cursor()

    # Retrieve the chat request
    c.execute('SELECT * FROM chat_requests WHERE id = ? AND to_user = ?', (request_id, username))
    chat_request = c.fetchone()

    if not chat_request:
        flash("Chat request not found.", "danger")
        conn.close()
        return redirect(url_for('chat_requests'))

    # Update the chat request status to 'accepted'
    c.execute('UPDATE chat_requests SET status = "accepted" WHERE id = ?', (request_id,))

    # Create a new chat
    from_user = chat_request['from_user']
    to_user = chat_request['to_user']
    c.execute('INSERT INTO chats (user1, user2) VALUES (?, ?)', (from_user, to_user))
    chat_id = c.lastrowid

    conn.commit()
    conn.close()

    flash("Chat request accepted.", "success")
    return redirect(url_for('chat_room', chat_id=chat_id))

@app.route('/decline_chat/<int:request_id>', methods=['POST'])
def decline_chat(request_id):
    if 'username' not in session:
        return redirect(url_for('login'))

    username = session['username']
    conn = get_db_connection()
    c = conn.cursor()

    # Retrieve the chat request
    c.execute('SELECT * FROM chat_requests WHERE id = ? AND to_user = ?', (request_id, username))
    chat_request = c.fetchone()

    if not chat_request:
        flash("Chat request not found.", "danger")
        conn.close()
        return redirect(url_for('chat_requests'))

    # Update the chat request status to 'declined'
    c.execute('UPDATE chat_requests SET status = "declined" WHERE id = ?', (request_id,))

    conn.commit()
    conn.close()

    flash("Chat request declined.", "info")
    return redirect(url_for('chat_requests'))

@app.route('/chat_room/<int:chat_id>')
def chat_room(chat_id):
    if 'username' not in session:
        return redirect(url_for('login'))

    username = session['username']
    conn = get_db_connection()
    c = conn.cursor()

    # Retrieve the chat
    c.execute('SELECT * FROM chats WHERE id = ?', (chat_id,))
    chat = c.fetchone()

    if not chat:
        flash("Chat not found.", "danger")
        conn.close()
        return redirect(url_for('marketplace'))

    if username not in [chat['user1'], chat['user2']]:
        flash("You are not a participant of this chat.", "danger")
        conn.close()
        return redirect(url_for('marketplace'))

    if chat['status'] != 'active':
        flash("This chat has been ended.", "info")
        conn.close()
        return redirect(url_for('active_chats'))

    # Retrieve messages
    c.execute('SELECT * FROM messages WHERE chat_id = ? ORDER BY timestamp ASC', (chat_id,))
    messages = c.fetchall()
    conn.close()

    other_user = chat['user2'] if chat['user1'] == username else chat['user1']

    return render_template('chat_room.html', chat_id=chat_id, messages=messages, other_user=other_user)

@app.route('/send_message/<int:chat_id>', methods=['POST'])
def send_message(chat_id):
    if 'username' not in session:
        return jsonify({"status": "error", "message": "Unauthorized"}), 401

    username = session['username']
    content = request.form.get('message', '').strip()

    if not content:
        return jsonify({"status": "error", "message": "Empty message"}), 400

    conn = get_db_connection()
    c = conn.cursor()

    # Verify chat exists, is active, and user is a participant
    c.execute('SELECT * FROM chats WHERE id = ? AND status = "active"', (chat_id,))
    chat = c.fetchone()

    if not chat or username not in [chat['user1'], chat['user2']]:
        conn.close()
        return jsonify({"status": "error", "message": "Chat not found or unauthorized"}), 404

    # Insert the message
    c.execute('''INSERT INTO messages (chat_id, sender, content)
                 VALUES (?, ?, ?)''',
              (chat_id, username, content))
    conn.commit()
    conn.close()

    return jsonify({"status": "success", "message": "Message sent"}), 200

@app.route('/get_messages/<int:chat_id>')
def get_messages(chat_id):
    if 'username' not in session:
        return jsonify({"status": "error", "message": "Unauthorized"}), 401

    username = session['username']
    conn = get_db_connection()
    c = conn.cursor()

    # Verify chat exists, is active, and user is a participant
    c.execute('SELECT * FROM chats WHERE id = ? AND status = "active"', (chat_id,))
    chat = c.fetchone()

    if not chat or username not in [chat['user1'], chat['user2']]:
        conn.close()
        return jsonify({"status": "error", "message": "Chat not found or unauthorized"}), 404

    # Retrieve messages
    c.execute('SELECT * FROM messages WHERE chat_id = ? ORDER BY timestamp ASC', (chat_id,))
    messages = c.fetchall()
    conn.close()

    messages_list = []
    for msg in messages:
        messages_list.append({
            "sender": msg['sender'],
            "content": msg['content'],
            "timestamp": msg['timestamp']
        })

    return jsonify({"status": "success", "messages": messages_list}), 200

@app.route('/ping', methods=['POST'])
def ping():
    if 'username' in session:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute('UPDATE users SET last_active = CURRENT_TIMESTAMP WHERE username = ?', (session['username'],))
        conn.commit()
        conn.close()
    return jsonify({"status": "success"}), 200

def convert_currency(amount, from_currency, to_currency):
    rates = {
        "USD": 1.0,
        "EUR": 0.85,
        "GBP": 0.75,
        "JPY": 110.0
    }
    try:
        usd_amount = amount / rates[from_currency]
        converted_amount = usd_amount * rates[to_currency]
        return converted_amount
    except KeyError:
        return amount

if __name__ == '__main__':
    init_database()
    app.run(host='0.0.0.0', port=5000, debug=True)
