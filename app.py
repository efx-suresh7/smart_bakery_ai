import os
from datetime import datetime, timedelta
import joblib
import pandas as pd
import numpy as np
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from models import db, User, Item, Inventory, Sale, Forecast
from werkzeug.security import check_password_hash, generate_password_hash
import google.generativeai as genai

# Configure Gemini API
gemini_key = os.environ.get("GEMINI_API_KEY")
has_gemini = False
if gemini_key:
    genai.configure(api_key=gemini_key)
    has_gemini = True

app = Flask(__name__)
app.config['SECRET_KEY'] = 'smart_bakery_secret_key_12345'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///bakery.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

# Helper Decorators for Auth
def login_required(f):
    import functools
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'danger')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    import functools
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in first.', 'danger')
            return redirect(url_for('login'))
        if session.get('user_role') != 'Admin':
            flash('Admin privilege required.', 'warning')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

# Context Processor to make username and role available in templates
@app.context_processor
def inject_user_details():
    return {
        'logged_in': 'user_id' in session,
        'username': session.get('user_name', ''),
        'user_role': session.get('user_role', '')
    }

# --- AUTH ROUTES ---

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
        
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password_hash, password):
            session['user_id'] = user.id
            session['user_role'] = user.role
            session['user_name'] = user.name
            flash(f'Welcome back, {user.name}!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid email or password.', 'danger')
            
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        role = request.form.get('role', 'Staff')
        
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('Email already registered.', 'danger')
            return redirect(url_for('register'))
            
        hashed_pw = generate_password_hash(password)
        new_user = User(name=name, email=email, password_hash=hashed_pw, role=role)
        db.session.add(new_user)
        db.session.commit()
        
        flash('Account registered successfully. Please log in.', 'success')
        return redirect(url_for('login'))
        
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully.', 'info')
    return redirect(url_for('login'))

# --- DASHBOARD & CRUD ROUTES ---

@app.route('/')
@login_required
def dashboard():
    return render_template('dashboard.html')

# Inventory Management (CRUD)
@app.route('/inventory', methods=['GET'])
@login_required
def inventory():
    # Fetch all items that are Raw Materials and join with Inventory
    raw_materials = db.session.query(Item, Inventory).filter(
        Item.category == 'Raw Material',
        Item.id == Inventory.item_id
    ).all()
    
    # Check if there are low stock items
    low_stock_count = 0
    formatted_materials = []
    for item, inv in raw_materials:
        is_low = inv.stock_qty < inv.reorder_threshold
        if is_low:
            low_stock_count += 1
        formatted_materials.append({
            'id': item.id,
            'name': item.name,
            'price': item.price,
            'stock_qty': inv.stock_qty,
            'unit': inv.unit,
            'reorder_threshold': inv.reorder_threshold,
            'is_low': is_low
        })
        
    return render_template('inventory.html', materials=formatted_materials, low_stock_count=low_stock_count)

@app.route('/inventory/add', methods=['POST'])
@login_required
def add_inventory():
    name = request.form.get('name')
    price = float(request.form.get('price', 0.0))
    stock_qty = float(request.form.get('stock_qty', 0.0))
    unit = request.form.get('unit')
    reorder_threshold = float(request.form.get('reorder_threshold', 0.0))
    
    # Create item in items table
    new_item = Item(name=name, category='Raw Material', price=price)
    db.session.add(new_item)
    db.session.flush() # Populate new_item.id
    
    # Create inventory details
    new_inventory = Inventory(
        item_id=new_item.id,
        stock_qty=stock_qty,
        unit=unit,
        reorder_threshold=reorder_threshold
    )
    db.session.add(new_inventory)
    db.session.commit()
    
    flash(f'Raw material "{name}" added to inventory.', 'success')
    return redirect(url_for('inventory'))

@app.route('/inventory/edit/<int:item_id>', methods=['POST'])
@login_required
def edit_inventory(item_id):
    item = Item.query.get(item_id)
    if not item or item.category != 'Raw Material':
        flash('Material not found.', 'danger')
        return redirect(url_for('inventory'))
        
    inv = Inventory.query.filter_by(item_id=item_id).first()
    
    item.name = request.form.get('name')
    item.price = float(request.form.get('price', 0.0))
    if inv:
        inv.stock_qty = float(request.form.get('stock_qty', 0.0))
        inv.unit = request.form.get('unit')
        inv.reorder_threshold = float(request.form.get('reorder_threshold', 0.0))
        
    db.session.commit()
    flash(f'Material "{item.name}" updated successfully.', 'success')
    return redirect(url_for('inventory'))

@app.route('/inventory/delete/<int:item_id>', methods=['POST'])
@login_required
def delete_inventory(item_id):
    # Only Admin can delete inventory items
    if session.get('user_role') != 'Admin':
        flash('Only Admins can delete inventory items.', 'danger')
        return redirect(url_for('inventory'))
        
    item = Item.query.get(item_id)
    if item:
        db.session.delete(item) # Cascade deletes corresponding inventory row
        db.session.commit()
        flash('Raw material deleted from database.', 'info')
    else:
        flash('Material not found.', 'danger')
    return redirect(url_for('inventory'))

# Sales Management
@app.route('/sales', methods=['GET', 'POST'])
@login_required
def sales():
    # If POST: Add daily sales record
    if request.method == 'POST':
        item_id = int(request.form.get('item_id'))
        date_str = request.form.get('date')
        quantity_sold = int(request.form.get('quantity_sold'))
        
        date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
        
        # Check if record already exists for this item and date
        existing_sale = Sale.query.filter_by(item_id=item_id, date=date_obj).first()
        if existing_sale:
            existing_sale.quantity_sold += quantity_sold
            flash(f'Added {quantity_sold} units to existing sales record.', 'success')
        else:
            new_sale = Sale(item_id=item_id, date=date_obj, quantity_sold=quantity_sold)
            db.session.add(new_sale)
            flash('Sales record added successfully.', 'success')
            
        db.session.commit()
        return redirect(url_for('sales'))
        
    # GET: View with filters
    items = Item.query.filter_by(category='Bakery Product').all()
    
    # Read filters
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')
    selected_item_id = request.args.get('item_id')
    
    query = Sale.query
    
    if start_date_str:
        start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
        query = query.filter(Sale.date >= start_date)
    if end_date_str:
        end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
        query = query.filter(Sale.date <= end_date)
    if selected_item_id and selected_item_id != 'all':
        query = query.filter(Sale.item_id == int(selected_item_id))
        
    sales_records = query.order_by(Sale.date.desc()).all()
    
    return render_template(
        'sales.html', 
        sales_records=sales_records, 
        items=items,
        start_date=start_date_str,
        end_date=end_date_str,
        selected_item_id=selected_item_id
    )

# Forecast Screen
@app.route('/forecast')
@login_required
def forecast_view():
    items = Item.query.filter_by(category='Bakery Product').all()
    return render_template('forecast.html', items=items)


# --- API ENDPOINTS ---

@app.route('/api/forecast/<date_str>', methods=['GET'])
@login_required
def get_forecast(date_str):
    """
    Returns predicted quantity to bake per item for the given date.
    Saves predictions to 'forecasts' table.
    """
    try:
        target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400
        
    # Check if forecast file exists
    model_path = 'forecast_model.joblib'
    if not os.path.exists(model_path):
        return jsonify({'error': 'Forecasting model not trained yet. Please run train_model.py'}), 500
        
    # Load model and metadata
    try:
        model_data = joblib.load(model_path)
    except Exception as e:
        return jsonify({'error': f'Failed to load model: {str(e)}'}), 500
        
    model = model_data['model']
    item_ids = model_data['item_ids']
    feature_cols = model_data['feature_cols']
    
    # Calculate features for this target date
    day_of_week = target_date.weekday()
    is_weekend = 1 if day_of_week in [5, 6] else 0
    
    predictions = []
    
    # Retrieve all active bakery products
    bakery_products = Item.query.filter_by(category='Bakery Product').all()
    
    for item in bakery_products:
        # Calculate past 7 days average sales prior to target_date
        start_date = target_date - timedelta(days=7)
        sales_records = Sale.query.filter(
            Sale.item_id == item.id,
            Sale.date >= start_date,
            Sale.date < target_date
        ).all()
        
        if sales_records:
            past_7_day_avg = sum(s.quantity_sold for s in sales_records) / len(sales_records)
        else:
            # Fallback to historical mean
            all_sales = Sale.query.filter(Sale.item_id == item.id).all()
            if all_sales:
                past_7_day_avg = sum(s.quantity_sold for s in all_sales) / len(all_sales)
            else:
                past_7_day_avg = 0.0
                
        # Build features dict for matching one-hot encoding columns
        feat_dict = {
            'day_of_week': day_of_week,
            'is_weekend': is_weekend,
            'past_7_day_avg': past_7_day_avg
        }
        for item_id in item_ids:
            feat_dict[f'item_{item_id}'] = 1 if item.id == item_id else 0
            
        # Ensure correct column order
        feat_vector = [feat_dict[col] for col in feature_cols]
        
        # Run prediction
        pred = model.predict([feat_vector])[0]
        predicted_qty = max(0, int(round(pred)))
        
        # Save or update forecast in database
        forecast = Forecast.query.filter_by(item_id=item.id, date=target_date).first()
        if forecast:
            forecast.predicted_qty = predicted_qty
        else:
            forecast = Forecast(item_id=item.id, date=target_date, predicted_qty=predicted_qty)
            db.session.add(forecast)
            
        predictions.append({
            'item_id': item.id,
            'item_name': item.name,
            'predicted_qty': predicted_qty,
            'unit_price': item.price,
            'past_7_day_avg': round(past_7_day_avg, 2)
        })
        
    db.session.commit()
    return jsonify({
        'date': date_str,
        'day_of_week': ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'][day_of_week],
        'is_weekend': bool(is_weekend),
        'predictions': predictions
    })

@app.route('/api/dashboard_data', methods=['GET'])
@login_required
def get_dashboard_data():
    """
    Returns data for charts and widgets:
    - Low stock items
    - Historical sales trend (last 7 days)
    - Forecast vs Actual comparison (last 14 days)
    - Wastage report (forecast vs actual for last 7 days)
    - Accuracy percentage
    """
    # 1. Low stock items
    low_stock = []
    materials = db.session.query(Item, Inventory).filter(
        Item.category == 'Raw Material',
        Item.id == Inventory.item_id
    ).all()
    for item, inv in materials:
        if inv.stock_qty < inv.reorder_threshold:
            low_stock.append({
                'name': item.name,
                'stock_qty': inv.stock_qty,
                'unit': inv.unit,
                'threshold': inv.reorder_threshold
            })
            
    # 2. Sales Trend (last 7 days of actual sales records in database)
    # Find the most recent sales date in the database
    latest_sale = Sale.query.order_by(Sale.date.desc()).first()
    if not latest_sale:
        return jsonify({'error': 'No sales records found.'}), 400
        
    end_date = latest_sale.date
    start_date = end_date - timedelta(days=6)
    
    # Query sales in range
    sales_in_range = Sale.query.filter(Sale.date >= start_date, Sale.date <= end_date).all()
    
    # Process sales trend
    sales_df = pd.DataFrame([{
        'date': s.date,
        'qty': s.quantity_sold,
        'revenue': s.quantity_sold * s.item.price
    } for s in sales_in_range])
    
    trend_data = []
    if not sales_df.empty:
        sales_grouped = sales_df.groupby('date').agg({'qty': 'sum', 'revenue': 'sum'}).reset_index()
        sales_grouped = sales_grouped.sort_values(by='date')
        for idx, row in sales_grouped.iterrows():
            trend_data.append({
                'date': row['date'].strftime('%Y-%m-%d'),
                'total_qty': int(row['qty']),
                'total_revenue': round(float(row['revenue']), 2)
            })
            
    # 3. Forecast vs Actual (last 14 days)
    f_vs_a_start = end_date - timedelta(days=13)
    
    sales_14d = Sale.query.filter(Sale.date >= f_vs_a_start, Sale.date <= end_date).all()
    forecasts_14d = Forecast.query.filter(Forecast.date >= f_vs_a_start, Forecast.date <= end_date).all()
    
    sales_14d_df = pd.DataFrame([{'date': s.date, 'actual': s.quantity_sold} for s in sales_14d])
    forecast_14d_df = pd.DataFrame([{'date': f.date, 'forecast': f.predicted_qty} for f in forecasts_14d])
    
    f_vs_a_data = []
    
    if not sales_14d_df.empty or not forecast_14d_df.empty:
        # Build date range lists
        dates = [f_vs_a_start + timedelta(days=i) for i in range(14)]
        for d in dates:
            act_qty = int(sales_14d_df[sales_14d_df['date'] == d]['actual'].sum()) if not sales_14d_df.empty else 0
            fore_qty = int(forecast_14d_df[forecast_14d_df['date'] == d]['forecast'].sum()) if not forecast_14d_df.empty else 0
            f_vs_a_data.append({
                'date': d.strftime('%Y-%m-%d'),
                'actual': act_qty,
                'forecast': fore_qty
            })
            
    # 4. Wastage Report (last 7 days per item)
    # Wastage = Predicted/Baked - Actual Sold (only positive differences, since we baked exactly predicted_qty)
    wastage_start = end_date - timedelta(days=6)
    sales_7d = Sale.query.filter(Sale.date >= wastage_start, Sale.date <= end_date).all()
    forecasts_7d = Forecast.query.filter(Forecast.date >= wastage_start, Forecast.date <= end_date).all()
    
    s_7d_df = pd.DataFrame([{'item_name': s.item.name, 'actual': s.quantity_sold} for s in sales_7d])
    f_7d_df = pd.DataFrame([{'item_name': f.item.name, 'forecast': f.predicted_qty} for f in forecasts_7d])
    
    wastage_data = {}
    
    # Initialize dictionary
    bakery_products = Item.query.filter_by(category='Bakery Product').all()
    for item in bakery_products:
        wastage_data[item.name] = {'actual': 0, 'forecast': 0, 'wastage': 0}
        
    if not s_7d_df.empty:
        for name, group in s_7d_df.groupby('item_name'):
            if name in wastage_data:
                wastage_data[name]['actual'] = int(group['actual'].sum())
    if not f_7d_df.empty:
        for name, group in f_7d_df.groupby('item_name'):
            if name in wastage_data:
                wastage_data[name]['forecast'] = int(group['forecast'].sum())
                
    for name in wastage_data:
        # wastage = predicted (forecast) - actual sold
        # if actual sold > forecast (e.g. customers bought everything and wanted more, wastage is 0)
        actual = wastage_data[name]['actual']
        forecast = wastage_data[name]['forecast']
        wastage_data[name]['wastage'] = max(0, forecast - actual)
        
    # 5. ML Accuracy (Mean Absolute Percentage Error over last 30 days)
    acc_start = end_date - timedelta(days=29)
    sales_30d = Sale.query.filter(Sale.date >= acc_start, Sale.date <= end_date).all()
    forecasts_30d = Forecast.query.filter(Forecast.date >= acc_start, Forecast.date <= end_date).all()
    
    # Match dates and items
    s_30d_dict = {(s.date, s.item_id): s.quantity_sold for s in sales_30d}
    f_30d_dict = {(f.date, f.item_id): f.predicted_qty for f in forecasts_30d}
    
    errors = []
    for key, f_qty in f_30d_dict.items():
        if key in s_30d_dict:
            actual = s_30d_dict[key]
            # avoid division by zero
            denom = max(1, actual)
            err = abs(actual - f_qty) / denom
            errors.append(err)
            
    if errors:
        mape = np.mean(errors)
        accuracy = max(0.0, round((1.0 - mape) * 100, 2))
    else:
        accuracy = 100.0  # Default if no data
        
    return jsonify({
        'low_stock': low_stock,
        'sales_trend': trend_data,
        'forecast_vs_actual': f_vs_a_data,
        'wastage_report': [{'item_name': k, **v} for k, v in wastage_data.items()],
        'accuracy_score': accuracy
    })

@app.route('/api/ai_chat', methods=['POST'])
@login_required
def ai_chat():
    data = request.get_json()
    if not data or 'message' not in data:
        return jsonify({'error': 'Message is required'}), 400
        
    message = data['message']
    
    # 1. Fetch live context - Low stock items
    low_stock = []
    materials = db.session.query(Item, Inventory).filter(
        Item.category == 'Raw Material',
        Item.id == Inventory.item_id
    ).all()
    for item, inv in materials:
        if inv.stock_qty < inv.reorder_threshold:
            low_stock.append(f"- {item.name}: Stock {inv.stock_qty} {inv.unit} (Threshold: {inv.reorder_threshold} {inv.unit})")
    low_stock_str = "\n".join(low_stock) if low_stock else "None (all items fully stocked)"
    
    # 2. Fetch live context - Sales trend summary
    latest_sale = Sale.query.order_by(Sale.date.desc()).first()
    sales_context = ""
    if latest_sale:
        end_date = latest_sale.date
        start_date = end_date - timedelta(days=6)
        sales_in_range = Sale.query.filter(Sale.date >= start_date, Sale.date <= end_date).all()
        total_qty = sum(s.quantity_sold for s in sales_in_range)
        total_rev = sum(s.quantity_sold * s.item.price for s in sales_in_range)
        sales_context = f"Total units sold: {total_qty}, Gross Revenue: ${total_rev:.2f} (from {start_date} to {end_date})"
    else:
        sales_context = "No sales records logged yet."
        
    # 3. Fetch live context - Forecast targets for tomorrow
    tomorrow = datetime.now().date() + timedelta(days=1)
    tomorrow_forecasts = Forecast.query.filter_by(date=tomorrow).all()
    forecast_str = ""
    if tomorrow_forecasts:
        forecast_str = "\n".join([f"- {f.item.name}: Predicted bake target {f.predicted_qty} units" for f in tomorrow_forecasts])
    else:
        forecast_str = "No forecast generated yet for tomorrow."
        
    system_prompt = f"""You are the Smart Bakery AI Assistant. You have access to real-time status of the bakery:

[INVENTORY STATUS - LOW STOCK INGREDIENTS]
{low_stock_str}

[SALES METRICS - PAST 7 DAYS SUMMARY]
{sales_context}

[TOMORROW FORECAST BAKE TARGETS]
{forecast_str}

Answer the user's business query. Follow these rules:
1. Provide a professional, concise, and helpful response.
2. If inventory is low, offer to draft restock email layouts or recommend replenishments.
3. Suggest baking recipes or menu strategies based on available stock.
4. Keep the tone executive-ready and action-focused.
"""

    global has_gemini
    local_has_gemini = has_gemini
    reply = ""
    
    if local_has_gemini:
        try:
            model = genai.GenerativeModel("gemini-2.5-flash")
            response = model.generate_content([system_prompt, f"User Query: {message}"])
            reply = response.text
        except Exception as e:
            reply = f"Error calling Gemini API: {str(e)}. (Running in simulation mode fallback)"
            local_has_gemini = False
            
    if not local_has_gemini:
        # Simulation Mock Fallback Mode
        msg_lower = message.lower()
        if "stock" in msg_lower or "inventory" in msg_lower or "ingredients" in msg_lower or "reorder" in msg_lower:
            reply = f"**[AI Simulation Mode]** It looks like you're asking about inventory. Here are the items currently below their reorder threshold:\n\n{low_stock_str}\n\n**Draft Restock Order Recommendation:**\nWe should immediately place an order for these items to prevent any production halts. Would you like me to generate a supplier restock email for you?"
        elif "sales" in msg_lower or "revenue" in msg_lower or "trend" in msg_lower or "earning" in msg_lower:
            reply = f"**[AI Simulation Mode]** Here is the sales summary for the last 7 days of recorded data:\n\n* **Metrics**: {sales_context}\n\nThe trend shows healthy weekend demand. We recommend boosting Sourdough Bread production targets on Friday night to capture Saturday's peaks."
        elif "forecast" in msg_lower or "bake" in msg_lower or "tomorrow" in msg_lower:
            reply = f"**[AI Simulation Mode]** The AI forecast targets calculated for tomorrow are:\n\n{forecast_str}\n\nBaking exactly to these targets maximizes revenue efficiency and keeps wastage below 5%."
        elif "email" in msg_lower or "draft" in msg_lower or "supplier" in msg_lower:
            reply = f"**[AI Simulation Mode]** Here is a drafted restock order email:\n\n---\n**Subject**: Urgent Ingredient Restock Order - Smart Bakery\n\nDear Supplier,\n\nPlease prepare an urgent delivery of the following ingredients for Smart Bakery:\n\n* **Fresh Milk** (Current Stock: 8.0 L, Threshold: 10.0 L) - Request: 30 L\n\nBilling will be processed under account #SB-4029. Please confirm delivery estimate.\n\nBest regards,\nSmart Bakery Operations\n---"
        else:
            reply = f"**[AI Simulation Mode]** Hello! I am your AI Operations Assistant. (Note: The `GEMINI_API_KEY` is not set, so I am running in Simulation Mode).\n\nI can analyze raw materials, write supplier orders, and summarize sales data. Try asking:\n- *'Which ingredients are low in stock?'*\n- *'Show me a sales summary for the past week.'*\n- *'Write a supplier email draft for the low items.'*"
            
    return jsonify({'response': reply})

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, port=5005)
