import sqlite3
import uuid

DB_PATH = 'C:/Users/Thiago/OneDrive/Desktop/Restaurant-NEV2-MANAGER/backend/restaurant_nev2.db'

def migrate():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 1. Update Product table
    cursor.execute("PRAGMA table_info(products)")
    cols = [col[1] for col in cursor.fetchall()]
    if 'stock_quantity' not in cols:
        print("Adding stock_quantity to products...")
        cursor.execute("ALTER TABLE products ADD COLUMN stock_quantity INTEGER DEFAULT 0 NOT NULL")

    # 2. Create InventoryMovement table
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='inventory_movements'")
    if not cursor.fetchone():
        print("Creating inventory_movements table...")
        cursor.execute('''
            CREATE TABLE inventory_movements (
                id BLOB PRIMARY KEY,
                product_id BLOB NOT NULL,
                restaurant_id BLOB NOT NULL,
                quantity INTEGER NOT NULL,
                movement_type VARCHAR(20) NOT NULL,
                reason VARCHAR(255),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(product_id) REFERENCES products(id),
                FOREIGN KEY(restaurant_id) REFERENCES restaurants(id)
            )
        ''')

    conn.commit()
    conn.close()
    print("Inventory migration complete.")

if __name__ == "__main__":
    migrate()
