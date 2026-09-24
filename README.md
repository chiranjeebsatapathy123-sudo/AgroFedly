# AgroFedly 🌱
**AI-Powered Agriculture, Supply Chain & Produce Intelligence Platform**

AgroFedly is a modern, enterprise-grade Django platform engineered to provide a real-time, digital twin of the entire agricultural and food supply chain ecosystem. 

It connects farmers, logistics drivers, commercial kitchens, and NGOs into a single, unified, AI-driven traceability layer.

---

## 🏗️ Architecture & Ecosystem Flow

AgroFedly powers the food lifecycle through five interconnected modules, orchestrated via a robust ASGI + Postgres + AI backend architecture.

```mermaid
graph TD
    %% Styling
    classDef client fill:#f8fafc,stroke:#cbd5e1,stroke-width:2px,color:#0f172a
    classDef proxy fill:#f1f5f9,stroke:#94a3b8,stroke-width:2px,color:#0f172a
    classDef django fill:#10b981,stroke:#047857,stroke-width:2px,color:white
    classDef db fill:#3b82f6,stroke:#1d4ed8,stroke-width:2px,color:white
    classDef ml fill:#8b5cf6,stroke:#6d28d9,stroke-width:2px,color:white
    
    %% Actors
    Browser["🌐 Web Client<br/>(Glassmorphism UI, JS, Leaflet Maps)"]:::client
    Nginx["🛡️ Reverse Proxy<br/>(Nginx / Caddy)"]:::proxy
    
    %% Backend
    subgraph AgroFedly Core
        Daphne["⚡ ASGI Server (Daphne/Gunicorn)"]:::django
        Django["🚀 Django + Channels"]:::django
        
        %% Workspaces
        Agri["🌱 Agriculture"]:::django
        Kitch["🍳 Kitchen"]:::django
        Logis["🚚 Logistics"]:::django
        Redis["🤝 Redistribution"]:::django
    end

    %% Data Layer
    Postgres[("🐘 NeonDB PostgreSQL<br/>(Strictly Enforced)")]:::db
    RedisDB[("🔴 Redis<br/>(WebSockets & Cache)")]:::db
    
    %% ML Layer
    subgraph AI/ML Engine
        WeatherAI["☁️ Weather Forecast AI"]:::ml
        AttendAI["👥 Attendance Forecast AI"]:::ml
        NutriAI["🍎 Nutrition Physics AI"]:::ml
        SafetyAI["🌡️ Food Safety Classifier"]:::ml
    end
    
    %% Connections
    Browser <-->|HTTPS / WSS| Nginx
    Nginx <--> Daphne
    Daphne <--> Django
    
    Django --> Agri
    Django --> Kitch
    Django --> Logis
    Django --> Redis
    
    Django <--> Postgres
    Django <--> RedisDB
    
    Kitch -.-> AttendAI
    Agri -.-> WeatherAI
    Kitch -.-> NutriAI
    Redis -.-> SafetyAI
```

## ✨ Core Workspaces

1. **Agriculture (Farmers & FPOs)**: Field management, IoT telemetry, AI weather forecasts, crop disease scanning, and automated subsidy matching.
2. **Kitchen (Enterprise & Commercial)**: AI-driven attendance forecasting to minimize waste, automated nutrition calculations via Physics ML, and direct produce ordering.
3. **Logistics (Fleet & Routing)**: Live CARTO-integrated mapping, vehicle registration, driver safety tracking, and delivery route optimization.
4. **Redistribution (NGOs)**: Matching surplus food with local NGOs using our AI Food Safety Classifier (detecting spoilage risk via storage temp/duration) to guarantee safe donations.
5. **Traceability & Analytics**: An unbreakable ledger tracking food custody from soil to consumption.

---

## 🧠 Machine Learning Engine

AgroFedly features 4 production-ready AI models trained on bespoke datasets:
* **Attendance Forecast AI (`attendance_bundle.pkl`)**: Predicts expected daily meal attendance based on calendar features (holidays, exams, weekends) using a RandomForestRegressor.
* **Weather Forecast AI (`weather_bundle.pkl`)**: A multi-output time-series Random Forest predicting local Temperature, Humidity, and Rainfall.
* **Nutrition Physics AI (`nutrition_bundle.pkl`)**: Linear Regression model that mathematically learned the exact biological caloric weights of macronutrients (Protein/Carbs/Fat).
* **Food Safety AI (`food_safety_bundle.pkl`)**: A RandomForestClassifier achieving 99.95% accuracy in flagging surplus food as High/Medium/Low risk based on real storage telemetries.

---

## 🛠️ Technology Stack

- **Framework**: Django 5 / Python 3.10+
- **Database**: PostgreSQL (NeonDB Serverless integration mandatory; SQLite fallback permanently disabled)
- **Caching & WebSockets**: Redis & Django Channels
- **Frontend**: Vanilla CSS + Glassmorphism Design System + Chart.js + CARTO Maps
- **AI/ML**: `scikit-learn`, `pandas`, `joblib`

---

## 🚀 Local Development Setup

1. **Clone the repository:**
   ```bash
   git clone <repository>
   cd AgroFedly
   ```

2. **Create and activate a virtual environment:**
   ```bash
   # Windows
   python -m venv venv
   venv\Scripts\activate
   
   # Linux/macOS
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Environment Variables (.env):**
   AgroFedly **requires** a valid PostgreSQL connection to run. SQLite fallback has been removed for strict consistency.
   ```env
   # Core
   DJANGO_DEBUG=1
   DJANGO_SECRET_KEY=your_secret_key_here
   
   # Database (STRICTLY REQUIRED)
   DATABASE_URL=postgresql://user:pass@host/dbname
   
   # Integrations (Optional)
   WEATHER_API_KEY=YOUR_OPENWEATHER_KEY
   CARTO_API_KEY=YOUR_CARTO_KEY
   ```

5. **Start the Platform:**
   ```bash
   python manage.py runserver
   ```
   Navigate to `http://127.0.0.1:8000/` to begin!

## 🔐 Architecture & Security

- **Strict Tenant Isolation**: All queries are automatically scoped to the user's active `Organization`.
- **Role-Based Access Control**: Granular permissions preventing Farmers from accessing Kitchens, and vice versa.
- **API Hardening**: CSRF-protected JSON endpoints for ERP/IoT syncing.
