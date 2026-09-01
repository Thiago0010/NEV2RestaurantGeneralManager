
import asyncio
import httpx
import uuid
from decimal import Decimal

BASE_URL = "http://127.0.0.1:8000"

async def test_system():
    async with httpx.AsyncClient(base_url=BASE_URL) as client:
        print("--- Starting System Audit ---")

        # 1. Register Owner
        print("\n[1] Testing Registration...")
        email = f"test_{uuid.uuid4().hex[:6]}@example.com"
        reg_payload = {
            "email": email,
            "password": "Password123!",
            "full_name": "Test Owner",
            "restaurant_name": "Test Gourmet",
            "restaurant_slug": f"test-gourmet-{uuid.uuid4().hex[:6]}",
            "secret_key": "change_this_in_env_or_set_correctly" # Need to check actual env
        }
        # Note: registration secret might fail if not set in .env
        resp = await client.post("/api/v1/auth/register", json=reg_payload)
        if resp.status_code != 200:
            print(f"Registration failed: {resp.status_code} - {resp.text}")
            # For audit purposes, if registration fails due to secret, we might skip or try without restaurant
            return

        token = resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        print("Registration Successful.")

        # 2. Create Category
        print("\n[2] Testing Categories...")
        cat_resp = await client.post("/api/v1/categories", json={"name": "Test Category"}, headers=headers)
        category_id = cat_resp.json()["id"]
        print(f"Category created: {category_id}")

        # 3. Create Product
        print("\n[3] Testing Products...")
        prod_payload = {
            "name": "Test Burger",
            "price": 25.00,
            "cost_price": 10.00,
            "category_id": category_id,
            "stock_quantity": 100,
            "unit": "unit"
        }
        prod_resp = await client.post("/api/v1/products", json=prod_payload, headers=headers)
        product_id = prod_resp.json()["id"]
        print(f"Product created: {product_id}")

        # 4. Setup BOM (Recipe)
        print("\n[4] Testing Recipe (BOM)...")
        # Create an ingredient product first
        ing_payload = {
            "name": "Beef Patty",
            "price": 0,
            "cost_price": 5.00,
            "category_id": category_id,
            "stock_quantity": 1000,
            "unit": "unit"
        }
        ing_resp = await client.post("/api/v1/products", json=ing_payload, headers=headers)
        ing_id = ing_resp.json()["id"]

        recipe_payload = {
            "ingredients": [
                {"ingredient_id": ing_id, "quantity": 1}
            ]
        }
        # Endpoints for recipes might vary, check product endpoints
        rec_resp = await client.put(f"/api/v1/products/{product_id}/recipe", json=recipe_payload, headers=headers)
        print(f"Recipe setup response: {rec_resp.status_code}")

        # 5. Table Flow
        print("\n[5] Testing Tables...")
        table_resp = await client.post("/api/v1/tables", json={"number": "01", "qty": 1, "seats": 4}, headers=headers)
        table_id = table_resp.json()[0]["id"]

        start_resp = await client.post(f"/api/v1/tables/{table_id}/start", headers=headers)
        print(f"Table start response: {start_resp.status_code}")

        # 6. Order Flow
        print("\n[6] Testing Order Flow...")
        order_payload = {
            "table_id": table_id,
            "table_number": "01",
            "items": [
                {"product_id": product_id, "product_name": "Test Burger", "quantity": 2, "unit_price": 25.00}
            ]
        }
        order_resp = await client.post("/api/v1/orders", json=order_payload, headers=headers)
        order_id = order_resp.json()["id"]
        print(f"Order created: {order_id}")

        # Transition to PREPARING (should deduct stock)
        update_resp = await client.put(f"/api/v1/orders/{order_id}", json={"status": "preparing"}, headers=headers)
        print(f"Order Preparing response: {update_resp.status_code}")

        # 7. Close Order and Financials
        print("\n[7] Testing Financials...")
        close_resp = await client.put(f"/api/v1/orders/{order_id}", json={"status": "closed", "payment_method": "pix"}, headers=headers)
        print(f"Order Closed response: {close_resp.status_code}")

        # Check Analytics
        from datetime import datetime, timedelta
        start = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        end = datetime.now().strftime("%Y-%m-%d")
        stats_resp = await client.get(f"/api/v1/analytics/stats?start_date={start}&end_date={end}", headers=headers)
        print(f"Stats: {stats_resp.json()}")

if __name__ == "__main__":
    asyncio.run(test_system())
