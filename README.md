# Breathe ESG Data Normalization Pipeline

A full-stack prototype for ingesting, normalizing, and verifying multi-source carbon emissions data.

## Overview

This system handles the messy reality of enterprise ESG reporting. It takes inconsistent data from SAP exports, utility portals, and corporate travel platforms, normalizes the units to standard kgCO2e, and provides a clean human-in-the-loop audit dashboard for verification. 

## The Tech Stack

**Backend:** Django, Django REST Framework, SQLite
**Frontend:** React, Vite, Axios
**Architecture:** Multi-tenant database design with strict source-of-truth tracking.

## Deep Dive Documentation

The core of this system lies in the architecture and engineering judgment calls. Please review the included documentation files in the root directory for a complete breakdown of how this prototype was designed.

1. MODEL.md details the schema design and the approach to multi-tenancy.
2. DECISIONS.md covers how specific product ambiguities were resolved.
3. TRADEOFFS.md explains what was intentionally left out for this prototype sprint.
4. SOURCES.md outlines the research on real-world SAP, Utility, and Travel data shapes.

## Running Locally

Clone the repository and install the backend dependencies using your preferred Python virtual environment. Run the Django migrations and start the server on port 8000. 

For the frontend, navigate to the React folder, install the NPM packages, and start the Vite development server. You must create a test company in the Django admin panel before attempting to upload any CSV data through the dashboard.