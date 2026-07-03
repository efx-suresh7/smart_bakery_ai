# Smart Bakery Management System with AI-Based Demand Forecasting

A full-stack operational web application featuring automated inventory tracking, historical sales filters, machine learning-powered baking target predictions, and a Generative AI operations assistant chatbot. The UI is built using a clean, minimalist system sans-serif theme.

---

## 🔑 Default User Profiles (Auth)
Passwords are encrypted using `werkzeug.security` hashes.

| Role | Email Address | Plaintext Password |
|---|---|---|
| **Admin** (Full CRUD + Delete access) | `admin@bakery.com` | `admin123` |
| **Staff** (CRUD access without deletion) | `staff@bakery.com` | `staff123` |

---

## 🛠️ Installation & Setup

### 1. Install Dependencies
Ensure you have Python 3.8+ installed, then run:
```bash
pip install -r requirements.txt
```

### 2. Generate Synthetic Historical Data & Seed Database
This script initializes the SQLite database schema (`bakery.db`), registers the Admin/Staff users, seeds the default inventory items, and generates **90 days of synthetic daily sales records** with realistic weekday/weekend demand ratios:
```bash
python generate_data.py
```

### 3. Train the AI Model & Generate Forecasts
This script extracts calendar traits (`day_of_week`, `is_weekend`) and rolling historical metrics (`past_7_day_avg`), fits a Random Forest Regressor model from `scikit-learn`, serializes the output to `forecast_model.joblib`, and pre-populates the database's `forecasts` table with historical predictions for the dashboard charts:
```bash
python train_model.py
```

### 4. Launch the Web Application
Start the Flask development server on port 5005:
```bash
python app.py
```

Open your browser and navigate to **`http://127.0.0.1:5005/login`** to sign in!

---

## 🖥️ Screen Reference & Functional Analysis

### 1. Operations Dashboard
The main control panel serves as the central hub of the bakery. It loads visual metrics from database queries and aggregates them into charts.

![Operations Dashboard](screenshots/dashboard.png?v=2)

#### Core Functions:
- **Forecast Accuracy KPI**: Calculates the forecast accuracy percentage over the last 30 days based on historical actual sales compared to the model's predictions.
- **Sales & Revenue Trend Line Graph**: Powered by Chart.js. Dual-axis line chart illustrating the daily number of units sold (left axis, cyan) and gross revenue in dollars (right axis, pink) for the last 7 days.
- **Forecast vs. Actual Sales Bar Graph**: Side-by-side bar chart showing predicted bake targets (pink) vs. actual units sold (cyan) for the last 14 days, allowing the admin to visually monitor the model's predictive alignment.
- **Wastage Breakdown Sum**: Displays a tabular breakdown of forecasted (estimated baked) quantities vs. actual units sold per product over the last 7 days. Highlights estimated leftovers (wastage) and baking efficiency ratios.
- **Urgent Reorders Alert List**: Displays a table of raw materials whose current stock levels have fallen below their set reorder thresholds.

---

### 2. AI Assistant Chatbot
A floating chat interface in the lower right corner, styled as a modern clean popup box, designed to answer operations queries and assist with supplier orders.

![AI Assistant Chatbot](screenshots/ai_assistant.png?v=2)

#### Core Functions:
- **Real-Time Context Delivery**: Every chat query sent to the backend endpoint `/api/ai_chat` automatically queries the database to compile a report containing:
  - Any raw materials currently below reorder thresholds.
  - Sales totals and revenue figures for the last 7 days.
  - Forecasted bake targets computed for tomorrow.
- **Gemini LLM Integration**: Instructs Google's `gemini-2.5-flash` model using a custom system prompt to provide professional operations guidance, suggest menu adjustments, or draft restock orders.
- **Supplier Order Auto-Drafting**: Generates ready-to-copy email drafts to suppliers requesting order shipments for low-stock ingredients.
- **Graceful Offline Simulation Fallback**: If no `GEMINI_API_KEY` environment variable is configured, the assistant automatically shifts to an offline simulation mode. It parses query text using keyword mapping to return structured, context-appropriate responses.

---

### 3. Raw Materials Inventory Management (CRUD)
The interface for tracking ingredients (category: Raw Material) and monitoring threshold levels.

![Raw Materials Inventory](screenshots/inventory.png?v=2)

#### Core Functions:
- **Ingredient Catalog Grid**: Renders all ingredients in a table showing current stock, unit of measurement, and reorder threshold limits.
- **Status Indicator Badges**: Automatically flags rows with a red highlight and displays a "Low Stock" warning badge if current stock drops below the reorder threshold.
- **Modals for Add/Edit**: Intercepts user inputs using inline overlays to add new ingredients or modify current stock levels.
- **Admin Deletion Gate**: Inspects the user's role stored in the Flask session. Displays the red trash icon and allows item deletion only for users with the "Admin" role (disables the action for "Staff" users).

---

### 4. Sales Logging & History Filters
Allows staff to record customer purchases and view historical database logs.

![Sales Records and History](screenshots/sales.png?v=2)

#### Core Functions:
- **Record Purchase Entry**: Form input to log daily customer transactions (Dropdown product list, Date selection, and Qty sold). Updates database tables and retrains models accordingly.
- **Logs Filter Query**: Search options allowing you to narrow down the sales log table by a specific product, start date, or end date.
- **Revenue Computation**: Automatically multiplies quantities sold by the corresponding product pricing and shows the total gross revenue.

---

### 5. scikit-learn AI Forecasting
The trigger page to generate Recommended Bake Lists for any calendar date.

![Bake Forecasting Screen](screenshots/forecast.png?v=2)

#### Core Functions:
- **Future Date Predictor**: Allows staff to pick any date (defaults to tomorrow) and request baking recommendations.
- **Feature Math Processing**:
  - Dynamically calculates the weekday index and sets the `is_weekend` flag.
  - Queries the sales table to compute the average units sold for each product over the 7 days prior to the target date.
  - Maps these into the serialized `RandomForestRegressor` (`forecast_model.joblib`).
- **Baking Recommended List**: Displays the optimal quantity of units to bake, unit prices, and potential revenue.
- **Advisory Warnings**: Flags weekend shifts to highlight holiday demand changes.
- **Print Optimization**: Integrates CSS print media rules, allowing users to print a paper copy of the baking target sheet for kitchen staff.
