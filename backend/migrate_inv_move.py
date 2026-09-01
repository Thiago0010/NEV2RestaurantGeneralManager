import sqlite3

DB_PATH = 'C:/Users/Thiago/OneDrive/Desktop/Restaurant-NEV2-MANAGER/backend/restaurant_nev2.db'

def migrate():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    print("Starting InventoryMovement migration...")

    # Change quantity to REAL (equivalent to Numeric/float)
    # SQLite doesn't support ALTER COLUMN. We must recreate the table.

    cursor.execute("CREATE TABLE inventory_movements_new (id BLOB PRIMARY KEY, product_id BLOB NOT NULL, restaurant_id BLOB NOT NULL, quantity REAL NOT NULL, movement_type VARCHAR(20) NOT NULL, reason TEXT, created_at DATETIME DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY(product_id) REFERENCES products(id), FOREIGN KEY(restaurant_id) REFERENCES restaurants(id))")

    cursor.execute("INSERT INTO inventory_movements_new SELECT * FROM inventory_movements")

    cursor.execute("DROP TABLE inventory_movements")
    cursor.execute("ALTER TABLE inventory_movements_new RENAME TO inventory_movements")

    conn.commit()
    conn.close()
    print("InventoryMovement migration complete.")

if __name__ == "__main__":
    migrate()
