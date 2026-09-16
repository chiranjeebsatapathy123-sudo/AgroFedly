# AgroFedly - AI-Powered Agriculture & Produce Intelligence

AgroFedly is a modern, enterprise-grade Django platform designed for intelligent agricultural operations, produce lifecycle management, and surplus food redistribution.

We provide a real-time operational digital twin of the agriculture and food supply chain ecosystem. 

## Features

- **Enterprise Organization Management**: Complete Multi-tenant architecture for Farms, Distributors, NGOs, and Food Service Organizations.
- **Predictive AI Demand Forecasting**: Advanced machine-learning integration to accurately forecast food demand and yield, dynamically adapting to local climate and consumption patterns.
- **Intelligent Operations Center**: A real-time digital twin generating actionable AI-driven operational insights, alerts, and orchestration directives.
- **Food Safety & Compliance**: End-to-end traceability of produce batches, including IoT temperature telemetry integrations and automated safety audits.
- **Logistics & Fleet Management**: Complete routing, transit tracking, status workflows, and visual delivery dashboards.
- **Automated Subsidy Matching**: Deterministic capability matching against agricultural schemes for certified farmers.

## Technology Stack

- **Core Framework**: Django 5 / Python 3.10+
- **Database**: PostgreSQL (Production ready), SQLite (Local dev fallback)
- **Caching & Brokers**: Redis for real-time WebSockets and Celery task queues.
- **Frontend**: Vanilla CSS with modern standard features (Glassmorphism, CSS Variables) + Vanilla JS.
- **Integrations**: OpenWeather API, ReportLab for automated compliance PDF generation.

## Local Setup

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
   Create a `.env` file in the project root.
   ```env
   # Core
   DEBUG=True
   SECRET_KEY=your_secret_key_here
   
   # Database (Optional - Uses SQLite by default)
   DATABASE_URL=postgres://user:pass@localhost:5432/agrofedly
   
   # Integrations
   WEATHER_API_KEY=YOUR_OPENWEATHER_KEY
   ```

5. **Initialize Database:**
   ```bash
   python manage.py migrate
   ```

6. **Start the Platform:**
   ```bash
   python manage.py runserver
   ```
   Navigate to http://127.0.0.1:8000/ to begin organization onboarding.

## Architecture & Security

- **Strict Tenant Isolation**: All queries are automatically scoped to the user's active `Organization`.
- **Role-Based Access Control**: Granular permissions via `organization_memberships`.
- **API Hardening**: Rate-limited, CSRF-protected JSON endpoints for ERP/IoT syncing.

## Deployment

AgroFedly is configured out-of-the-box for containerized PaaS deployment (Render, Heroku, AWS Elastic Beanstalk).
- Use `gunicorn` as the WSGI server: `gunicorn Fedly.wsgi:application`
- Static files are configured to use Whitenoise for efficient CDN delivery.
