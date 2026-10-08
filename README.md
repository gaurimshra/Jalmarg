# 🌊 JalMarg (जलमार्ग)

**Agentic AI for urban waterlogging: verify it, measure it, predict it, route around it.**

> Built for **Environmental Hacks**, WeMakeDevs x AWS Bharat Builds Tour (Oct 8-11, 2026)
> Track: **Heat and Water** (floods, monsoon waterlogging)

---

## The problem

Every monsoon in Delhi-NCR, cars get submerged in underpasses and people get stranded. Navigation apps show traffic, but not **how deep the water is on a road right now**, and nobody warns you **before** a low-lying spot floods.

Existing flood systems either need expensive sensors (NYC FloodNet, Singapore PUB) or trust unverified crowd reports (PetaBencana.id). Both fall short for Indian cities.

## What JalMarg does

JalMarg is a multi-agent AI system that turns a single citizen photo into a verified, depth-estimated, forecast-aware flood map, and routes people around it based on **their vehicle**.

1. **Report:** a citizen sends a photo (or a Hindi voice note) of a flooded road.
2. **Verify:** an agent checks if the photo is real, recent, at the claimed location, and not reused or AI-generated. It outputs a trust score.
3. **Measure:** a vision model estimates water depth using reference objects (tyre, kerb, door height) with a confidence score.
4. **Predict:** a forecasting agent combines terrain, rainfall nowcasts and past floods to warn *before* water arrives.
5. **Route:** the router returns a fastest vs safest path, personalised to a bike, hatchback or SUV.
6. **Act:** a dispatcher agent suggests pump deployment, and a human approves it.

## AI / ML at the core

| Layer | Technique | Purpose |
|---|---|---|
| Vision-LLM reasoning | Amazon Bedrock multimodal model | Depth estimation from reference objects, with reasoning and confidence |
| Flood segmentation | Fine-tuned SegFormer / U-Net on public flood-image datasets | Pixel-level water mask, a second opinion on depth |
| Depth regression | Gradient boosting / small CNN head on mask + object features | Calibrates depth against LLM estimates |
| Image forensics | EXIF/GPS validation, error-level analysis, perceptual-hash duplicate search, AI-generated image detector | Trust score per report |
| Flood risk prediction | LightGBM / XGBoost on terrain (TWI, flow accumulation), rainfall and report history | Per-hotspot flood probability |
| Nowcasting | Open-Meteo + NASA GPM IMERG rainfall fusion | Short-term alerts (e.g. "likely to flood in ~30 min") |
| Anomaly detection | Isolation Forest on report streams | Spots fake report floods and sensor glitches |
| Agentic orchestration | Strands Agents SDK, multi-agent supervisor pattern | Autonomous observe → reason → tool → act loops |
| Retrieval (RAG) | Bedrock Knowledge Bases over drainage and civic-response documents | Grounded advisories and pump-deployment reasoning |
| Voice AI | Amazon Transcribe + Polly (Hindi/English) | Spoken reporting and spoken alerts |

## Agent architecture

```
                      ┌──────────────────┐
   events ──────────▶ │    Supervisor    │ ◀── scheduler / forecast changes
 (report, rain,       └───────┬──────────┘
  user chat)                  │
     ┌───────────┬────────────┼─────────────┬──────────────┐
     ▼           ▼            ▼             ▼              ▼
 Verifier   Depth Agent   Forecaster     Router       Dispatcher
 (trust)    (vision)      (risk+alerts)  (vehicle)    (human-in-loop)
     │           │            │             │              │
     └───────────┴──── shared memory (per-hotspot history) ─┘
```

- **Verifier** asks nearby users for a second photo when trust is low or reports conflict.
- **Depth Agent** requests another angle when confidence is low.
- **Forecaster** raises proactive alerts and reranks affected routes before flooding.
- **Router** compares fastest vs safest paths and explains the choice.
- **Dispatcher** proposes a pump plan that needs human approval.
- Every decision is logged to an **agent reasoning timeline** (observation → thought → tool → action).

## Features

### MVP (must work end to end)
- [ ] Photo report with auto-captured location
- [ ] Verification and trust score
- [ ] Vision-LLM depth estimate with confidence
- [ ] Live flood map with time decay
- [ ] Vehicle-aware safe routing (bike / hatchback / sedan / SUV)

### Stretch
- [ ] Pre-flood risk map from Copernicus DEM (flow accumulation, Topographic Wetness Index)
- [ ] Rainfall nowcasting alerts (Open-Meteo + GPM IMERG)
- [ ] Multi-agent orchestration with Strands Agents
- [ ] Authority dashboard, hotspot ranking and pump deployment plan
- [ ] Offline-first PWA with Hindi and voice reporting
- [ ] CCTV / traffic-cam frame ingestion
- [ ] 3D flood replay (deck.gl)
- [ ] Optional ESP32 + ultrasonic sensor node

## Tech stack

- **Frontend:** Next.js, TypeScript, Tailwind, MapLibre GL, deck.gl, PWA (English + Hindi)
- **Backend:** AWS Lambda, API Gateway, DynamoDB, S3, Cognito, EventBridge, SNS
- **AI:** Amazon Bedrock, Strands Agents SDK, Amazon Transcribe, Amazon Polly
- **Geo:** Amazon Location Service, Copernicus DEM (AWS Open Data)
- **Data:** Open-Meteo, NASA GPM IMERG
- **Infra:** AWS SAM, Amplify Hosting, CloudFront

## Inspired by global flood-response systems

| System | Idea we borrow |
|---|---|
| NYC FloodNet | Low-cost street-level depth sensing |
| Singapore PUB | Water-level sensing plus CCTV with public alerts |
| Jakarta PetaBencana.id | Crowdsourced flood maps |
| Japan XRAIN | High-resolution rainfall for localized warnings |
| Rotterdam / Copenhagen | Terrain-based cloudburst planning and digital twins |
| Google Flood Hub | AI-based flood forecasting |

JalMarg combines crowdsourcing, sensing, nowcasting and terrain modelling into one low-cost system built for India.

## Live vs simulated (will be kept up to date)

| Component | Status |
|---|---|
| Hotspot data for Delhi underpasses | Seeded |
| Citizen reports | Seeded + live uploads |
| Rainfall forecast | Planned: live (Open-Meteo) |
| Terrain risk layer | Planned: live (Copernicus DEM) |
| Agent orchestration | Planned |

We are upfront about what is real and what is simulated for the demo.

## Getting started

```bash
git clone https://github.com/<your-username>/jalmarg.git
cd jalmarg
# setup instructions coming soon
```

## Roadmap

- [x] Idea and architecture
- [ ] Core pipeline: photo → verify → depth → map
- [ ] Safe routing
- [ ] Agent layer and forecasting
- [ ] Authority dashboard
- [ ] Demo video and AWS Builder Center blog

## Team

Built by **Triyansh Agarwal** for Environmental Hacks 2026.
