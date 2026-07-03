from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='Staff')  # 'Admin' or 'Staff'

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'role': self.role
        }

class Item(db.Model):
    __tablename__ = 'items'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50), nullable=False)  # 'Bakery Product' or 'Raw Material'
    price = db.Column(db.Float, nullable=False, default=0.0)

    # Relationships
    inventory = db.relationship('Inventory', back_populates='item', uselist=False, cascade="all, delete-orphan")
    sales = db.relationship('Sale', back_populates='item', cascade="all, delete-orphan")
    forecasts = db.relationship('Forecast', back_populates='item', cascade="all, delete-orphan")

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'category': self.category,
            'price': self.price
        }

class Inventory(db.Model):
    __tablename__ = 'inventory'
    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.Integer, db.ForeignKey('items.id'), unique=True, nullable=False)
    stock_qty = db.Column(db.Float, nullable=False, default=0.0)
    unit = db.Column(db.String(20), nullable=False)  # e.g., 'kg', 'L', 'units'
    reorder_threshold = db.Column(db.Float, nullable=False, default=0.0)

    # Relationship
    item = db.relationship('Item', back_populates='inventory')

    def to_dict(self):
        return {
            'id': self.id,
            'item_id': self.item_id,
            'name': self.item.name if self.item else '',
            'stock_qty': self.stock_qty,
            'unit': self.unit,
            'reorder_threshold': self.reorder_threshold,
            'is_low_stock': self.stock_qty < self.reorder_threshold
        }

class Sale(db.Model):
    __tablename__ = 'sales'
    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.Integer, db.ForeignKey('items.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)  # YYYY-MM-DD
    quantity_sold = db.Column(db.Integer, nullable=False)

    # Relationship
    item = db.relationship('Item', back_populates='sales')

    def to_dict(self):
        return {
            'id': self.id,
            'item_id': self.item_id,
            'item_name': self.item.name if self.item else '',
            'date': self.date.isoformat(),
            'quantity_sold': self.quantity_sold,
            'total_revenue': self.quantity_sold * (self.item.price if self.item else 0.0)
        }

class Forecast(db.Model):
    __tablename__ = 'forecasts'
    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.Integer, db.ForeignKey('items.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)  # YYYY-MM-DD
    predicted_qty = db.Column(db.Integer, nullable=False)

    # Relationship
    item = db.relationship('Item', back_populates='forecasts')

    def to_dict(self):
        return {
            'id': self.id,
            'item_id': self.item_id,
            'item_name': self.item.name if self.item else '',
            'date': self.date.isoformat(),
            'predicted_qty': self.predicted_qty
        }
