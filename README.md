# Breathe ESG Data Normalization Pipeline

A full-stack prototype for ingesting, normalizing, and verifying multi-source carbon emissions data. 

This system handles the messy reality of enterprise ESG reporting. It takes inconsistent data from SAP exports, utility portals, and corporate travel platforms, normalizes the units to standard kgCO2e, and provides a clean human-in-the-loop audit dashboard for verification.

## Prerequisites

Before you begin, ensure you have the following installed on your machine:
- [Python 3.10+](https://www.python.org/downloads/)
- [Node.js 18+](https://nodejs.org/)
- Git

## Local Setup Instructions

Follow these exact steps to get the development environment running on your local machine.

### 1. Clone the Repository
Open your terminal and clone this project to your local machine.

```bash
git clone [https://github.com/20omkale/breathe-esg-mrv-prototype.git](https://github.com/20omkale/breathe-esg-mrv-prototype.git)
cd breathe-esg-mrv-prototype
```

### 2. Backend Setup (Django)
Isolate the Python dependencies using a virtual environment and initialize the database. Run these commands from the root project directory:

**Create and activate the virtual environment:**

```bash
# For Windows
python -m venv env
env\Scripts\activate

# For Mac/Linux
python3 -m venv env
source env/bin/activate
```

**Install dependencies and prepare the database:**

```bash
pip install django djangorestframework django-cors-headers
python manage.py makemigrations
python manage.py migrate
```

**Create an admin account:**
You must create a superuser to access the Django admin panel and manage tenant companies.

```bash
python manage.py createsuperuser
```
*(Follow the terminal prompts to set your username and password).*

**Start the backend server:**

```bash
python manage.py runserver
```
The backend API is now running at `http://127.0.0.1:8000/`. Keep this terminal window open.

### 3. Frontend Setup (React + Vite)
Open a brand new terminal window, navigate back to the root `breathe-esg-mrv-prototype` folder, and run these commands to start the user interface:

```bash
cd frontend
npm install
npm run dev
```
The React dashboard is now running at `http://localhost:5173/`.

## How to Test the Application

To properly evaluate the data ingestion logic, you must configure a test environment before uploading any files.

1. **Create a Tenant Company:** Navigate to `http://127.0.0.1:8000/admin/` in your browser. Log in with your superuser credentials and create a new Company (e.g., "Acme Corp"). This ensures the database has a tenant to attach the incoming emission records to.
2. **Access the Dashboard:** Open `http://localhost:5173/` in your browser.
3. **Ingest Data:** Use the dropdown menu to select a data source type. Click "Choose File" and upload the corresponding CSV file located in the `Test_Data` directory of this repository.
4. **Verify Normalization:** The pending audit table will immediately populate, demonstrating the conversion of raw inputs (Liters, kWh, km) into normalized kgCO2e based on the appropriate Scope categories.

## Deep Dive Documentation

The core of this system lies in the architecture and engineering judgment calls. Please review the included documentation files in the root directory for a complete breakdown of how this prototype was designed.

- **`MODEL.md`**: Details the schema design and the approach to multi-tenancy.
- **`DECISIONS.md`**: Covers how specific product ambiguities were resolved.
- **`TRADEOFFS.md`**: Explains what was intentionally left out for this sprint.
- **`SOURCES.md`**: Outlines the research on real-world SAP, Utility, and Travel data shapes.