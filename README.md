# 🚁 Drone Operations Coordinator AI Agent

An intelligent agent system for managing drone operations, pilot roster, drone inventory, and mission assignments with Google Sheets integration.

## 🌟 Features

### 1. **Roster Management**

- Track pilot availability by skill, certification, and location
- Update pilot status (Available/On Leave/Unavailable) with Google Sheets sync
- View current assignments and availability

### 2. **Assignment Tracking**

- Match pilots to projects based on requirements (skills, certifications, location)
- Track active assignments
- Handle urgent reassignments with cascading reassignment logic

### 3. **Drone Inventory**

- Query fleet by capability, availability, and location
- Track deployment status
- Flag maintenance issues and upcoming maintenance
- Update drone status with Google Sheets sync

### 4. **Conflict Detection**

- Double-booking detection (pilot or drone assigned to overlapping projects)
- Skill/certification mismatch warnings
- Equipment-pilot location mismatch alerts
- Maintenance schedule conflicts

### 5. **Urgent Reassignment Handling**

- Priority-based preemption for urgent missions
- Cascading reassignment to minimize disruption
- Proximity optimization for rapid deployment
- Skill similarity matching when exact matches unavailable

## 🏗️ Architecture

Frontend (Streamlit) → Backend (FastAPI) → Google Sheets API
↑ ↑
User Interface Business Logic
↑
Specialized Agents
(Roster, Inventory, Assignment, Conflict)

### Tech Stack

- **Backend**: FastAPI (Python) - Async API with automatic OpenAPI docs
- **Frontend**: Streamlit - Conversational interface with real-time updates
- **Google Sheets**: gspread library for 2-way sync
- **Data Processing**: Pandas for CSV operations and matching logic
- **Deployment**: Railway/Replit for easy hosting

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Google Cloud Service Account with Sheets API access
- Google Sheet with three tabs: `pilot_roster`, `drone_fleet`, `missions`

### Local Development

1. **Clone and setup**

```bash
git clone <repository-url>
cd drone-coordinator-agent
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```
