import socket
import json
import threading
import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk
import base64
from io import BytesIO
import queue

class AUBoutiqueClient:
    def __init__(self, host, port):  # Make sure this line is properly indented
        self.host = host
        self.port = port
        self.socket = None
        self.username = None
        self.message_queue = queue.Queue()
        self.setup_gui()
        print(f"[CLIENT] Initialized with host={host}, port={port}")  # Debug print

    def setup_gui(self):
        """Initialize the GUI"""
        self.root = tk.Tk()
        self.root.title("AUBoutique")
        self.root.geometry("800x600")
        
        # Create main container
        self.main_frame = ttk.Frame(self.root, padding="10")
        self.main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        self.show_login_frame()
        
        # Start checking message queue
        self.check_message_queue()

    def show_login_frame(self):
        """Display login/register interface"""
        self.clear_main_frame()
        
        # Login frame
        login_frame = ttk.LabelFrame(self.main_frame, text="Login", padding="10")
        login_frame.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")
        
        ttk.Label(login_frame, text="Username:").grid(row=0, column=0, pady=5)
        self.username_entry = ttk.Entry(login_frame)
        self.username_entry.grid(row=0, column=1, pady=5)
        
        ttk.Label(login_frame, text="Password:").grid(row=1, column=0, pady=5)
        self.password_entry = ttk.Entry(login_frame, show="*")
        self.password_entry.grid(row=1, column=1, pady=5)
        
        ttk.Button(login_frame, text="Login", 
                  command=self.handle_login).grid(row=2, column=0, pady=10)
        ttk.Button(login_frame, text="Register", 
                  command=self.show_register_frame).grid(row=2, column=1, pady=10)

    def show_register_frame(self):
        """Display registration interface"""
        self.clear_main_frame()
        
        register_frame = ttk.LabelFrame(self.main_frame, text="Register", padding="10")
        register_frame.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")
        
        fields = [("Name:", "name"), ("Email:", "email"), 
                 ("Username:", "username"), ("Password:", "password")]
        self.register_entries = {}
        
        for i, (label, key) in enumerate(fields):
            ttk.Label(register_frame, text=label).grid(row=i, column=0, pady=5)
            entry = ttk.Entry(register_frame)
            entry.grid(row=i, column=1, pady=5)
            self.register_entries[key] = entry
        
        ttk.Button(register_frame, text="Register", 
                  command=self.handle_register).grid(row=len(fields), column=0, 
                                                   columnspan=2, pady=10)
        ttk.Button(register_frame, text="Back to Login", 
                  command=self.show_login_frame).grid(row=len(fields)+1, 
                                                    column=0, columnspan=2)

    def show_main_interface(self):
        """Display main marketplace interface"""
        self.clear_main_frame()
        
        # Create notebook for different sections
        notebook = ttk.Notebook(self.main_frame)
        notebook.grid(row=0, column=0, sticky="nsew")
        
        # Products tab
        products_frame = ttk.Frame(notebook, padding="10")
        notebook.add(products_frame, text="Browse Products")
        
        # Product listing
        self.products_tree = ttk.Treeview(products_frame, 
            columns=("ID", "Name", "Price", "Seller", "Description"),
            show="headings")
        
        for col in ("ID", "Name", "Price", "Seller", "Description"):
            self.products_tree.heading(col, text=col)
            self.products_tree.column(col, width=100)
        
        self.products_tree.grid(row=0, column=0, columnspan=2, sticky="nsew")
        
        # Buttons
        ttk.Button(products_frame, text="Refresh", 
                  command=self.refresh_products).grid(row=1, column=0, pady=5)
        ttk.Button(products_frame, text="Buy Selected", 
                  command=self.buy_product).grid(row=1, column=1, pady=5)
        
        # Sell tab
        sell_frame = ttk.Frame(notebook, padding="10")
        notebook.add(sell_frame, text="Sell Item")
        
        fields = [("Name:", "name"), ("Price:", "price"), 
                 ("Description:", "description")]
        self.sell_entries = {}
        
        for i, (label, key) in enumerate(fields):
            ttk.Label(sell_frame, text=label).grid(row=i, column=0, pady=5)
            entry = ttk.Entry(sell_frame)
            entry.grid(row=i, column=1, pady=5)
            self.sell_entries[key] = entry
        
        ttk.Button(sell_frame, text="Add Product", 
                  command=self.add_product).grid(row=len(fields), 
                                               column=0, columnspan=2, pady=10)
        
        # Chat tab
        chat_frame = ttk.Frame(notebook, padding="10")
        notebook.add(chat_frame, text="Chat")
        
        # Chat interface
        self.chat_text = tk.Text(chat_frame, height=15, width=50)
        self.chat_text.grid(row=0, column=0, columnspan=2, pady=5)
        
        ttk.Label(chat_frame, text="To:").grid(row=1, column=0)
        self.chat_recipient = ttk.Entry(chat_frame)
        self.chat_recipient.grid(row=1, column=1, pady=5)
        
        ttk.Label(chat_frame, text="Message:").grid(row=2, column=0)
        self.chat_message = ttk.Entry(chat_frame)
        self.chat_message.grid(row=2, column=1, pady=5)
        
        ttk.Button(chat_frame, text="Send", 
                  command=self.send_chat_message).grid(row=3, column=0, 
                                                     columnspan=2, pady=5)

    def clear_main_frame(self):
        """Clear all widgets from main frame"""
        for widget in self.main_frame.winfo_children():
            widget.destroy()

  

    def connect_to_server(self):
        """Establish connection to server"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.host, self.port))
            return True
        except Exception as e:
            messagebox.showerror("Connection Error", 
                               f"Could not connect to server: {str(e)}")
            return False

    def send_message(self, message):
        """Send message to server and get response"""
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                if not self.socket:
                    if not self.connect_to_server():
                        return None
                
                # Send message
                print(f"[CLIENT] Sending message attempt {retry_count + 1}")
                self.socket.send(json.dumps(message).encode('utf-8'))
                
                # Get response with timeout
                self.socket.settimeout(10.0)  # Increased timeout to 10 seconds
                response = self.socket.recv(4096).decode('utf-8')
                self.socket.settimeout(None)  # Reset timeout
                
                try:
                    return json.loads(response)
                except json.JSONDecodeError as e:
                    print(f"[CLIENT] Invalid JSON response: {response}")
                    return None
                
            except socket.timeout:
                print(f"[CLIENT] Timeout on attempt {retry_count + 1}")
                retry_count += 1
                if retry_count == max_retries:
                    print("[CLIENT] All retries failed")
                    return None
                    
            except Exception as e:
                print(f"[CLIENT] Communication error: {str(e)}")
                if retry_count == max_retries - 1:
                    messagebox.showerror("Communication Error", 
                                    f"Error communicating with server: {str(e)}")
                return None


    def send_chat_message(self):
        """Send a chat message"""
        print("[CLIENT] Attempting to send chat message")
        
        recipient = self.chat_recipient.get().strip()
        message_text = self.chat_message.get().strip()
        
        if not recipient or not message_text:
            messagebox.showerror("Error", "Please fill in both recipient and message")
            return
        
        if not self.username:
            messagebox.showerror("Error", "You must be logged in to send messages")
            return
        
        try:
            message = {
                "type": "chat",
                "from": self.username,
                "to": recipient,
                "message": message_text
            }
            
            print(f"[CLIENT] Sending chat message: {message}")
            response = self.send_message(message)
            print(f"[CLIENT] Server response: {response}")
            
            if response and response.get("status") == "success":
                # Show sent message in our window
                self.chat_text.insert(tk.END, 
                    f"You to {recipient}: {message_text}\n")
                self.chat_text.see(tk.END)
                
                # Clear message field but keep recipient
                self.chat_message.delete(0, tk.END)
            else:
                error_msg = response.get("message", "Failed to send message") if response else "No response from server"
                messagebox.showerror("Error", error_msg)
                
        except Exception as e:
            print(f"[CLIENT] Error sending chat message: {str(e)}")
            messagebox.showerror("Error", f"Failed to send message: {str(e)}")

    def receive_messages(self):
        """Background thread to receive incoming messages"""
        print("[CLIENT] Starting message receiver thread")
        
        while True:
            try:
                if not self.socket:
                    print("[CLIENT] Socket closed, stopping receiver")
                    break
                
                try:
                    self.socket.settimeout(0.1)  # Short timeout for checking
                    data = self.socket.recv(4096).decode('utf-8')
                    self.socket.settimeout(None)
                    
                    if not data:
                        print("[CLIENT] Connection closed by server")
                        break
                    
                    print(f"[CLIENT] Raw data received: {data}")
                    
                    try:
                        message = json.loads(data)
                        print(f"[CLIENT] Processed message: {message}")
                        
                        # Only queue chat messages
                        if isinstance(message, dict) and message.get("type") == "chat":
                            print(f"[CLIENT] Queuing chat message: {message}")
                            self.message_queue.put(message)
                            
                    except json.JSONDecodeError:
                        print(f"[CLIENT] Invalid JSON received: {data}")
                        continue
                        
                except socket.timeout:
                    continue
                
            except Exception as e:
                print(f"[CLIENT] Error in receive_messages: {str(e)}")
                break
        
        print("[CLIENT] Message receiver thread ended")

    def check_message_queue(self):
        """Process messages from the queue"""
        try:
            while True:
                try:
                    message = self.message_queue.get_nowait()
                    print(f"[CLIENT] Processing queued message: {message}")
                    
                    if isinstance(message, dict) and message.get("type") == "chat":
                        # Add message to chat window
                        self.chat_text.insert(tk.END,
                            f"{message['from']}: {message['message']}\n")
                        self.chat_text.see(tk.END)  # Auto-scroll to bottom
                        
                except queue.Empty:
                    break
                    
        except Exception as e:
            print(f"[CLIENT] Error processing message queue: {str(e)}")
            
        finally:
            # Schedule next check
            self.root.after(50, self.check_message_queue)  # Check more frequently

    def handle_login(self):
        """Process login attempt"""
        username = self.username_entry.get()
        password = self.password_entry.get()
        
        if not username or not password:
            messagebox.showerror("Error", "Please fill in all fields")
            return
        
        message = {
            "type": "login",
            "username": username,
            "password": password
        }
        
        response = self.send_message(message)
        if response and response["status"] == "success":
            self.username = username
            messagebox.showinfo("Success", "Login successful!")
            
            # Start receive thread before showing main interface
            self.receive_thread = threading.Thread(target=self.receive_messages)
            self.receive_thread.daemon = True
            self.receive_thread.start()
            
            # Show main interface
            self.root.after(100, self.show_main_interface)
        else:
            messagebox.showerror("Error", 
                response.get("message", "Login failed"))

    def handle_register(self):
        """Process registration attempt"""
        fields = {}
        for key, entry in self.register_entries.items():
            fields[key] = entry.get()
            if not fields[key]:
                messagebox.showerror("Error", "Please fill in all fields")
                return
        
        message = {
            "type": "register",
            **fields
        }
        
        response = self.send_message(message)
        if response and response["status"] == "success":
            messagebox.showinfo("Success", "Registration successful!")
            self.show_login_frame()
        else:
            messagebox.showerror("Error", 
                response.get("message", "Registration failed"))



    def refresh_products(self):
            """Update product listing"""
            try:
                message = {"type": "list_products"}
                response = self.send_message(message)
                
                if response and response["status"] == "success":
                    # Clear existing items
                    for item in self.products_tree.get_children():
                        self.products_tree.delete(item)
                    
                    # Add new items
                    for product in response["products"]:
                        self.products_tree.insert("", "end", values=(
                            product["id"],
                            product["name"],
                            f"${product['price']:.2f}",
                            product["seller"],
                            product["description"]
                        ))
                    return True
                else:
                    error_msg = response.get("message", "Failed to fetch products") if response else "No response from server"
                    messagebox.showerror("Error", error_msg)
                    return False
            except Exception as e:
                messagebox.showerror("Error", f"Failed to refresh products: {str(e)}")
                return False

    def buy_product(self):
        """Handle product purchase with improved error handling"""
        print("[CLIENT] Starting buy_product")
        
        if not self.username:
            messagebox.showerror("Error", "Please log in first")
            return
            
        selected = self.products_tree.selection()
        if not selected:
            messagebox.showerror("Error", "Please select a product to buy")
            return
        
        try:
            # Get product details
            product_values = self.products_tree.item(selected[0])["values"]
            if not product_values:
                messagebox.showerror("Error", "Invalid product selection")
                return
                
            product_id = product_values[0]
            product_name = product_values[1]
            product_seller = product_values[3]
            
            # Check if trying to buy own product
            if product_seller == self.username:
                messagebox.showerror("Error", "You cannot buy your own product")
                return
            
            # Confirm purchase
            if not messagebox.askyesno("Confirm Purchase", 
                                    f"Are you sure you want to buy {product_name}?"):
                return
            
            # Prepare message
            message = {
                "type": "buy_product",
                "product_id": product_id,
                "buyer": self.username
            }
            
            print(f"[CLIENT] Attempting to buy product {product_id}")
            
            # Disable the buy button temporarily
            buy_button = None
            for widget in self.products_tree.master.winfo_children():
                if isinstance(widget, ttk.Button) and widget["text"] == "Buy Selected":
                    buy_button = widget
                    buy_button["state"] = "disabled"
                    break
            
            try:
                # Send buy request
                response = self.send_message(message)
                print(f"[CLIENT] Buy response received: {response}")
                
                if response and response.get("status") == "success":
                    # Show success message
                    messagebox.showinfo("Success", response.get("message", "Purchase successful!"))
                    
                    # Refresh the product list
                    self.refresh_products()
                else:
                    error_msg = response.get("message", "Purchase failed") if response else "No response from server"
                    print(f"[CLIENT] Purchase error: {error_msg}")
                    messagebox.showerror("Error", error_msg)
            
            finally:
                # Re-enable the buy button
                if buy_button:
                    self.root.after(100, lambda: buy_button.configure(state="normal"))
                    
        except Exception as e:
            print(f"[CLIENT] Error in buy_product: {str(e)}")
            messagebox.showerror("Error", f"Failed to complete purchase: {str(e)}")
    


    def add_product(self):
        """Add new product with improved error handling"""
        print("[CLIENT] Starting add_product")
        
        if not self.username:
            messagebox.showerror("Error", "Please log in first")
            return
            
        try:
            # Validate fields
            fields = {}
            for key, entry in self.sell_entries.items():
                fields[key] = entry.get().strip()
                if not fields[key]:
                    print(f"[CLIENT] Missing field: {key}")
                    messagebox.showerror("Error", f"Please fill in the {key} field")
                    return
            
            try:
                fields["price"] = float(fields["price"])
                if fields["price"] <= 0:
                    print("[CLIENT] Invalid price (<=0)")
                    messagebox.showerror("Error", "Price must be greater than 0")
                    return
            except ValueError:
                print("[CLIENT] Invalid price format")
                messagebox.showerror("Error", "Price must be a valid number")
                return
            
            # Prepare message
            message = {
                "type": "add_product",
                "seller": self.username,
                "name": fields["name"],
                "price": fields["price"],
                "description": fields["description"],
                "image": ""
            }
            
            print(f"[CLIENT] Prepared message: {message}")
            
            # Disable the add product button temporarily
            add_button = None
            for widget in self.sell_entries["name"].master.winfo_children():
                if isinstance(widget, ttk.Button) and widget["text"] == "Add Product":
                    add_button = widget
                    add_button["state"] = "disabled"
                    break
            
            try:
                # Send message and get response
                response = self.send_message(message)
                
                if response and response.get("status") == "success":
                    # Clear entry fields
                    for entry in self.sell_entries.values():
                        entry.delete(0, tk.END)
                    
                    # Show success message
                    messagebox.showinfo("Success", "Product added successfully!")
                    
                    # Refresh products list
                    self.refresh_products()
                else:
                    error_msg = response.get("message", "Failed to add product") if response else "No response from server"
                    print(f"[CLIENT] Error: {error_msg}")
                    messagebox.showerror("Error", error_msg)
            
            finally:
                # Re-enable the add product button
                if add_button:
                    self.root.after(100, lambda: add_button.configure(state="normal"))
                
        except Exception as e:
            print(f"[CLIENT] Unexpected error in add_product: {str(e)}")
            messagebox.showerror("Error", f"Unexpected error: {str(e)}")

    def run(self):
        """Start the client application"""
        self.root.mainloop()


if __name__ == "__main__":
    import sys
    if len(sys.argv) != 3:
        print("Usage: python client.py <host> <port>")
        sys.exit(1)
    
    host = sys.argv[1]
    port = int(sys.argv[2])
    print(f"Starting client with host={host}, port={port}")  # Debug print
    client = AUBoutiqueClient(host, port)  # Remove keyword arguments
    client.run()