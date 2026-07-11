"""
Inventory Monitoring — SQLAlchemy ORM models.

No separate table here by design. Inventory Monitoring reads stock
levels directly from Product.current_stock / min_stock_threshold
(see app/modules/products/models.py) instead of duplicating that state
into a second table that would need to stay in sync.
"""
