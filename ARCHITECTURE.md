# AgroFedly Architecture

AgroFedly is designed to be a highly responsive, real-time platform using the ASGI architecture.

## High-Level Architecture Diagram

```text
                    ┌──────────────────┐
                    │     Browser      │
                    │ (HTML / JS / 3D) │
                    └────────┬─────────┘
                             │
                  HTTPS (AJAX) / WSS (WebSocket)
                             │
                    ┌────────▼─────────┐
                    │   Reverse Proxy  │
                    │ (Nginx / Caddy)  │
                    └────────┬─────────┘
                             │
                    ┌────────▼─────────┐
                    │  ASGI Server     │
                    │  (Daphne)        │
                    └────────┬─────────┘
                             │
                    ┌────────▼─────────┐
                    │ AgroFedly Django │
                    │   + Channels     │
                    └──────┬─────┬──────┘
                           │     │
                    ┌──────▼─┐ ┌─▼──────┐
                    │Postgres│ │ Redis  │
                    └────────┘ └────────┘
                           │
                    ┌──────▼───────────┐
                    │ AI / ML Engine   │
                    │ (scikit-learn /  │
                    │  OpenAI API)     │
                    └──────────────────┘
```

## Business Architecture Flow (Ecosystem)

AgroFedly operates on a unified flow spanning from farm-level agriculture down to community redistribution and analytics:

```text
                    AGROFEDLY
                        │
          ┌─────────────┴─────────────┐
          │                           │
     AGRICULTURE                 PRODUCE LIFECYCLE
          │                           │
     Farm Management             Harvest
     Field Management                ↓
     Crop Intelligence          Quality Check
     Weather                         ↓
     Disease                    Processing
     Yield AI                         ↓
     IoT                         Storage
          │                           ↓
          └──────────────→ Marketplace
                                  │
                                  ↓
                             Distribution
                                  │
                  ┌───────────────┼───────────────┐
                  ↓               ↓               ↓
               Kitchen       Redistribution    Logistics
                  │               │               │
                  └───────────────┴───────────────┘
                                  ↓
                            TRACEABILITY
                                  ↓
                              ANALYTICS
```

## Components

### 1. The Browser (Experience Manager)
The frontend uses vanilla Javascript wrapped in a lightweight `ExperienceManager` that intercepts all navigation. This allows the application to function identically to a Single Page Application (SPA), providing cinematic transitions without the heavy footprint of React or Vue.

### 2. The ASGI Application
Because AgroFedly utilizes WebSockets for real-time notifications (deliveries, surplus matching), the traditional WSGI interface is insufficient. We use **Django Channels** and deploy with **Daphne**, allowing the same server process to handle both standard HTTP requests and long-lived WebSocket connections.

### 3. PostgreSQL Database
All relational data is stored in PostgreSQL. Concurrency is strictly managed in critical paths (e.g., surplus redistribution) using `transaction.atomic()` and `select_for_update()`.

### 4. Redis Channel Layer
Redis is the backbone of the real-time event system. When a model changes (e.g., `Delivery` status updates), a Django `post_save` signal fires, dumping the event to Redis. The Channels consumers listen to Redis and push JSON events down to the connected clients via WebSockets.

### 5. AI & ML Engine
- **Predictive Models:** Pre-trained `scikit-learn` models (`demand_bundle.pkl`) are loaded into memory on server boot. This prevents heavy initialization costs per request.
- **Generative AI:** The AgroFedly Copilot interacts with the OpenAI API for natural language understanding. Tool definitions strictly enforce deterministic routing and staging of actions.
