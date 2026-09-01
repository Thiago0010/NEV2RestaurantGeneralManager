import sqlite3

DB_PATH = 'C:/Users/Thiago/OneDrive/Desktop/Restaurant-NEV2-MANAGER/backend/restaurant_nev2.db'

def migrate():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    print("Starting Financials migration...")

    # 1. Add cost_price to products
    try:
        cursor.execute("ALTER TABLE products ADD COLUMN cost_price REAL DEFAULT 0")
        print("Added 'cost_price' column to products.")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e):
            print("'cost_price' column already exists, skipping.")
        else:
            print(f"Error adding 'cost_price' column: {e}")

    # 2. Create expenses table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS expenses (
            id BLOB PRIMARY KEY,
            restaurant_id BLOB NOT NULL,
            description VARCHAR(255) NOT NULL,
            amount REAL NOT NULL,
            category VARCHAR(50) NOT NULL,
            date DATETIME NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(restaurant_id) REFERENCES restaurants(id)
        )
    ''')
    print("Created expenses table.")

    conn.commit()
    conn.close()
    print("Financials migration complete.")

if __name__ == "__main__":
    migrate()
