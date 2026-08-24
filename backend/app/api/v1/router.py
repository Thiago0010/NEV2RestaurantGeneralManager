from fastapi import APIRouter

from app.api.v1.endpoints import (
    auth, restaurant, categories, products, tables,
    orders, employees, service_calls, public, billing, admin_billing
)
from app.api.v1.websockets import routes as websocket_routes

api_router = APIRouter(prefix="/api/v1")

# Auth
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])

# Restaurant
api_router.include_router(restaurant.router, prefix="/restaurant", tags=["restaurant"])

# Categories
api_router.include_router(categories.router)

# Products
api_router.include_router(products.router)

# Tables
api_router.include_router(tables.router)

# Orders
api_router.include_router(orders.router)

# Employees
api_router.include_router(employees.router)

# Service Calls
api_router.include_router(service_calls.router)

# Billing
api_router.include_router(billing.router, prefix="/billing", tags=["billing"])

# Admin Billing
api_router.include_router(admin_billing.router, prefix="/admin/billing", tags=["admin-billing"])

# Public (no auth)
api_router.include_router(public.router)

# WebSockets
api_router.include_router(websocket_routes.router, prefix="/ws", tags=["websockets"])