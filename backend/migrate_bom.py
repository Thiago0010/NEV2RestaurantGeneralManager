import sqlite3
import uuid

DB_PATH = 'C:/Users/Thiago/OneDrive/Desktop/Restaurant-NEV2-MANAGER/backend/restaurant_nev2.db'

def migrate():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    print("Starting BOM migration...")

    # 1. Add 'unit' column to products
    try:
        cursor.execute("ALTER TABLE products ADD COLUMN unit TEXT DEFAULT 'unit'")
        print("Added 'unit' column to products.")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e):
            print("'unit' column already exists, skipping.")
        else:
            print(f"Error adding 'unit' column: {e}")

    # 2. Create product_recipes table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS product_recipes (
            id BLOB PRIMARY KEY,
            product_id BLOB NOT NULL,
            ingredient_id BLOB NOT NULL,
            quantity REAL NOT NULL,
            restaurant_id BLOB NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(product_id) REFERENCES products(id),
            FOREIGN KEY(ingredient_id) REFERENCES products(id),
            FOREIGN KEY(restaurant_id) REFERENCES restaurants(id)
        )
    ''')
    print("Created product_recipes table.")

    conn.commit()
    conn.close()
    print("BOM migration complete.")

if __name__ == "__main__":
    migrate()
