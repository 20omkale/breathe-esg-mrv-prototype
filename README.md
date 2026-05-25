# Breathe ESG Data Normalization Pipeline

A full-stack prototype for ingesting, normalizing, and verifying multi-source carbon emissions data. 

This system handles the messy reality of enterprise ESG reporting. It takes inconsistent data from SAP exports, utility portals, and corporate travel platforms, normalizes the units to standard kgCO2e, and provides a clean human-in-the-loop audit dashboard for verification.

---

## 🚀 Live Demo & Evaluator Access

You do not need to run this locally to evaluate the prototype. The application is fully deployed and connected to a persistent cloud database.

* **Frontend Dashboard (Vercel):** https://breathe-esg-mrv-prototype.vercel.app
* **Backend Admin Panel (Render):** https://breathe-esg-backend-nnxo.onrender.com/admin/

**Admin Credentials:**
The production database uses an automated seeding script upon deployment. You can log into the Django admin panel using these pre-configured credentials:
* **Username:** admin
* **Password:** Breathe2026!

**How to Test:**
1. Open the Frontend Dashboard.
2. The UI will autonomously connect to the live database and fetch the pre-seeded tenant company ("ABC Construction PVT. LTD").
3. Use the dropdown to select a data source.
4. Upload one of the sample CSV files located in the `Test_Data` directory of this repository.
5. Watch the system normalize raw inputs (Liters, kWh, km) into standard kgCO2e in the pending audit table.

---

## 🏗️ Production Architecture Highlights

This project was built to simulate a robust, real-world deployment environment, moving past standard hackathon shortcuts:
* **Decoupled Client/Server:** React frontend deployed to Vercel edge networks, communicating securely with a Django REST API on Render.
* **Autonomous Database Seeding:** Python scripting safely handles initialization of superusers and tenant contexts in ephemeral cloud environments.
* **Dynamic Environment Fallbacks:** Frontend implements secure environment variables (`VITE_API_URL`) with hardcoded fallbacks to prevent runtime crashes during cloud sleep cycles.
* **Persistent Cloud Infrastructure:** Migrated from local SQLite to a fully managed **Neon PostgreSQL** database to ensure data persistence across server restarts.
* **Resilient Data Parsing:** Backend endpoints utilize custom safe-parsing utility functions to gracefully handle empty cells or malformed text strings in real-world CSV uploads.

---

## 💻 Local Setup Instructions

If you wish to run the development environment locally, follow these steps:

### 1. Clone the Repository

```bash
git clone [https://github.com/20omkale/breathe-esg-mrv-prototype.git](https://github.com/20omkale/breathe-esg-mrv-prototype.git)
cd breathe-esg-mrv-prototype
```

### 2. Backend Setup (Django)
Isolate the Python dependencies using a virtual environment and initialize the database.

```bash
# Create and activate virtual environment (Windows)
python -m venv env
env\Scripts\activate

# For Mac/Linux
# python3 -m venv env
# source env/bin/activate

# Install dependencies and prepare the database
pip install -r requirements.txt
python manage.py migrate

# Seed the database and start the server
python seed_db.py
python manage.py runserver
```
The backend API is now running at http://127.0.0.1:8000/.

### 3. Frontend Setup (React + Vite)
Open a new terminal window and navigate to the frontend folder.

```bash
cd frontend
npm install
npm run dev
```
The React dashboard is now running at http://localhost:5173/. Create a `.env` file in the frontend directory with `VITE_API_URL=http://127.0.0.1:8000/api` to connect to your local backend.

---

## 📖 Deep Dive Documentation

The core of this system lies in the architecture and engineering judgment calls. Please review the included documentation files in the root directory for a complete breakdown of how this prototype was designed.

- **`MODEL.md`**: Details the schema design and the approach to multi-tenancy.
- **`DECISIONS.md`**: Covers how specific product ambiguities were resolved.
- **`TRADEOFFS.md`**: Explains what was intentionally left out for this sprint.
- **`SOURCES.md`**: Outlines the research on real-world SAP, Utility, and Travel data shapes.