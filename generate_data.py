import os
import random
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash
from app import app
from models import db, User, Item, Inventory, Sale

def seed_database():
    print("Starting database seeding...")
    
    # 1. Create tables
    with app.app_context():
        db.drop_all()
        db.create_all()
        print("Database tables created.")

        # 2. Seed Users
        admin = User(
            name="Alice Admin",
            email="admin@bakery.com",
            password_hash=generate_password_hash("admin123"),
            role="Admin"
        )
        staff = User(
            name="Bob Staff",
            email="staff@bakery.com",
            password_hash=generate_password_hash("staff123"),
            role="Staff"
        )
        db.session.add(admin)
        db.session.add(staff)
        print("Users seeded (admin@bakery.com / admin123, staff@bakery.com / staff123).")

        # 3. Seed Items (Bakery Products)
        products = [
            Item(name="Sourdough Bread", category="Bakery Product", price=5.50),
            Item(name="Chocolate Croissant", category="Bakery Product", price=3.75),
            Item(name="Strawberry Muffin", category="Bakery Product", price=2.50),
            Item(name="Cinnamon Roll", category="Bakery Product", price=3.00)
        ]
        for p in products:
            db.session.add(p)
        db.session.flush() # Flush to get item IDs

        # 4. Seed Items (Raw Materials) & Inventory
        raw_materials = [
            {"name": "Wheat Flour", "unit": "kg", "stock_qty": 120.0, "reorder_threshold": 40.0, "price": 1.20},
            {"name": "Butter", "unit": "kg", "stock_qty": 25.0, "reorder_threshold": 10.0, "price": 4.50},
            {"name": "Granulated Sugar", "unit": "kg", "stock_qty": 15.0, "reorder_threshold": 8.0, "price": 0.90},
            {"name": "Active Dry Yeast", "unit": "kg", "stock_qty": 2.0, "reorder_threshold": 0.5, "price": 12.0},
            {"name": "Fresh Milk", "unit": "L", "stock_qty": 8.0, "reorder_threshold": 10.0, "price": 1.50}  # Low stock on purpose
        ]
        
        for rm in raw_materials:
            item = Item(name=rm["name"], category="Raw Material", price=rm["price"])
            db.session.add(item)
            db.session.flush() # get ID
            
            inv = Inventory(
                item_id=item.id,
                stock_qty=rm["stock_qty"],
                unit=rm["unit"],
                reorder_threshold=rm["reorder_threshold"]
            )
            db.session.add(inv)
        print("Bakery Products and Raw Materials/Inventory seeded.")

        # 5. Generate 3 Months (90 Days) of Daily Sales Data
        # We will generate data up to yesterday
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=90)
        
        # Base demand and weekend scaling for products
        product_patterns = {
            "Sourdough Bread": {"base": 40, "weekend_mult": 1.5, "noise": 6},
            "Chocolate Croissant": {"base": 25, "weekend_mult": 1.8, "noise": 5},
            "Strawberry Muffin": {"base": 18, "weekend_mult": 1.4, "noise": 4},
            "Cinnamon Roll": {"base": 15, "weekend_mult": 1.6, "noise": 3}
        }
        
        sales_count = 0
        current_day = start_date
        while current_day < end_date:
            is_weekend = 1 if current_day.weekday() in [5, 6] else 0
            
            for p in products:
                pattern = product_patterns[p.name]
                base = pattern["base"]
                
                # Apply weekend multiplier
                if is_weekend:
                    sales_qty = int(base * pattern["weekend_mult"])
                else:
                    sales_qty = base
                
                # Add random noise and round
                noise = random.randint(-pattern["noise"], pattern["noise"])
                sales_qty = max(0, sales_qty + noise)
                
                sale = Sale(
                    item_id=p.id,
                    date=current_day,
                    quantity_sold=sales_qty
                )
                db.session.add(sale)
                sales_count += 1
            
            current_day += timedelta(days=1)
            
        db.session.commit()
        print(f"Seeded {sales_count} sales records across 90 days.")
        print("Database seeding completed successfully.")

if __name__ == "__main__":
    seed_database()
