# AUBoutique

**AUBoutique** is an online marketplace designed to facilitate seamless transactions between buyers and sellers. Built with a robust client-server architecture using Flask and SQLite, AUBoutique offers features such as user authentication, product management, real-time chat, and an optional wishlist system.

## Features

- **User Authentication:** Secure registration and login with hashed passwords.
- **Product Management:** List, update, purchase, and rate products.
- **Real-time Chat:** Communicate instantly with other users.
- **Wishlist (Optional):** Add and manage favorite products for future reference.

## Technologies Used

- **Backend:** Flask, SQLite
- **Frontend:** HTML, CSS (Bootstrap), JavaScript
- **Version Control:** Git, GitHub
- **Others:** AJAX for asynchronous operations

## Installation

1. **Clone the Repository:**
    ```bash
    git clone https://github.com/AppropriateUsername553/AUBoutique.git
    cd AUBoutique
    ```

2. **Create a Virtual Environment:**
    ```bash
    python3 -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

3. **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4. **Initialize the Database:**
    ```bash
    python app.py
    ```
    *This will create the `auboutique.db` with all necessary tables.*

## Usage

1. **Run the Application:**
    ```bash
    python app.py
    ```
    *Access the application at `http://localhost:5000`.*

2. **Register a New User:**
    - Navigate to the **Register** page.
    - Fill in the required details and submit.

3. **Login:**
    - Use your credentials to log in.
  
4. **Explore Features:**
    - **Marketplace:** Browse and search for products.
    - **Add Products:** List new products for sale.
    - **Chat:** Communicate with other users in real-time.
    - **Wishlist:** (Optional) Add products to your wishlist.
