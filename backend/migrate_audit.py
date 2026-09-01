import sqlite3
import uuid

DB_PATH = 'C:/Users/Thiago/OneDrive/Desktop/Restaurant-NEV2-MANAGER/backend/restaurant_nev2.db'

def migrate():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS audit_logs (
            id BLOB PRIMARY KEY,
            user_id BLOB NOT NULL,
            restaurant_id BLOB NOT NULL,
            action VARCHAR(255) NOT NULL,
            details TEXT,
            ip_address VARCHAR(45),
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id),
            FOREIGN KEY(restaurant_id) REFERENCES restaurants(id)
        )
    ''')

    conn.commit()
    conn.close()
    print("AuditLog migration complete.")

if __name__ == "__main__":
    migrate()
