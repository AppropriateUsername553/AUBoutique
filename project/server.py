import socket
import threading
import json
import sqlite3
from datetime import datetime
import base64


class AUBoutiqueServer:
    def __init__(self, port):
        self.host = 'localhost'
        self.port = port
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen()
        
        # Track online users and their sockets
        self.online_users = {}  # username -> socket
        self.socket_to_user = {}  # socket -> username
        
        # Initialize database
        self.init_database()
        
        print(f"Server started on port {port}")

    def init_database(self):
        conn = sqlite3.connect('auboutique.db')
        c = conn.cursor()
        
        # Create users table
        c.execute('''CREATE TABLE IF NOT EXISTS users
                    (username TEXT PRIMARY KEY,
                     password TEXT NOT NULL,
                     name TEXT NOT NULL,
                     email TEXT NOT NULL)''')
        
        # Create products table
        c.execute('''CREATE TABLE IF NOT EXISTS products
                    (id INTEGER PRIMARY KEY AUTOINCREMENT,
                     name TEXT NOT NULL,
                     description TEXT NOT NULL,
                     price REAL NOT NULL,
                     image BLOB,
                     seller TEXT NOT NULL,
                     buyer TEXT,
                     sold BOOLEAN DEFAULT 0,
                     FOREIGN KEY (seller) REFERENCES users(username))''')
        
        conn.commit()
        conn.close()

    def handle_client(self, client_socket, addr):
        """Handle individual client connections"""
        try:
            while True:
                data = client_socket.recv(4096).decode('utf-8')
                if not data:
                    break
                
                try:
                    message = json.loads(data)
                    response = self.process_message(message, client_socket)
                    client_socket.send(json.dumps(response).encode('utf-8'))
                except json.JSONDecodeError:
                    client_socket.send(json.dumps({
                        "status": "error",
                        "message": "Invalid JSON format"
                    }).encode('utf-8'))
        except Exception as e:
            print(f"Error handling client {addr}: {e}")
        finally:
            self.handle_client_disconnect(client_socket)
            client_socket.close()

    def process_message(self, message, client_socket):
        """Process incoming messages based on their type"""
        msg_type = message.get('type')
        
        if msg_type == 'register':
            return self.handle_registration(message)
        elif msg_type == 'login':
            return self.handle_login(message, client_socket)
        elif msg_type == 'list_products':
            return self.get_products()
        elif msg_type == 'add_product':
            return self.add_product(message)
        elif msg_type == 'buy_product':
            return self.buy_product(message)
        elif msg_type == 'chat':
            return self.relay_chat_message(message)
        elif msg_type == 'user_products':
            return self.get_user_products(message)
        else:
            return {"status": "error", "message": "Unknown message type"}

    def handle_registration(self, message):
        """Handle new user registration"""
        try:
            conn = sqlite3.connect('auboutique.db')
            c = conn.cursor()
            
            # Check if username exists
            c.execute('SELECT username FROM users WHERE username = ?', 
                     (message['username'],))
            if c.fetchone():
                return {"status": "error", "message": "Username already exists"}
            
            # Insert new user
            c.execute('INSERT INTO users (username, password, name, email) VALUES (?, ?, ?, ?)',
                     (message['username'], message['password'], 
                      message['name'], message['email']))
            
            conn.commit()
            return {"status": "success", "message": "Registration successful"}
        except sqlite3.Error as e:
            return {"status": "error", "message": str(e)}
        finally:
            conn.close()

    def handle_login(self, message, client_socket):
        """Handle user login"""
        try:
            conn = sqlite3.connect('auboutique.db')
            c = conn.cursor()
            
            c.execute('SELECT username FROM users WHERE username = ? AND password = ?',
                     (message['username'], message['password']))
            user = c.fetchone()
            
            if user:
                username = user[0]
                self.online_users[username] = client_socket
                self.socket_to_user[client_socket] = username
                return {"status": "success", "message": "Login successful"}
            else:
                return {"status": "error", "message": "Invalid credentials"}
        except sqlite3.Error as e:
            return {"status": "error", "message": str(e)}
        finally:
            conn.close()

    # Add these debugging prints to the server's add_product method:

    def add_product(self, message):
        """Add a new product to the marketplace"""
        print(f"[SERVER] Received add product request: {message}")
        
        try:
            # Input validation
            required_fields = ['name', 'description', 'price', 'seller']
            for field in required_fields:
                if field not in message:
                    print(f"[SERVER] Missing field: {field}")
                    return {"status": "error", "message": f"Missing required field: {field}"}
            
            print(f"[SERVER] All required fields present")
            
            # Use context manager for database connection
            with sqlite3.connect('auboutique.db', timeout=30.0) as conn:
                c = conn.cursor()
                
                try:
                    # Insert new product
                    c.execute('''INSERT INTO products 
                                (name, description, price, image, seller)
                                VALUES (?, ?, ?, ?, ?)''',
                            (message['name'], 
                            message['description'],
                            float(message['price']), 
                            message.get('image', ''),
                            message['seller']))
                    
                    conn.commit()
                    print(f"[SERVER] Product added successfully")
                    return {"status": "success", "message": "Product added successfully"}
                    
                except sqlite3.Error as e:
                    print(f"[SERVER] Database error: {str(e)}")
                    return {"status": "error", "message": f"Database error: {str(e)}"}
                    
        except Exception as e:
            print(f"[SERVER] Server error: {str(e)}")
            return {"status": "error", "message": f"Server error: {str(e)}"}




    def get_products(self):
        """Get all available products"""
        try:
            conn = sqlite3.connect('auboutique.db')
            c = conn.cursor()
            
            c.execute('''SELECT id, name, description, price, seller, sold 
                        FROM products WHERE sold = 0''')
            products = c.fetchall()
            
            product_list = [{
                "id": p[0],
                "name": p[1],
                "description": p[2],
                "price": p[3],
                "seller": p[4],
                "sold": p[5]
            } for p in products]
            
            return {
                "status": "success",
                "products": product_list
            }
        except sqlite3.Error as e:
            return {"status": "error", "message": str(e)}
        finally:
            conn.close()

    def buy_product(self, message):
        """Handle product purchase with improved error handling"""
        print(f"[SERVER] Processing buy request: {message}")
        
        try:
            # Validate required fields
            if 'product_id' not in message or 'buyer' not in message:
                return {"status": "error", "message": "Missing required fields"}
            
            with sqlite3.connect('auboutique.db', timeout=30.0) as conn:
                c = conn.cursor()
                
                # First check if product exists and is available
                c.execute('''SELECT seller, sold FROM products 
                            WHERE id = ?''', (message['product_id'],))
                result = c.fetchone()
                
                if not result:
                    return {"status": "error", "message": "Product not found"}
                    
                seller, sold = result
                
                # Check if product is already sold
                if sold:
                    return {"status": "error", "message": "Product is already sold"}
                    
                # Check if trying to buy own product
                if seller == message['buyer']:
                    return {"status": "error", "message": "Cannot buy your own product"}
                
                # Update product as sold
                c.execute('''UPDATE products 
                            SET sold = 1, buyer = ? 
                            WHERE id = ? AND sold = 0''',
                        (message['buyer'], message['product_id']))
                
                if c.rowcount > 0:
                    conn.commit()
                    print(f"[SERVER] Product {message['product_id']} sold to {message['buyer']}")
                    return {
                        "status": "success",
                        "message": "Purchase successful! Check your email for collection details."
                    }
                else:
                    return {"status": "error", "message": "Product no longer available"}
                    
        except sqlite3.Error as e:
            print(f"[SERVER] Database error in buy_product: {str(e)}")
            return {"status": "error", "message": f"Database error: {str(e)}"}
            
        except Exception as e:
            print(f"[SERVER] Error in buy_product: {str(e)}")
            return {"status": "error", "message": "Server error occurred"}

    def relay_chat_message(self, message):
        """Relay chat messages between users with improved handling"""
        print(f"[SERVER] Processing chat message: {message}")
        
        try:
            # Validate message format
            required_fields = ['from', 'to', 'message', 'type']
            for field in required_fields:
                if field not in message:
                    print(f"[SERVER] Missing field in message: {field}")
                    return {"status": "error", "message": f"Missing required field: {field}"}
            
            sender = message['from']
            recipient = message['to']
            
            print(f"[SERVER] Attempting to send message from {sender} to {recipient}")
            
            # Validate recipient exists
            with sqlite3.connect('auboutique.db') as conn:
                c = conn.cursor()
                c.execute('SELECT username FROM users WHERE username = ?', (recipient,))
                if not c.fetchone():
                    print(f"[SERVER] Recipient {recipient} does not exist")
                    return {"status": "error", "message": "Recipient does not exist"}
            
            # Check if recipient is online
            if recipient in self.online_users:
                try:
                    recipient_socket = self.online_users[recipient]
                    
                    # Create chat message for recipient
                    chat_message = {
                        "type": "chat",
                        "from": sender,
                        "message": message['message'],
                        "timestamp": datetime.now().strftime("%H:%M:%S")
                    }
                    
                    # Send to recipient
                    encoded_message = json.dumps(chat_message).encode('utf-8')
                    print(f"[SERVER] Sending to {recipient}: {chat_message}")
                    recipient_socket.send(encoded_message)
                    
                    print(f"[SERVER] Message successfully sent to {recipient}")
                    return {"status": "success", "message": "Message sent successfully"}
                    
                except Exception as e:
                    print(f"[SERVER] Error sending to {recipient}: {str(e)}")
                    self.handle_client_disconnect(recipient_socket)
                    return {"status": "error", "message": "Failed to deliver message"}
            else:
                print(f"[SERVER] Recipient {recipient} is offline")
                return {"status": "error", "message": "User is offline"}
                
        except Exception as e:
            print(f"[SERVER] Error in relay_chat_message: {str(e)}")
            return {"status": "error", "message": "Server error occurred"}

    def handle_client_disconnect(self, client_socket):
        """Clean up when a client disconnects"""
        try:
            if client_socket in self.socket_to_user:
                username = self.socket_to_user[client_socket]
                print(f"[SERVER] Client disconnected: {username}")
                
                # Remove from both dictionaries
                if username in self.online_users:
                    del self.online_users[username]
                del self.socket_to_user[client_socket]
                
        except Exception as e:
            print(f"[SERVER] Error in handle_client_disconnect: {str(e)}")


    def run(self):
        """Main server loop"""
        try:
            while True:
                client_socket, addr = self.server_socket.accept()
                print(f"New connection from {addr}")
                client_thread = threading.Thread(
                    target=self.handle_client,
                    args=(client_socket, addr)
                )
                client_thread.start()
        except KeyboardInterrupt:
            print("\nShutting down server...")
        finally:
            self.server_socket.close()

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        print("Usage: python server.py <port>")
        sys.exit(1)
    
    port = int(sys.argv[1])
    server = AUBoutiqueServer(port)
    server.run()


