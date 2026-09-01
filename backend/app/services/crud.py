from typing import Optional, List, Dict, Any
from uuid import UUID
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_, and_
from sqlalchemy.orm import selectinload
import secrets

from app.models import (
    Restaurant, User, Category, Product, Table, Order, OrderItem,
    Employee, ServiceCall, InventoryMovement, AuditLog, ProductRecipe, Expense
)
from app.schemas import (
    RestaurantCreate, RestaurantUpdate,
    CategoryCreate, CategoryUpdate,
    ProductCreate, ProductUpdate,
    TableCreate, TableUpdate,
    OrderCreate, OrderUpdate,
    OrderItemCreate,
    EmployeeCreate, EmployeeUpdate,
    ServiceCallCreate, ServiceCallUpdate,
    TableStatus, OrderStatus, PaymentMethod,
    UserRole, ServiceCallType, ServiceCallStatus
)
from app.core.security import get_password_hash, verify_password
from app.utils.qr_code import generate_qr_token, generate_qr_code_image, generate_qr_code_url


class AuditService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def log(self, user_id: UUID, restaurant_id: UUID, action: str, details: Optional[str] = None, ip_address: Optional[str] = None):
        log = AuditLog(
            user_id=user_id,
            restaurant_id=restaurant_id,
            action=action,
            details=details,
            ip_address=ip_address
        )
        self.db.add(log)
        await self.db.flush()

class RestaurantService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def generate_unique_slug(self, base_slug: str) -> str:
        """Ensure the slug is unique by appending a numeric suffix if necessary."""
        from app.utils.format import slugify
        slug = slugify(base_slug)
        if not slug:
            slug = "restaurant"

        count = 0
        while True:
            candidate = slug if count == 0 else f"{slug}-{count}"
            result = await self.db.execute(
                select(Restaurant).where(Restaurant.slug == candidate)
            )
            if not result.scalar_one_or_none():
                return candidate
            count += 1

    async def create(self, data: RestaurantCreate, owner_id: UUID) -> Restaurant:
        payload = data.model_dump()
        # Ensure slug is unique and normalized
        payload["slug"] = await self.generate_unique_slug(payload["slug"])

        restaurant = Restaurant(**payload)
        self.db.add(restaurant)
        await self.db.flush()
        # Refresh so server-default columns (created_at, updated_at) are populated
        # in the current async context before Pydantic serialization.
        await self.db.refresh(restaurant)

        # Create owner user if not exists
        # This is handled in auth service
        return restaurant

    async def get_by_id(self, restaurant_id: UUID) -> Optional[Restaurant]:
        result = await self.db.execute(
            select(Restaurant).where(Restaurant.id == restaurant_id)
        )
        return result.scalar_one_or_none()

    async def get_by_slug(self, slug: str) -> Optional[Restaurant]:
        result = await self.db.execute(
            select(Restaurant).where(Restaurant.slug == slug)
        )
        return result.scalar_one_or_none()

    async def update(self, restaurant_id: UUID, data: RestaurantUpdate) -> Optional[Restaurant]:
        restaurant = await self.get_by_id(restaurant_id)
        if not restaurant:
            return None

        update_data = data.model_dump(exclude_unset=True)
        if "slug" in update_data:
            # If slug is changing, ensure the new one is unique
            update_data["slug"] = await self.generate_unique_slug(update_data["slug"])

        for field, value in update_data.items():
            setattr(restaurant, field, value)

        await self.db.flush()
        # Refresh to ensure server-managed columns (updated_at via onupdate=func.now())
        # are loaded eagerly inside this async context. Otherwise Pydantic's
        # from_attributes triggers a lazy-load -> MissingGreenlet at serialization.
        await self.db.refresh(restaurant)
        return restaurant

    async def delete(self, restaurant_id: UUID, user_id: UUID) -> bool:
        restaurant = await self.get_by_id(restaurant_id)
        if not restaurant:
            return False

        # Log action
        audit_log = AuditLog(
            user_id=user_id,
            restaurant_id=restaurant_id,
            action="DELETE_RESTAURANT",
            details=f"Restaurant {restaurant.name} deleted"
        )
        self.db.add(audit_log)

        await self.db.delete(restaurant)
        return True


class CategoryService:
    def __init__(self, db: AsyncSession):
        self.db = db

    @staticmethod
    def _generate_slug(name: str) -> str:
        import re
        slug = re.sub(r'[^a-zA-Z0-9\s]', '', name).strip().lower()
        slug = re.sub(r'[\s\-]+', '-', slug)
        return slug

    async def create(self, data: CategoryCreate, restaurant_id: UUID) -> Category:
        # Get max sort_order
        result = await self.db.execute(
            select(func.max(Category.sort_order)).where(Category.restaurant_id == restaurant_id)
        )
        max_order = result.scalar() or 0

        payload = data.model_dump()
        # If client didn't explicitly set sort_order, auto-assign next slot
        if "sort_order" not in data.model_fields_set:
            payload["sort_order"] = max_order + 1
        # Generate slug if not provided
        if "slug" not in data.model_fields_set:
            base_slug = self._generate_slug(payload["name"])
            payload["slug"] = f"{base_slug}-{str(restaurant_id)[:8]}"

        category = Category(
            **payload,
            restaurant_id=restaurant_id,
        )
        self.db.add(category)
        await self.db.flush()
        await self.db.refresh(category)
        return category

    async def bulk_create(self, items: List[CategoryCreate], restaurant_id: UUID) -> List[Category]:
            """Create multiple categories in a single transaction"""
            # Get current max sort_order
            result = await self.db.execute(
                select(func.max(Category.sort_order)).where(Category.restaurant_id == restaurant_id)
            )
            max_order = result.scalar() or 0
            sort_order = max_order + 1
            categories = []
            for item in items:
                payload = item.model_dump()
                if not payload.get("sort_order"):
                    payload["sort_order"] = sort_order
                    sort_order += 1
                # Generate slug if not explicitly provided
                if "slug" not in item.model_fields_set:
                    base_slug = self._generate_slug(payload["name"])
                    payload["slug"] = f"{base_slug}-{str(restaurant_id)[:8]}"

                category = Category(
                    **payload,
                    restaurant_id=restaurant_id,
                )
                self.db.add(category)
                categories.append(category)

            await self.db.flush()
            for c in categories:
                await self.db.refresh(c)
            return categories

    async def get_by_id(self, category_id: UUID, restaurant_id: UUID) -> Optional[Category]:
        result = await self.db.execute(
            select(Category).where(
                Category.id == category_id,
                Category.restaurant_id == restaurant_id
            )
        )
        return result.scalar_one_or_none()

    async def list(
        self,
        restaurant_id: UUID,
        page: int = 1,
        page_size: int = 50
    ) -> tuple[List[Category], int]:
        query = select(Category).where(Category.restaurant_id == restaurant_id).order_by(Category.sort_order)
        total_result = await self.db.execute(select(func.count()).select_from(query.subquery()))
        total = total_result.scalar()

        result = await self.db.execute(
            query.offset((page - 1) * page_size).limit(page_size)
        )
        return result.scalars().all(), total

    async def update(self, category_id: UUID, restaurant_id: UUID, data: CategoryUpdate) -> Optional[Category]:
        category = await self.get_by_id(category_id, restaurant_id)
        if not category:
            return None

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(category, field, value)

        await self.db.flush()
        await self.db.refresh(category)
        return category

    async def delete(self, category_id: UUID, restaurant_id: UUID) -> bool:
        category = await self.get_by_id(category_id, restaurant_id)
        if not category:
            return False
        await self.db.delete(category)
        return True


class ProductService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, data: ProductCreate, restaurant_id: UUID) -> Product:
        product = Product(**data.model_dump(), restaurant_id=restaurant_id)
        self.db.add(product)
        await self.db.flush()
        return product

    async def get_by_id(self, product_id: UUID, restaurant_id: UUID) -> Optional[Product]:
        result = await self.db.execute(
            select(Product).where(
                Product.id == product_id,
                Product.restaurant_id == restaurant_id
            )
        )
        return result.scalar_one_or_none()

    async def list(
        self,
        restaurant_id: UUID,
        category_id: Optional[UUID] = None,
        available_only: bool = False,
        page: int = 1,
        page_size: int = 100
    ) -> tuple[List[Product], int]:
        query = select(Product).where(Product.restaurant_id == restaurant_id).order_by(Product.created_at.desc())

        if category_id:
            query = query.where(Product.category_id == category_id)
        if available_only:
            # The column is mapped to the Python attribute `is_available`
            # (see `Product` in `app/models/__init__.py`), not `available`.
            query = query.where(Product.is_available == True)

        total_result = await self.db.execute(select(func.count()).select_from(query.subquery()))
        total = total_result.scalar()

        result = await self.db.execute(
            query.offset((page - 1) * page_size).limit(page_size)
        )
        return result.scalars().all(), total

    async def update(self, product_id: UUID, restaurant_id: UUID, user_id: UUID, data: ProductUpdate) -> Optional[Product]:
        product = await self.get_by_id(product_id, restaurant_id)
        if not product:
            return None

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(product, field, value)

        # Log action
        audit = AuditService(self.db)
        await audit.log(
            user_id=user_id,
            restaurant_id=restaurant_id,
            action="UPDATE_PRODUCT",
            details=f"Product {product.name} updated: {update_data}"
        )

        await self.db.flush()
        await self.db.refresh(product)
        return product

    async def delete(self, product_id: UUID, restaurant_id: UUID, user_id: UUID) -> bool:
        product = await self.get_by_id(product_id, restaurant_id)
        if not product:
            return False

        # Log action
        audit = AuditService(self.db)
        await audit.log(
            user_id=user_id,
            restaurant_id=restaurant_id,
            action="DELETE_PRODUCT",
            details=f"Product {product.name} deleted"
        )

        await self.db.delete(product)
        return True

    async def toggle_field(self, product_id: UUID, restaurant_id: UUID, field: str) -> Optional[Product]:
        product = await self.get_by_id(product_id, restaurant_id)
        if not product:
            return None
        setattr(product, field, not getattr(product, field))
        await self.db.flush()
        return product


class TableService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, data: TableCreate, restaurant_id: UUID) -> List[Table]:
        tables = []
        start_num = int(data.number) if data.number.isdigit() else 1

        for i in range(data.qty):
            num = str(start_num + i).zfill(2)
            qr_token = generate_qr_token()

            table = Table(
                restaurant_id=restaurant_id,
                number=num,
                seats=data.seats,
                qr_token=qr_token
            )
            self.db.add(table)
            tables.append(table)

        await self.db.flush()
        return tables

    async def bulk_create(self, restaurant_id: UUID, count: int = 6, seats: int = 4, start_number: int = 1) -> List[Table]:
        """Create multiple tables in a single transaction"""
        tables = []
        for i in range(count):
            num = str(start_number + i).zfill(2)
            qr_token = generate_qr_token()

            table = Table(
                restaurant_id=restaurant_id,
                number=num,
                seats=seats,
                qr_token=qr_token
            )
            self.db.add(table)
            tables.append(table)

        await self.db.flush()
        return tables

    async def get_by_id(self, table_id: UUID, restaurant_id: UUID) -> Optional[Table]:
        result = await self.db.execute(
            select(Table).where(
                Table.id == table_id,
                Table.restaurant_id == restaurant_id
            )
        )
        return result.scalar_one_or_none()

    async def get_by_qr_token(self, qr_token: str) -> Optional[Table]:
        result = await self.db.execute(
            select(Table).where(Table.qr_token == qr_token)
        )
        return result.scalar_one_or_none()

    async def list(
        self,
        restaurant_id: UUID,
        status: Optional[TableStatus] = None,
        page: int = 1,
        page_size: int = 500
    ) -> tuple[List[Table], int]:
        query = select(Table).where(Table.restaurant_id == restaurant_id).order_by(Table.number)

        if status:
            query = query.where(Table.status == status)

        total_result = await self.db.execute(select(func.count()).select_from(query.subquery()))
        total = total_result.scalar()

        result = await self.db.execute(
            query.offset((page - 1) * page_size).limit(page_size)
        )
        return result.scalars().all(), total

    async def update(self, table_id: UUID, restaurant_id: UUID, data: TableUpdate) -> Optional[Table]:
        table = await self.get_by_id(table_id, restaurant_id)
        if not table:
            return None

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(table, field, value)

        await self.db.flush()
        await self.db.refresh(table)
        return table

    async def start_table(self, table_id: UUID, restaurant_id: UUID) -> Optional[Table]:
        """Marks a table as occupied (starts the service)."""
        table = await self.get_by_id(table_id, restaurant_id)
        if not table:
            return None

        table.status = TableStatus.OCCUPIED
        from app.utils.format import today_iso
        table.opened_at = today_iso()

        await self.db.flush()
        await self.db.refresh(table)
        return table

    async def delete(self, table_id: UUID, restaurant_id: UUID) -> bool:
        table = await self.get_by_id(table_id, restaurant_id)
        if not table:
            return False
        await self.db.delete(table)
        return True

    async def get_qr_code(self, table_id: UUID, restaurant_id: UUID, base_url: str) -> Optional[dict]:
        table = await self.get_by_id(table_id, restaurant_id)
        if not table:
            return None

        qr_image = generate_qr_code_image(generate_qr_code_url(base_url, table.qr_token))
        return {
            "table_id": table.id,
            "table_number": table.number,
            "qr_token": table.qr_token,
            "qr_code_base64": qr_image,
            "public_url": generate_qr_code_url(base_url, table.qr_token)
        }


class OrderService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, data: OrderCreate, restaurant_id: UUID, service_tax_percent: float = 10.0) -> Order:
        # Calculate totals using Decimal for financial precision.
        # SQLAlchemy Numeric columns map to Python Decimal.
        tax_pct = Decimal(str(service_tax_percent))
        subtotal = sum((Decimal(str(item.unit_price)) * Decimal(str(item.quantity)) for item in data.items), Decimal("0.00"))
        service_tax = (subtotal * (tax_pct / Decimal("100"))).quantize(Decimal("0.01"))
        total = (subtotal + service_tax).quantize(Decimal("0.01"))

        # Reject creating a brand-new order on a table that already has an
        # open one. The customer flow is supposed to call ``addItems`` on
        # the existing order in that case; if a duplicate POST sneaks
        # through (stale client state, retry, etc.) we'd otherwise split
        # the table's ticket in two and the tracking panel would jump back
        # and forth between the two.
        if data.table_id:
            table_row = await self.db.execute(
                select(Table).where(Table.id == data.table_id)
            )
            table = table_row.scalar_one_or_none()
            if table and table.current_order_id:
                existing = await self.get_by_id(table.current_order_id, restaurant_id)
                if existing and existing.status in (
                    OrderStatus.RECEIVED,
                    OrderStatus.PREPARING,
                    OrderStatus.READY,
                ):
                    raise ValueError(
                        f"Table already has an open order ({existing.id}); "
                        "use addItems instead of creating a new one"
                    )

        order = Order(
            restaurant_id=restaurant_id,
            table_id=data.table_id,
            table_number=data.table_number,
            status=OrderStatus.RECEIVED,
            subtotal=subtotal,
            service_tax=service_tax,
            total=total
        )
        self.db.add(order)
        await self.db.flush()

        # Create order items
        for item_data in data.items:
            item = OrderItem(
                restaurant_id=restaurant_id,
                order_id=order.id,
                product_id=item_data.product_id,
                product_name=item_data.product_name,
                quantity=item_data.quantity,
                unit_price=item_data.unit_price,
                notes=item_data.notes
            )
            self.db.add(item)

        # Update table
        table = await self.db.execute(
            select(Table).where(Table.id == data.table_id)
        )
        table = table.scalar_one_or_none()
        if table:
            table.status = TableStatus.OCCUPIED
            table.current_order_id = order.id
            from app.utils.format import today_iso
            table.opened_at = today_iso()

        await self.db.flush()
        # Eager-load `items` (and other relations) before returning so callers
        # can serialize via Pydantic without triggering lazy-load I/O outside
        # the async context — otherwise `OrderRead.model_validate(order)`
        # raises `MissingGreenlet`.
        return await self.get_by_id(order.id, restaurant_id)

    async def get_by_id(self, order_id: UUID, restaurant_id: UUID) -> Optional[Order]:
        result = await self.db.execute(
            select(Order)
            .options(selectinload(Order.items))
            .where(Order.id == order_id, Order.restaurant_id == restaurant_id)
        )
        return result.scalar_one_or_none()

    async def list(
        self,
        restaurant_id: UUID,
        status: Optional[List[OrderStatus]] = None,
        table_id: Optional[UUID] = None,
        created_date_gte: Optional[str] = None,
        created_date_lte: Optional[str] = None,
        page: int = 1,
        page_size: int = 100
    ) -> tuple[List[Order], int]:
        query = select(Order).where(Order.restaurant_id == restaurant_id).order_by(Order.created_at.desc())

        if status:
            query = query.where(Order.status.in_(status))
        if table_id:
            query = query.where(Order.table_id == table_id)
        if created_date_gte:
            query = query.where(Order.created_at >= created_date_gte)
        if created_date_lte:
            query = query.where(Order.created_at <= created_date_lte)

        total_result = await self.db.execute(select(func.count()).select_from(query.subquery()))
        total = total_result.scalar()

        result = await self.db.execute(
            query.options(selectinload(Order.items))
            .offset((page - 1) * page_size).limit(page_size)
        )
        return result.scalars().all(), total

    async def _deduct_stock(self, order: Order, restaurant_id: UUID):
        """Deducts stock for all items in the order based on BOM or product stock."""
        inv_service = InventoryService(self.db)
        recipe_service = RecipeService(self.db)

        for item in order.items:
            if not item.product_id:
                continue

            # Check if product has a recipe (BOM)
            recipe = await recipe_service.get_recipe(item.product_id, restaurant_id)

            if recipe:
                # Deduct each ingredient
                for ingredient_item in recipe:
                    qty_to_deduct = float(Decimal(str(ingredient_item.quantity)) * Decimal(str(item.quantity)))
                    await inv_service.update_stock(
                        product_id=ingredient_item.ingredient_id,
                        restaurant_id=restaurant_id,
                        quantity=qty_to_deduct,
                        movement_type="OUT",
                        reason=f"Order {order.id} - {item.product_name}"
                    )
            else:
                # Deduct the product itself
                await inv_service.update_stock(
                    product_id=item.product_id,
                    restaurant_id=restaurant_id,
                    quantity=float(item.quantity),
                    movement_type="OUT",
                    reason=f"Order {order.id} - {item.product_name}"
                )

    async def update(self, order_id: UUID, restaurant_id: UUID, data: OrderUpdate) -> Optional[Order]:
        order = await self.get_by_id(order_id, restaurant_id)
        if not order:
            return None

        update_data = data.model_dump(exclude_unset=True)

        # Handle status changes
        if "status" in update_data:
            new_status = update_data["status"]

            # Deduct stock when moving to PREPARING
            if new_status == OrderStatus.PREPARING and order.status != OrderStatus.PREPARING:
                await self._deduct_stock(order, restaurant_id)

            order.status = new_status

            if new_status in (OrderStatus.CLOSED, OrderStatus.CANCELLED):
                from app.utils.format import today_iso
                order.closed_at = today_iso()

                # Free the table so the next customer at the same seat can
                # start a fresh order.
                if order.table_id:
                    table = await self.db.execute(
                        select(Table).where(Table.id == order.table_id)
                    )
                    table = table.scalar_one_or_none()
                    if table:
                        table.status = TableStatus.FREE
                        table.current_order_id = None
                        table.opened_at = None

        if "payment_method" in update_data:
            order.payment_method = update_data["payment_method"]

        await self.db.flush()
        await self.db.refresh(order)
        return order

    async def add_items(self, order_id: UUID, restaurant_id: UUID, items: List[OrderItemCreate], service_tax_percent: float = 10.0) -> Optional[Order]:
        order = await self.get_by_id(order_id, restaurant_id)
        if not order:
            return None

        for item_data in items:
            item = OrderItem(
                restaurant_id=restaurant_id,
                order_id=order.id,
                product_id=item_data.product_id,
                product_name=item_data.product_name,
                quantity=item_data.quantity,
                unit_price=item_data.unit_price,
                notes=item_data.notes
            )
            self.db.add(item)

        # Recalculate totals
        await self.db.flush()
        await self.recalculate_totals(order.id, restaurant_id, service_tax_percent)

        return await self.get_by_id(order_id, restaurant_id)

    async def recalculate_totals(self, order_id: UUID, restaurant_id: UUID, service_tax_percent: float = 10.0) -> Optional[Order]:
        order = await self.get_by_id(order_id, restaurant_id)
        if not order:
            return None

        # Use Decimal for precision to avoid floating point rounding errors
        tax_pct = Decimal(str(service_tax_percent))
        subtotal = sum((Decimal(str(item.unit_price)) * Decimal(str(item.quantity)) for item in order.items), Decimal("0.00"))
        service_tax = (subtotal * (tax_pct / Decimal("100"))).quantize(Decimal("0.01"))
        total = (subtotal + service_tax).quantize(Decimal("0.01"))

        order.subtotal = subtotal
        order.service_tax = service_tax
        order.total = total

        await self.db.flush()
        return order

    async def delete_item(self, item_id: UUID, restaurant_id: UUID, service_tax_percent: float = 10.0) -> bool:
        result = await self.db.execute(
            select(OrderItem).where(
                OrderItem.id == item_id,
                OrderItem.restaurant_id == restaurant_id
            )
        )
        item = result.scalar_one_or_none()
        if not item:
            return False

        order_id = item.order_id
        await self.db.delete(item)
        await self.db.flush()

        await self.recalculate_totals(order_id, restaurant_id, service_tax_percent)
        return True


class EmployeeService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        data: EmployeeCreate,
        restaurant_id: UUID,
        user_id: Optional[UUID] = None,
    ) -> Employee:
        payload = data.model_dump()
        if not payload.get("hire_date"):
            from datetime import datetime, timezone
            payload["hire_date"] = datetime.now(timezone.utc)
        employee = Employee(
            **payload,
            restaurant_id=restaurant_id,
            user_id=user_id,
        )
        self.db.add(employee)
        await self.db.flush()
        return employee

    async def get_by_id(self, employee_id: UUID, restaurant_id: UUID) -> Optional[Employee]:
        result = await self.db.execute(
            select(Employee).where(
                Employee.id == employee_id,
                Employee.restaurant_id == restaurant_id
            )
        )
        return result.scalar_one_or_none()

    async def list(
        self,
        restaurant_id: UUID,
        active_only: bool = False,
        page: int = 1,
        page_size: int = 500
    ) -> tuple[List[Employee], int]:
        query = select(Employee).where(Employee.restaurant_id == restaurant_id)
        if active_only:
            query = query.where(Employee.is_active == True)
        query = query.order_by(Employee.name)
        total_result = await self.db.execute(select(func.count()).select_from(query.subquery()))
        total = total_result.scalar()
        result = await self.db.execute(
            query.offset((page - 1) * page_size).limit(page_size)
        )
        return result.scalars().all(), total

    async def update(self, employee_id: UUID, restaurant_id: UUID, data: EmployeeUpdate) -> Optional[Employee]:
        employee = await self.get_by_id(employee_id, restaurant_id)
        if not employee:
            return None

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(employee, field, value)

        # Keep the backing User in sync so login state matches the
        # Employee row (the FK is the User, and the owner's UI reads
        # is_active off the Employee).
        if "name" in update_data:
            employee.user.full_name = update_data["name"]
        if "is_active" in update_data:
            employee.user.is_active = update_data["is_active"]
        if "role" in update_data:
            employee.user.role = update_data["role"]

        await self.db.flush()
        await self.db.refresh(employee)
        return employee

    async def delete(self, employee_id: UUID, restaurant_id: UUID) -> bool:
        employee = await self.get_by_id(employee_id, restaurant_id)
        if not employee:
            return False
        await self.db.delete(employee)
        return True

    async def toggle_active(self, employee_id: UUID, restaurant_id: UUID) -> Optional[Employee]:
        employee = await self.get_by_id(employee_id, restaurant_id)
        if not employee:
            return None
        employee.is_active = not employee.is_active
        if employee.user is not None:
            employee.user.is_active = employee.is_active
        await self.db.flush()
        return employee


class ServiceCallService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, data: ServiceCallCreate, restaurant_id: UUID) -> ServiceCall:
        call = ServiceCall(
            **data.model_dump(),
            restaurant_id=restaurant_id,
            status=ServiceCallStatus.PENDING
        )
        self.db.add(call)
        await self.db.flush()
        return call

    async def get_by_id(self, call_id: UUID, restaurant_id: UUID) -> Optional[ServiceCall]:
        result = await self.db.execute(
            select(ServiceCall).where(
                ServiceCall.id == call_id,
                ServiceCall.restaurant_id == restaurant_id
            )
        )
        return result.scalar_one_or_none()

    async def list(
        self,
        restaurant_id: UUID,
        status: Optional[ServiceCallStatus] = None,
        page: int = 1,
        page_size: int = 200
    ) -> tuple[List[ServiceCall], int]:
        query = select(ServiceCall).where(ServiceCall.restaurant_id == restaurant_id).order_by(ServiceCall.created_at.desc())

        if status:
            query = query.where(ServiceCall.status == status)

        total_result = await self.db.execute(select(func.count()).select_from(query.subquery()))
        total = total_result.scalar()

        result = await self.db.execute(
            query.offset((page - 1) * page_size).limit(page_size)
        )
        return result.scalars().all(), total

    async def update_status(self, call_id: UUID, restaurant_id: UUID, status: ServiceCallStatus) -> Optional[ServiceCall]:
        call = await self.get_by_id(call_id, restaurant_id)
        if not call:
            return None

        call.status = status
        if status == ServiceCallStatus.RESOLVED:
            from app.utils.format import today_iso
            call.resolved_at = today_iso()

        await self.db.flush()
        await self.db.refresh(call)
        return call

class RecipeService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_or_update_recipe(self, product_id: UUID, restaurant_id: UUID, ingredients: List[Dict[str, Any]]) -> Product:
        """Sets the Bill of Materials (BOM) for a product."""
        # Remove existing recipe
        from sqlalchemy import delete
        await self.db.execute(delete(ProductRecipe).where(ProductRecipe.product_id == product_id))

        for ing in ingredients:
            recipe_item = ProductRecipe(
                product_id=product_id,
                ingredient_id=ing["ingredient_id"],
                quantity=Decimal(str(ing["quantity"])),
                restaurant_id=restaurant_id
            )
            self.db.add(recipe_item)

        await self.db.flush()

        # Return the product
        result = await self.db.execute(select(Product).where(Product.id == product_id))
        return result.scalar_one()

    async def get_recipe(self, product_id: UUID, restaurant_id: UUID) -> List[ProductRecipe]:
        """Returns the ingredients for a product."""
        result = await self.db.execute(
            select(ProductRecipe).where(
                ProductRecipe.product_id == product_id,
                ProductRecipe.restaurant_id == restaurant_id
            )
        )
        return result.scalars().all()

class InventoryService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def update_stock(self, product_id: UUID, restaurant_id: UUID, quantity: float, movement_type: str, reason: Optional[str] = None) -> Product:
        """Updates product stock and records the movement in audit trail."""
        result = await self.db.execute(
            select(Product).where(Product.id == product_id, Product.restaurant_id == restaurant_id)
        )
        product = result.scalar_one_or_none()
        if not product:
            raise ValueError("Product not found in this restaurant")

        # Record movement (using Decimal for storage)
        movement = InventoryMovement(
            product_id=product_id,
            restaurant_id=restaurant_id,
            quantity=int(quantity) if quantity == int(quantity) else quantity,
            movement_type=movement_type,
            reason=reason
        )
        self.db.add(movement)

        # Update stock
        q = Decimal(str(quantity))
        current_stock = Decimal(str(product.stock_quantity))

        if movement_type == "IN":
            product.stock_quantity = float(current_stock + q)
        elif movement_type == "OUT":
            if current_stock < q:
                raise ValueError("Insufficient stock for this operation")
            product.stock_quantity = float(current_stock - q)
        elif movement_type == "ADJUSTMENT":
            product.stock_quantity = float(q) # Direct override

        await self.db.flush()
        await self.db.refresh(product)
        return product

    async def get_stock_report(self, restaurant_id: UUID) -> List[Product]:
        result = await self.db.execute(
            select(Product).where(Product.restaurant_id == restaurant_id)
        )
        return result.scalars().all()

class FinancialService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_comprehensive_stats(self, restaurant_id: UUID, start_date: str, end_date: str) -> Dict[str, Any]:
        """
        Calculate a professional P&L (Profit and Loss) statement.
        """
        # Ensure end_date includes the full day (up to 23:59:59)
        full_end_date = f"{end_date} 23:59:59"

        # 1. Gross Revenue
        # Use closed_at for revenue tracking - revenue is realized when the order is CLOSED
        revenue_query = select(
            func.sum(Order.total).label("total_revenue"),
            func.count(Order.id).label("order_count")
        ).where(
            Order.restaurant_id == restaurant_id,
            Order.status == OrderStatus.CLOSED,
            Order.closed_at >= start_date,
            Order.closed_at <= full_end_date
        )
        rev_res = await self.db.execute(revenue_query)
        rev_row = rev_res.first()
        gross_revenue = Decimal(str(rev_row.total_revenue or 0))
        order_count = rev_row.order_count or 0

        # 2. COGS (Cost of Goods Sold)
        orders_query = select(Order).where(
            Order.restaurant_id == restaurant_id,
            Order.status == OrderStatus.CLOSED,
            Order.closed_at >= start_date,
            Order.closed_at <= full_end_date
        ).options(selectinload(Order.items))

        orders_res = await self.db.execute(orders_query)
        closed_orders = orders_res.scalars().all()

        total_cogs = Decimal("0.00")
        recipe_service = RecipeService(self.db)

        for order in closed_orders:
            for item in order.items:
                if not item.product_id:
                    continue

                prod_res = await self.db.execute(select(Product).where(Product.id == item.product_id))
                product = prod_res.scalar_one_or_none()
                if not product:
                    continue

                recipe = await recipe_service.get_recipe(item.product_id, restaurant_id)
                if recipe:
                    item_cost = Decimal("0.00")
                    for ing_recipe in recipe:
                        ing_res = await self.db.execute(select(Product).where(Product.id == ing_recipe.ingredient_id))
                        ing_prod = ing_res.scalar_one_or_none()
                        if ing_prod:
                            item_cost += Decimal(str(ing_prod.cost_price)) * Decimal(str(ing_recipe.quantity))
                    total_cogs += item_cost * Decimal(str(item.quantity))
                else:
                    total_cogs += Decimal(str(product.cost_price)) * Decimal(str(item.quantity))

        # 3. Operational Expenses
        exp_query = select(func.sum(Expense.amount)).where(
            Expense.restaurant_id == restaurant_id,
            Expense.date >= start_date,
            Expense.date <= full_end_date
        )
        exp_res = await self.db.execute(exp_query)
        operational_expenses = Decimal(str(exp_res.scalar() or 0))

        # 4. Final Calculations
        gross_profit = gross_revenue - total_cogs
        net_profit = gross_profit - operational_expenses

        profit_margin = Decimal("0.00")
        if gross_revenue > 0:
            profit_margin = (net_profit / gross_revenue) * 100

        return {
            "period": {"start": start_date, "end": end_date},
            "gross_revenue": float(gross_revenue),
            "order_count": order_count,
            "cogs": float(total_cogs),
            "gross_profit": float(gross_profit),
            "operational_expenses": float(operational_expenses),
            "net_profit": float(net_profit),
            "profit_margin_percent": float(profit_margin.quantize(Decimal("0.01")))
        }

    async def get_revenue_stats(self, restaurant_id: UUID, start_date: str, end_date: str) -> Dict[str, Any]:
        """Simple revenue stats for the dashboard"""
        stats = await self.get_comprehensive_stats(restaurant_id, start_date, end_date)
        return {
            "total_revenue": stats["gross_revenue"],
            "order_count": stats["order_count"]
        }

    async def get_top_products(self, restaurant_id: UUID, limit: int = 5) -> List[Dict[str, Any]]:
        """Get most sold products by quantity."""
        query = (
            select(
                Product.name,
                func.sum(OrderItem.quantity).label("total_qty")
            )
            .join(OrderItem, OrderItem.product_id == Product.id)
            .join(Order, Order.id == OrderItem.order_id)
            .where(Order.restaurant_id == restaurant_id, Order.status == OrderStatus.CLOSED)
            .group_by(Product.name)
            .order_by(func.sum(OrderItem.quantity).desc())
            .limit(limit)
        )
        result = await self.db.execute(query)
        return [{"name": row[0], "quantity": row[1]} for row in result.all()]
