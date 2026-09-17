# AgroFedly Intelligence Architecture

This document describes the architectural flow of data and intelligence through the AgroFedly operations platform, established in Phase 31.

## Core Principles
1. **Single Source of Truth**: All operational metrics (e.g., total surplus, safe surplus) are calculated by dedicated Service classes, ensuring consistency across dashboards, APIs, and background jobs.
2. **Real Data First**: The AI Orchestrator and Alerting systems derive insights exclusively from actual database records (e.g., `SystemEvent`, `IoTTemperatureReading`, `StorageRecord`), eliminating fabricated data or mock alerts.
3. **Tenant Isolation**: Every service is instantiated with an `Organization` context, physically preventing cross-tenant data leakage in operations and forecasts.

## Service Layer

The business logic has been extracted from Django views into `feedly/services/`:

### 1. `DataQualityEngine` (`feedly/services/data_quality.py`)
- **Purpose**: Audits the database for anomalies, negative capacities, orphaned records, and stale states.
- **Integration**: Feeds directly into the `AIOrchestrator` to generate high-priority data quality alerts for administrators.

### 2. `SurplusCalculator` (`feedly/services/surplus.py`)
- **Purpose**: Authoritatively aggregates surplus totals and calculates operational priority scores based on storage time, temperature, and quantity.
- **Integration**: Used by `dashboard.py` and `intelligence.py` to render consistent KPIs.

### 3. `RecipientMatchingEngine` (`feedly/services/matching.py`)
- **Purpose**: Ranks available recipients for a given surplus batch using capacity, distance, and urgency.
- **Integration**: Exposes a transaction-safe `allocate_surplus` method using `select_for_update()` to prevent concurrent over-allocation.

### 4. `DemandForecastingPipeline` (`feedly/services/forecasting.py`)
- **Purpose**: Houses the ML and heuristic forecasting logic.
- **Integration**: Replaces standalone view logic. It natively integrates with the `DemandForecast` model, making it reusable by Celery background jobs.

## Background Automation

Scheduled Celery tasks (`feedly/tasks.py`) ensure the platform remains continuously updated:
- `refresh_organization_forecasts`: Nightly refresh of demand predictions.
- `run_data_quality_audit`: Nightly sweep for data corruption or process bottlenecks, injecting findings as `SystemEvent` records.

## State Management & Traceability

### Delivery State Machine
The `Delivery` model enforces a strict, immutable state machine in its `save()` method, rejecting illegal transitions (e.g., moving from `DELIVERED` back to `PENDING`).

### Produce Traceability Ledger
The `ProduceTraceabilityLedger` is heavily integrated into the `RecipientMatchingEngine` and `FoodSafety` modules, ensuring an unbroken, cryptographically robust chain of custody for every transaction and quality check.
