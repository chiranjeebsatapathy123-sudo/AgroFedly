# Smart India Hackathon (SIH) 2026 - Demonstration Flow

**Duration:** ~3 Minutes
**Goal:** Prove the platform is a fully integrated, real-time AI solution for the agriculture to surplus redistribution pipeline.

## 1. Environment Reset (Pre-Pitch)
Run the following commands to ensure a perfectly clean and deterministic environment for the judges.
```bash
python manage.py clear_demo_data
python manage.py seed_demo_data
```

## 2. Login & The Command Center (0:00 - 0:45)
- Navigate to `http://localhost:8000` (or the production domain) and click Login.
- **Login Credentials:** `sih_admin` / `sih2026`.
- You will land on the **Operations Dashboard**. 
- **Talking Point:** "AgroFedly is not a collection of static pages; it's a real-time command center for the entire food lifecycle. The dashboard you see here aggregates live data across farms, warehouses, and NGOs."
- **Action:** Open the Global Command Palette by pressing `Ctrl + K`. Search for "Surplus" and hit Enter.

## 3. Intelligent Surplus & Safety (0:45 - 1:30)
- You are now on the **Surplus Food List**.
- **Action:** Point out the `AI_Freshness_Score` on the `SIH Excess Produce` item.
- **Talking Point:** "Before any food is redistributed, our AI evaluates its safety based on visual quality and IoT temperature logs. We enforce a strict safety gate—unsafe food cannot be mathematically selected for human redistribution."

## 4. The AI Copilot & Real-Time Logistics (1:30 - 2:15)
- **Action:** Open the **AgroFedly AI Copilot** (bottom right).
- **Type/Speak:** "Check the delivery status of the surplus produce to the NGO."
- **Talking Point:** "Our AI is deterministic. It doesn't just chat; it queries the live PostgreSQL database securely and can execute staged actions."
- **Action:** Click on the Delivery link provided by the Copilot. This takes you to the **Delivery Live Tracking** page.
- **Talking Point:** "Notice the live map and IoT telemetry. If a truck's temperature spikes above 5 degrees, this WebSocket connection instantly alerts the driver and the recipient NGO."

## 5. Traceability Ledger & Impact (2:15 - 3:00)
- **Action:** From the Delivery page, click "View Traceability Ledger".
- **Talking Point:** "Trust is paramount. AgroFedly maintains an immutable, cryptographically secured Chain of Custody. Every handoff, temperature reading, and quality check is hashed to the previous state, preventing fraud in the supply chain."
- **Action:** Navigate to the **Impact Dashboard** via the sidebar.
- **Talking Point:** "By connecting agriculture with real-time intelligence, we turn potential waste into measurable impact."

## 6. End Presentation
- Field questions.
- If they ask to see a feature, use `Ctrl+K` to jump to it instantly.
