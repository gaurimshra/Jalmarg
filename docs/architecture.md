# JalMarg System Architecture

## Overview
JalMarg is an intelligent urban waterlogging response platform designed to shift the burden of incident reporting from human verification to Agentic AI resolution. It connects public report inflows into deeply nested verification chains, producing deterministic flood routing scores and suggesting Dispatch Action items to municipal responders.

## System Architecture

JalMarg is structured as a decoupled monolithic application:
- **Frontend**: Next.js 14, React, TailwindCSS, MapLibre GL for client-side rendering.
- **Backend API**: FastAPI framework serving as the synchronous edge proxy.
- **Master Supervisor Framework**: The Strands SDK orchestrates asynchronous tool usage against Google's Gemini LLMs.
- **Datastore**: SQLite + SQLAlchemy managing heavily relational tracking properties.

### Database Models
- `Hotspot`: Represents geographic vulnerabilities carrying baseline and dynamic temporal risk tracking.
- `Report`: Stores individual citizen payloads (coordinates, hash verification blocks, LLM-generated depths).
- `WeatherSnapshot`: Snapshots precipitation thresholds via Open-Meteo explicitly joined locally.
- `HotspotRiskRecord`: Time-series logging of algorithmic risk updates.
- `AgentEvent`: The immutable blockchain-style ledger storing every single AI inference, human action, routing hit, or fallback parameter.
- `DispatchPlan`: AI-recommended interventions that hold an operational state, waiting for human approvals.

### Report Lifecycle & Flow
1. Citizen uploads picture alongside GeoLocation.
2. `POST /reports` accepts it.
3. Fast-tracked structural hashing (SHA256, Perceptual Hashing) is applied deterministically.
4. The Master Supervisor `orchestrator.py` receives the payload ID.
5. The LLM steps in (or the Fallback processor): Verify $\rightarrow$ Multimodal Vision Severity $\rightarrow$ Hotspot Risk update $\rightarrow$ Dispatch determination.
6. The frontend `/authority` dashboard pulses, revealing the AI's step-by-step logic and the requested Dispatch Action.
7. Human Authority interacts with the DispatchPlan, updating DB states identically.

### Agent/Tool Architecture
`Strands SDK` acts as the backbone. The core Agent Tools include:
- `verify_report`: Invokes perceptual analysis bounds.
- `estimate_water_severity`: Sends arrays to Gemini for multi-modal water depth estimation.
- `get_rainfall_forecast`: Harvests localized data from Open-Meteo.
- `calculate_hotspot_risk`: Calculates custom weighted sums factoring temporal decays.
- `compare_routes`: Checks vehicle tolerance (SUV vs Hatchback) against live geospatial mapping via OSRM.
- `retrieve_civic_guidance`: Pings TinyFish API bounding the response rules.

### Risk-Scoring Engine
Risk updates continuously adapt based on an amalgamation of factors: Base elevation susceptibility + live weather parameters + density of corroborated true-reports - timeline decay factors. A formula caps individual biases, protecting against automated report bombing overriding the weather models structurally.

### Routing Method
We lean heavily into `OSRM` and `Shapely`. By extracting bounding lines around known Hazard hotspots, we query the exact route geometries of citizen's requested paths. If their vehicle profile intercepts too deeply into the Hazard Radius, we output explicit vulnerability scores.

### Error-Handling & Fallback Strategy
**JalMarg operates offline-first by design for Hackathon resiliency:**
- If the `GEMINI_API_KEY` is missing, `deterministic_fallback` replicates the entire analysis payload via rules-based programming instantaneously logging `DETERMINISTIC FALLBACK`.
- Weather queries fallback to seeded arrays gracefully.
- OSRM calls utilize predefined polyline structures on timeout.
- TinyFish queries pivot into a local JSON advisory struct natively.

### Security and Limitations
The application is purely local, currently running non-production boundaries: SQLite is utilized. Security mechanisms assume demo-environments and operate purely for verification of Agentic Orchestrations, prioritizing explicit data trails (`AgentEvent`) for debugging over actual end-to-end TLS lockdowns.
