# AUBoutique - Online Marketplace Project

## Overview
AUBoutique is an online marketplace platform with a client-server architecture using TCP/IP sockets for communication. It allows multiple clients to connect, browse, buy, and sell products, and includes a real-time chat feature.

## Instructions for Running the Project

1. **Clone the Repository**:
   ```bash
   git clone <https://github.com/AppropriateUsername553/AUBoutique.git>
   cd <repository_folder>
   
2. Start the Server:

Open a terminal in the project directory.
Run:
python server.py 5000

The server will initialize a SQLite database and start on port 5000.

3. Launch a Client:

Open a new terminal for each client.
Run:
python client.py localhost 5000
A GUI window will appear for each client instance.

4. Testing the Project:

Register and log in to access features like adding products, browsing, purchasing, and using real-time chat between clients.

Dependencies :
- Python 3.x
- Tkinter (for the GUI)
- SQLite3 (for database management)
