# Airfare Price Index (APIx) System ✈️

A comprehensive airfare tracking, index calculation, knowledge graph, and forecasting system. The project features web scrapers, a FastAPI backend service, an ML forecasting engine, an SQLite database engine, and a standalone prototype frontend dashboard.

---

## 🚀 Key Features

*   **Real-time Fare Analytics:** Live data collection and tracking across multiple channels.
*   **APIx Calculation:** Compute Airfare Price Index against a base period (Base 2024 = 100).
*   **Machine Learning Forecasting:**
    *   Trains a RandomForestRegressor (fallback to polynomial regression) on historical fares.
    *   Predicts fares at various horizons (T+1 to T+45).
    *   Provides actionable insights for consumers (savings analysis) and market surveillance (surge risk alerts).
*   **Interactive Prototype Dashboard:**
    *   Professional, modern light-mode executive UI.
    *   Interactive moving forecast charts (7-day history + 30-day prediction).
    *   Route-Horizon Heatmap Matrix.

---

## 📁 Repository Structure

```text
airfare-index-system/
├── database/            # Central database schemas and SQLite files (airfare_index.db)
├── prototype/           # Prototyping scripts and standalone UI experiments
│   ├── index.html       # Prototype UI dashboard with responsive layout and charts
│   ├── backend.py       # Core backend index calculation & data processing
│   └── ml_forecaster.py # ML-based forecasting engine (Random Forest)
├── prototype_server.py  # FastAPI backend endpoints & live data scraping connector
├── requirements.txt     # Python backend dependencies
└── scrapers/            # Web scraping modules (if any)
```

---

## 🛠️ Tech Stack

*   **Backend:** Python, FastAPI, SQLite
*   **Machine Learning:** scikit-learn (Random Forest), NumPy, Pandas
*   **Frontend (Prototype):** HTML, Tailwind CSS, JavaScript, Chart.js, Leaflet

---

## ⚙️ Running the Prototype

1.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

2.  **Start the Backend Server:**
    ```bash
    python3 prototype_server.py
    ```
    *The server runs on `http://127.0.0.1:8000`.*

3.  **Open the Dashboard:**
    Serve `prototype/index.html` using a local web server (e.g., Live Server extension or `python3 -m http.server`) and navigate to the local address.
