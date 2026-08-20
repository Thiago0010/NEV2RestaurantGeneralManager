from typing import Optional, List, Dict, Any
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_, and_
from sqlalchemy.orm import selectinload
import secrets

from app.models import (
    Restaurant, User, Category, Product, Table, Order, OrderItem,
    Employee, ServiceCall
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


class RestaurantService:
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create(self, data: RestaurantCreate, owner_id: UUID) -> Restaurant:
        restaurant = Restaurant(**data.model_dump())
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
        for field, value in update_data.items():
            setattr(restaurant, field, value)

        await self.db.flush()
        # Refresh to ensure server-managed columns (updated_at via onupdate=func.now())
        # are loaded eagerly inside this async context. Otherwise Pydantic's
        # from_attributes triggers a lazy-load -> MissingGreenlet at serialization.
        await self.db.refresh(restaurant)
        return restaurant
    
    async def delete(self, restaurant_id: UUID) -> bool:
        restaurant = await self.get_by_id(restaurant_id)
        if not restaurant:
            return False
        await self.db.delete(restaurant)
        return True


class CategoryService:
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create(self, data: CategoryCreate, restaurant_id: UUID) -> Category:
        # Get max sort_order
        result = await self.db.execute(
            select(func.max(Category.sort_order)).where(Category.restaurant_id == restaurant_id)
        )
        max_order = result.scalar() or 0

        payload = data.model_dump()
        # If client didn't explicitly set sort_order (or sent 0), auto-assign next slot
        if not payload.get("sort_order"):
            payload["sort_order"] = max_order + 1

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

        categories = []
        for i, item in enumerate(items):
            payload = item.model_dump()
            if not payload.get("sort_order"):
                payload["sort_order"] = max_order + 1 + i

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
            query = query.where(Product.available == True)
        
        total_result = await self.db.execute(select(func.count()).select_from(query.subquery()))
        total = total_result.scalar()
        
        result = await self.db.execute(
            query.offset((page - 1) * page_size).limit(page_size)
        )
        return result.scalars().all(), total
    
    async def update(self, product_id: UUID, restaurant_id: UUID, data: ProductUpdate) -> Optional[Product]:
        product = await self.get_by_id(product_id, restaurant_id)
        if not product:
            return None

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(product, field, value)

        await self.db.flush()
        await self.db.refresh(product)
        return product
    
    async def delete(self, product_id: UUID, restaurant_id: UUID) -> bool:
        product = await self.get_by_id(product_id, restaurant_id)
        if not product:
            return False
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
        # Calculate totals. Both `item.unit_price` and `service_tax_percent`
        # come from Numeric columns, so they can be Decimal in the in-memory
        # model — coerce to float up front so arithmetic stays uniform (a
        # `Decimal * float` raises TypeError).
        tax_pct = float(service_tax_percent)
        subtotal = float(sum(item.unit_price * item.quantity for item in data.items))
        service_tax = round(subtotal * (tax_pct / 100), 2)
        total = round(subtotal + service_tax, 2)
        
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
    
    async def update(self, order_id: UUID, restaurant_id: UUID, data: OrderUpdate) -> Optional[Order]:
        order = await self.get_by_id(order_id, restaurant_id)
        if not order:
            return None

        update_data = data.model_dump(exclude_unset=True)

        # Handle status changes
        if "status" in update_data:
            new_status = update_data["status"]
            order.status = new_status

            if new_status == OrderStatus.CLOSED:
                from app.utils.format import today_iso
                order.closed_at = today_iso()

                # Free the table
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

        # Same Decimal/float normalization as create() — both `item.unit_price`
        # and `service_tax_percent` are Numeric columns.
        tax_pct = float(service_tax_percent)
        subtotal = float(sum(item.unit_price * item.quantity for item in order.items))
        service_tax = round(subtotal * (tax_pct / 100), 2)
        total = round(subtotal + service_tax, 2)
        
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
    
    async def create(self, data: EmployeeCreate, restaurant_id: UUID) -> Employee:
        employee = Employee(**data.model_dump(), restaurant_id=restaurant_id)
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
        query = select(Employee).where(Employee.restaurant_id == restaurant_id).order_by(Employee.name)
        
        if active_only:
            query = query.where(Employee.active == True)
        
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
        employee.active = not employee.active
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