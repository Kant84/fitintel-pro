# fix_bar_sale.py
with open('app/api/v1/warehouse.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Находим проблемный блок и заменяем
old = '''        elif item_type == "recipe":
            recipe = db.query(Recipe).filter(Recipe.id == item.get("recipe_id")).first()
            if not recipe:
                raise HTTPException(404, "Recipe not found")
            
            # Списываем ингредиенты
            for ing in recipe.ingredients:
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
                    ))'''

new = '''        elif item_type == "recipe":
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
                    ))'''

if old in content:
    content = content.replace(old, new)
    print("Bar sale fixed!")
else:
    print("Pattern not found")

with open('app/api/v1/warehouse.py', 'w', encoding='utf-8') as f:
    f.write(content)
