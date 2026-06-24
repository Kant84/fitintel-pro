# app/models/warehouse.py
from sqlalchemy import Column, String, Text, Numeric, Integer, Boolean, ForeignKey, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID
import uuid
from app.db.base import Base


class ProductCategory(Base):
    __tablename__ = "product_categories"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    club_id = Column(Integer, nullable=False)
    name = Column(String(100), nullable=False)
    type = Column(String(50))
    is_active = Column(Boolean, default=True)
    created_at = Column(TIMESTAMP, default="now()")


class WarehouseProduct(Base):
    __tablename__ = "warehouse_products"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    club_id = Column(Integer, nullable=False)
    category_id = Column(UUID(as_uuid=True))
    name = Column(String(200), nullable=False)
    description = Column(Text)
    unit = Column(String(20), default="шт")
    cost_price = Column(Numeric(10, 2), default=0)
    sale_price = Column(Numeric(10, 2), nullable=False)
    quantity = Column(Numeric(10, 3), default=0)
    min_quantity = Column(Numeric(10, 3), default=10)
    barcode = Column(String(50))
    supplier = Column(String(200))
    is_active = Column(Boolean, default=True)
    created_at = Column(TIMESTAMP, default="now()")
    updated_at = Column(TIMESTAMP, default="now()")


class Recipe(Base):
    __tablename__ = "recipes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    club_id = Column(Integer, nullable=False)
    name = Column(String(200), nullable=False)
    description = Column(Text)
    sale_price = Column(Numeric(10, 2), nullable=False)
    category = Column(String(50))
    is_active = Column(Boolean, default=True)
    created_at = Column(TIMESTAMP, default="now()")


class RecipeIngredient(Base):
    __tablename__ = "recipe_ingredients"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    recipe_id = Column(UUID(as_uuid=True), nullable=False)
    product_id = Column(UUID(as_uuid=True), nullable=False)
    quantity = Column(Numeric(10, 3), nullable=False)
    unit = Column(String(20), default="шт")
    created_at = Column(TIMESTAMP, default="now()")


class StockMovement(Base):
    __tablename__ = "stock_movements"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    club_id = Column(Integer, nullable=False)
    product_id = Column(UUID(as_uuid=True), nullable=False)
    type = Column(String(20))
    quantity = Column(Numeric(10, 3), nullable=False)
    unit_cost = Column(Numeric(10, 2))
    total_cost = Column(Numeric(10, 2))
    reason = Column(String(200))
    document_ref = Column(String(100))
    created_by = Column(UUID(as_uuid=True))
    created_at = Column(TIMESTAMP, default="now()")


class BarSale(Base):
    __tablename__ = "bar_sales"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    club_id = Column(Integer, nullable=False)
    client_id = Column(UUID(as_uuid=True))
    item_type = Column(String(20))
    product_id = Column(UUID(as_uuid=True))
    recipe_id = Column(UUID(as_uuid=True))
    item_name = Column(String(200))
    quantity = Column(Numeric(10, 3), nullable=False, default=1)
    unit_price = Column(Numeric(10, 2), nullable=False)
    total_price = Column(Numeric(10, 2), nullable=False)
    payment_method = Column(String(20))
    status = Column(String(20), default="completed")
    created_by = Column(UUID(as_uuid=True))
    created_at = Column(TIMESTAMP, default="now()")


class InventoryCount(Base):
    __tablename__ = "inventory_counts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    club_id = Column(Integer, nullable=False)
    product_id = Column(UUID(as_uuid=True), nullable=False)
    expected_quantity = Column(Numeric(10, 3), nullable=False)
    actual_quantity = Column(Numeric(10, 3), nullable=False)
    difference = Column(Numeric(10, 3))
    counted_by = Column(UUID(as_uuid=True))
    counted_at = Column(TIMESTAMP, default="now()")
