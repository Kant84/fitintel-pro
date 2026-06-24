# app/api/v1/warehouse.py
from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, require_permission
from app.db.session import get_db
from app.models.warehouse import (
    ProductCategory, WarehouseProduct, Recipe, RecipeIngredient,
    StockMovement, BarSale, InventoryCount
)
from app.models.trainer import TrainerProfile


router = APIRouter(prefix="/warehouse", tags=["Warehouse & Bar"])


# ========== CATEGORIES ==========
@router.post("/categories", status_code=201)
async def create_category(
    data: dict,
    db: Session = Depends(get_db),
    current_user = Depends(require_permission("warehouse.manage"))
):
    cat = ProductCategory(**data)
    db.add(cat)
    db.commit()
    db.refresh(cat)
    return {"id": str(cat.id), "name": cat.name, "type": cat.type}


@router.get("/categories")
async def list_categories(
    club_id: int = Query(...),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    return db.query(ProductCategory).filter(
        ProductCategory.club_id == club_id,
        ProductCategory.is_active == True
    ).all()


# ========== PRODUCTS ==========
@router.post("/products", status_code=201)
async def create_product(
    data: dict,
    db: Session = Depends(get_db),
    current_user = Depends(require_permission("warehouse.manage"))
):
    product = WarehouseProduct(**data)
    db.add(product)
    db.commit()
    db.refresh(product)
    return {
        "id": str(product.id),
        "name": product.name,
        "quantity": float(product.quantity),
        "sale_price": float(product.sale_price)
    }


@router.get("/products")
async def list_products(
    club_id: int = Query(...),
    low_stock: bool = Query(False),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    query = db.query(WarehouseProduct).filter(
        WarehouseProduct.club_id == club_id,
        WarehouseProduct.is_active == True
    )
    if low_stock:
        query = query.filter(WarehouseProduct.quantity <= WarehouseProduct.min_quantity)
    return query.all()


@router.get("/products/{product_id}")
async def get_product(product_id: UUID, db: Session = Depends(get_db)):
    product = db.query(WarehouseProduct).filter(WarehouseProduct.id == product_id).first()
    if not product:
        raise HTTPException(404, "Product not found")
    return product


# ========== STOCK MOVEMENTS ==========
@router.post("/stock/move", status_code=201)
async def stock_move(
    data: dict,
    db: Session = Depends(get_db),
    current_user = Depends(require_permission("warehouse.manage"))
):
    """Приход/расход/списание товара"""
    product_id = data.get("product_id")
    move_type = data.get("type")  # in, out, adjustment, write_off, sale, recipe
    quantity = Decimal(str(data.get("quantity", 0)))
    
    product = db.query(WarehouseProduct).filter(WarehouseProduct.id == product_id).first()
    if not product:
        raise HTTPException(404, "Product not found")
    
    # Обновляем остаток
    if move_type == "in":
        product.quantity = product.quantity + quantity
    elif move_type in ("out", "sale", "recipe", "write_off"):
        if product.quantity < quantity:
            raise HTTPException(400, f"Insufficient stock: {product.quantity} < {quantity}")
        product.quantity = product.quantity - quantity
    elif move_type == "adjustment":
        product.quantity = quantity  # прямое установление
    
    # Создаём запись движения
    movement = StockMovement(
        club_id=data.get("club_id"),
        product_id=product_id,
        type=move_type,
        quantity=quantity,
        unit_cost=data.get("unit_cost"),
        total_cost=data.get("total_cost"),
        reason=data.get("reason"),
        document_ref=data.get("document_ref"),
        created_by=current_user.id
    )
    db.add(movement)
    db.commit()
    db.refresh(movement)
    
    return {
        "movement_id": str(movement.id),
        "product_name": product.name,
        "new_quantity": float(product.quantity),
        "type": move_type
    }


# ========== RECIPES ==========
@router.post("/recipes", status_code=201)
async def create_recipe(
    data: dict,
    db: Session = Depends(get_db),
    current_user = Depends(require_permission("warehouse.manage"))
):
    ingredients = data.pop("ingredients", [])
    recipe = Recipe(**data)
    db.add(recipe)
    db.flush()
    
    for ing in ingredients:
        db.add(RecipeIngredient(
            recipe_id=recipe.id,
            product_id=ing["product_id"],
            quantity=Decimal(str(ing["quantity"])),
            unit=ing.get("unit", "шт")
        ))
    
    db.commit()
    db.refresh(recipe)
    return {"id": str(recipe.id), "name": recipe.name, "sale_price": float(recipe.sale_price)}


@router.get("/recipes")
async def list_recipes(
    club_id: int = Query(...),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    return db.query(Recipe).filter(
        Recipe.club_id == club_id,
        Recipe.is_active == True
    ).all()


# ========== BAR SALES ==========
@router.post("/bar/sales", status_code=201)
async def create_bar_sale(
    data: dict,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Продажа из бара/кафе"""
    items = data.pop("items", [])
    club_id = data.get("club_id")
    total = Decimal("0")
    
    for item in items:
        item_type = item.get("item_type")  # product или recipe
        qty = Decimal(str(item.get("quantity", 1)))
        
        if item_type == "product":
            product = db.query(WarehouseProduct).filter(
                WarehouseProduct.id == item.get("product_id")
            ).first()
            if not product:
                raise HTTPException(404, "Product not found")
            if product.quantity < qty:
                raise HTTPException(400, f"Insufficient stock for {product.name}")
            
            # Списываем со склада
            product.quantity = product.quantity - qty
            
            # Создаём запись продажи
            sale = BarSale(
                club_id=club_id,
                client_id=data.get("client_id"),
                item_type="product",
                product_id=product.id,
                item_name=product.name,
                quantity=qty,
                unit_price=product.sale_price,
                total_price=product.sale_price * qty,
                payment_method=data.get("payment_method"),
                created_by=current_user.id
            )
            db.add(sale)
            total += sale.total_price
            
            # Записываем движение
            db.add(StockMovement(
                club_id=club_id,
                product_id=product.id,
                type="sale",
                quantity=qty,
                reason="Bar sale",
                created_by=current_user.id
            ))
            
        elif item_type == "recipe":
            recipe = db.query(Recipe).filter(Recipe.id == item.get("recipe_id")).first()
            if not recipe:
                raise HTTPException(404, "Recipe not found")
            
            # Получаем ингредиенты через SQL
            from sqlalchemy import text
            ingredients = db.execute(text(
                "SELECT product_id, quantity FROM recipe_ingredients WHERE recipe_id = :recipe_id"
            ), {"recipe_id": str(recipe.id)}).fetchall()
            
            # Списываем ингредиенты
            for ing in ingredients:
                product = db.query(WarehouseProduct).filter(
                    WarehouseProduct.id == ing.product_id
                ).first()
                if product and product.quantity < ing.quantity * qty:
                    raise HTTPException(400, f"Insufficient {product.name} for recipe")
                if product:
                    product.quantity = product.quantity - (ing.quantity * qty)
                    db.add(StockMovement(
                        club_id=club_id,
                        product_id=product.id,
                        type="recipe",
                        quantity=ing.quantity * qty,
                        reason=f"Recipe: {recipe.name}",
                        created_by=current_user.id
                    ))
            
            sale = BarSale(
                club_id=club_id,
                client_id=data.get("client_id"),
                item_type="recipe",
                recipe_id=recipe.id,
                item_name=recipe.name,
                quantity=qty,
                unit_price=recipe.sale_price,
                total_price=recipe.sale_price * qty,
                payment_method=data.get("payment_method"),
                created_by=current_user.id
            )
            db.add(sale)
            total += sale.total_price
    
    db.commit()
    return {
        "total": float(total),
        "items_count": len(items),
        "payment_method": data.get("payment_method")
    }


@router.get("/bar/sales/today")
async def get_today_sales(
    club_id: int = Query(...),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    tomorrow = today + __import__('datetime').timedelta(days=1)
    
    sales = db.query(BarSale).filter(
        BarSale.club_id == club_id,
        BarSale.created_at >= today,
        BarSale.created_at < tomorrow
    ).all()
    
    total = sum(s.total_price for s in sales)
    return {
        "sales": sales,
        "total": float(total),
        "count": len(sales)
    }


# ========== INVENTORY ==========
@router.post("/inventory", status_code=201)
async def create_inventory(
    data: dict,
    db: Session = Depends(get_db),
    current_user = Depends(require_permission("warehouse.manage"))
):
    """Инвентаризация"""
    product_id = data.get("product_id")
    actual = Decimal(str(data.get("actual_quantity")))
    
    product = db.query(WarehouseProduct).filter(WarehouseProduct.id == product_id).first()
    if not product:
        raise HTTPException(404, "Product not found")
    
    expected = product.quantity
    diff = actual - expected
    
    # Обновляем остаток
    product.quantity = actual
    
    # Создаём запись инвентаризации
    inv = InventoryCount(
        club_id=data.get("club_id"),
        product_id=product_id,
        expected_quantity=expected,
        actual_quantity=actual,
        difference=diff,
        counted_by=current_user.id
    )
    db.add(inv)
    db.commit()
    db.refresh(inv)
    
    return {
        "product_name": product.name,
        "expected": float(expected),
        "actual": float(actual),
        "difference": float(diff)
    }


# ========== DASHBOARD ==========
@router.get("/dashboard")
async def get_dashboard(
    club_id: int = Query(...),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Дашборд склада и бара"""
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    tomorrow = today + __import__('datetime').timedelta(days=1)
    
    # Товары с низким остатком
    low_stock = db.query(WarehouseProduct).filter(
        WarehouseProduct.club_id == club_id,
        WarehouseProduct.is_active == True,
        WarehouseProduct.quantity <= WarehouseProduct.min_quantity
    ).count()
    
    # Продажи сегодня
    today_sales = db.query(BarSale).filter(
        BarSale.club_id == club_id,
        BarSale.created_at >= today,
        BarSale.created_at < tomorrow
    ).all()
    
    total_revenue = sum(s.total_price for s in today_sales)
    
    # Популярный товар
    popular = None
    if today_sales:
        from collections import Counter
        names = [s.item_name for s in today_sales]
        popular = Counter(names).most_common(1)[0][0]
    
    return {
        "low_stock_items": low_stock,
        "total_sales_today": float(total_revenue),
        "total_items_sold": len(today_sales),
        "popular_item": popular
    }
