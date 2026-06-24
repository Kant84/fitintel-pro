# fix_warehouse_fk.py
with open('app/models/warehouse.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Убираем ForeignKey на clubs из всех моделей
replacements = [
    ('club_id = Column(Integer, ForeignKey("clubs.id", ondelete="CASCADE"), nullable=False)', 'club_id = Column(Integer, nullable=False)  # FK to clubs.id'),
    ('category_id = Column(UUID(as_uuid=True), ForeignKey("product_categories.id", ondelete="SET NULL"))', 'category_id = Column(UUID(as_uuid=True))  # FK to product_categories.id'),
    ('product_id = Column(UUID(as_uuid=True), ForeignKey("warehouse_products.id", ondelete="CASCADE"), nullable=False)', 'product_id = Column(UUID(as_uuid=True), nullable=False)  # FK to warehouse_products.id'),
    ('recipe_id = Column(UUID(as_uuid=True), ForeignKey("recipes.id", ondelete="CASCADE"), nullable=False)', 'recipe_id = Column(UUID(as_uuid=True), nullable=False)  # FK to recipes.id'),
    ('product_id = Column(UUID(as_uuid=True), ForeignKey("warehouse_products.id", ondelete="CASCADE"), nullable=False)', 'product_id = Column(UUID(as_uuid=True), nullable=False)  # FK to warehouse_products.id'),
    ('created_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))', 'created_by = Column(UUID(as_uuid=True))  # FK to users.id'),
    ('client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id", ondelete="SET NULL"))', 'client_id = Column(UUID(as_uuid=True))  # FK to clients.id'),
    ('product_id = Column(UUID(as_uuid=True), ForeignKey("warehouse_products.id", ondelete="SET NULL"))', 'product_id = Column(UUID(as_uuid=True))  # FK to warehouse_products.id'),
    ('recipe_id = Column(UUID(as_uuid=True), ForeignKey("recipes.id", ondelete="SET NULL"))', 'recipe_id = Column(UUID(as_uuid=True))  # FK to recipes.id'),
]

for old, new in replacements:
    content = content.replace(old, new)

with open('app/models/warehouse.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("FK constraints removed from warehouse models!")
