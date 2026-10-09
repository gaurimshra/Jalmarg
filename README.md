# JalMarg (जलमार्ग)

JalMarg is a next-generation urban waterlogging detection and routing platform designed for municipal emergency orchestration. Utilizing the official Strands Agentic Framework and Google Gemini 1.5, JalMarg automates the process of handling raw citizen photo reports, analyzing structural threats, scoring hotspot risks, mapping deterministic safe-routing schemas, and generating accountable dispatch proposals for human authorities.

## The Problem
During severe storms, municipalities receive thousands of crowdsourced reports simultaneously. Human operators physically cannot verify every image stream, identify duplicate fakes, analyze depth variations manually, lookup correlated weather data, and coordinate local pumping assets safely in real-time. Emergency vehicles route themselves into hazards attempting to provide assistance blindly.

## Architecture
JalMarg fixes structural bottlenecks by acting as an asynchronous, deterministic edge proxy using LLMs securely:
- **Frontend Stack**: Built cleanly in Next.js 14, TailwindCSS, and MapLibre GL for client-side geospatial rendering.
- **Backend Stack**: Powered by Python FastAPI, SQLite + SQLAlchemy, processing RESTful hooks seamlessly.
- **Agent Integration**: An autonomous Supervisor Agent governed entirely by `strands-agents` tools boundaries natively queries `Gemini 1.5` sequentially resolving tasks based strictly on bounded steps.
- **Live Geospatial Tooling**: Fully integrated with public OSRM mapping geometries allowing algorithmic exposure matrices.

*(View the complete technical schematic inside `docs/architecture.md`)*

---

## Features
- ✅ **Perceptual Node Hashing**: Automatically prevents crowdsourced duplicate/faked spam imagery locally.
- ✅ **Multi-Modal Vision Recognition**: Estimates visible flood depths and confidence parameters from citizen reports. 
- ✅ **Algorithmic Hazard Aggregation**: Continuously parses surrounding live-API localized weather updates bounding to live risk tables.
- ✅ **Flood-Conscious Routing**: Calculates dynamic geospatial route deviations. Sedans are blocked from critical water hotspots while high-clearance SUVs are permitted safe passage. 
- ✅ **Dispatch Proposals**: Supervisor agent formulates exact emergency protocols based on external advisory fetches.
- ✅ **Authority Fallbacks**: 100% human-in-the-loop dashboard execution. Real-time deterministic fallback mechanisms catch the system safely if APIs disconnect ensuring zero service blocks.

---

## Setup & Run Instructions (Windows 11)

### 1. Prerequisites
- **Python 3.10+**
- **Node.js 18+** 
- **Git**

### 2. Environment Variables
Create a file named `.env` locally in the `backend/` directory:
```
# /backend/.env
GEMINI_API_KEY="AIzaSy... (Optional)"
TINYFISH_API_KEY="TF.123... (Optional)"
DEMO_MODE=True
```
*(If keys aren't supplied, JalMarg gracefully diverts all queries into a local Deterministic System caching pipeline, perfectly matching Hackathon simulation rules).*

### 3. Backend Setup
Execute sequentially inside your PowerShell prompt:
```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python scripts/init_db.py
uvicorn app.main:app --reload --port 8000
```
*(Ensure `init_db.py` mounts the `jalmarg.db` file securely without failures).*

### 4. Frontend Setup
Open a distinct secondary PowerShell prompt:
```powershell
cd frontend
npm install
npm run dev
```

### 5. Start Testing!
Navigate your browser to `http://localhost:3000`. You are ready for operations.

### 6. Test Commands
To run the full backend testing suite with mock verifications:
```powershell
cd backend
pytest tests/ -s
```

---

## 🔑 How to Obtain Optional API Keys
JalMarg thrives on LLM and external retrieval services:
1. **Google Gemini API Key**: Visit [Google AI Studio](https://aistudio.google.com/) to acquire a free key. This activates live image-depth verification and autonomous Strands orchestration.
2. **TinyFish Search Key**: (If applicable to your organization) Request an API credential from the civic retrieval platform to enable the Supervisor Agent to parse live PDF instructions internally.
If these keys are left empty, the application automatically pivots to the deterministic mock pipeline smoothly.

---

## 📂 Project Structure
```text
jalmarg/
├── backend/
│   ├── app/           # FastAPI application (routers, schemas, deps)
│   ├── data/          # Uploaded citizen media
│   ├── scripts/       # DB initialization & seeding tools
│   └── tests/         # Pytest integrations & tool assertions
├── frontend/
│   ├── src/app/       # Next.js 14 structured page routing
│   ├── src/components/# MapLibre / Dashboard widgets
│   └── public/        # Static assets
├── docs/              # Comprehensive Architecture schemas
└── demo/              # Demonstration execution scripts
```

---

## 📊 Dataset Description
The database is pre-seeded with synthesized Indian urban points designed to illustrate high-risk terrain modeling (e.g., Connaught Place Underpasses). 
- **Coordinates**: Anchor inside New Delhi limits.
- **Mock Events**: We use dummy weather/rainfall hashes for non-API test loops.
- **Map Visualizations**: Rely on `OpenFreeMap` open-source tiles preventing API-key exhaustion during evaluations.

---

## 🌐 Core API Endpoints
| Protocol | Route | Description |
|---|---|---|
| `POST` | `/api/reports/` | Accepts citizen Image uploads (multipart) & engages the Master Strands Agent. |
| `GET` | `/api/hotspots/` | Returns clustered vulnerability zones. |
| `POST` | `/api/routes/compare` | Takes an Origin, Destination, and Vehicle type. Returns an Exposure Matrix via OSRM geometries. |
| `PATCH` | `/api/admin/dispatch-plans/{id}/status` | Intercepts Human "Approve/Reject" clicks handling Emergency Protocols natively. |

---

## Technical Limitations & Policies
- **API Mocks**: To adhere strictly to evaluation rules, JalMarg provides comprehensive offline-mock logic protecting all critical integrations (OSRM, Open-Meteo, Gemini, TinyFish). Seeded testing elements render distinctly under `DEMO` indicators.
- **Data Retention**: SQLite destroys its transient tracking footprint per standard deployment upon cache clearances. The system does not directly retain massive multi-part image loads indefinitely.
- **Emergency Constraints**: JalMarg is an investigational software prototype demonstrating Agent logic constraints. **Do not use this software for live life-critical routing deployments**.
