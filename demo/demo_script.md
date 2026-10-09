# JalMarg 3-Minute Demo Script

*Setup: Ensure `npm run dev` and `uvicorn app.main:app` are running locally. Mount the main dashboard (`localhost:3000`). Make sure you have the simulated test image of the flooded street ready.*

**0:00 - 0:20 | Introduction**
*Action: Display the JalMarg Master Dashboard.*
"Urban flooding happens fast, and municipal authorities are overwhelmed blindly reacting to thousands of disparate tweets and fake pictures, destroying dispatch efficiency. Presenting JalMarg: an autonomous verification engine mapping crowdsourced intelligence into live infrastructural routing and automated human-reviewed dispatch workflows."

**0:20 - 0:45 | Dashboard & Incident Upload**
*Action: Show Map Interface. Navigate to 'Submit Report'. Upload the flood image.*
"Here is the map interface currently pulsing with local vulnerabilities. Let's act as a citizen reporting a critical failure at the main underpass. I upload a photo. Behind the scenes, JalMarg intercepts this asynchronously. Our first pipeline engages deterministic structural hashing, extracting metadata boundaries and instantly verifying if this photo is an old duplicate trying to manipulate emergency services."

**0:45 - 1:10 | AI Vision Inference**
*Action: Click back to the dashboard. Let the timeline start showing the agent working.*
"Once verification passes securely, the Strands AI Supervisor engages Gemini 1.5. Instead of human operators squinting at the picture, the multi-modal agent autonomously scans the pixels, outputting quantitative depth parameters (estimating 35cm of water) and attributing a 'CRITICAL' severity indicator instantly."

**1:10 - 1:35 | Risk Orchestration & Weather Mapping**
*Action: Zoom in on the newly glowing red Map Marker.*
"The Agent doesn't stop at the photo. Look at the map: it grabs the live vulnerability dataset for that node, reaches out to Open-Meteo for localized forecasting, pulling civic instructions recursively using the TinyFish API, and subsequently escalates the overall hotspot's risk vector to CRITICAL dynamically."

**1:35 - 2:00 | Vehicle-Aware Routing Validation**
*Action: Snap to the Route Planner view. Drop origin and destination points.*
"And for standard citizens: standard maps don't understand depths. JalMarg calculates custom geospatial radii bounding our new incident. If a Sedan attempts passing, our engine calculates direct water exposure geometries rejecting the route, allowing only high-clearance SUVs passage without catastrophic engine damage."

**2:00 - 2:25 | The Authority Handoff**
*Action: Open the '/authority' dashboard. Look at the pending Approvals.*
"For the backend Authority, everything culminates here. After measuring the depths, risks, and municipal frameworks sequentially, the AI has generated a formal Dispatch Proposal requesting pumps at the underpass. It lists precise rationale. The human is still in the loop. I hit 'APPROVE'." *Action: Hit Approve button.*

**2:25 - 3:00 | Agent Transparency Conclusion**
*Action: Point out the Agent Activity Timeline.*
"Notice how the UI logged my approval using a live database modification. More importantly, observe this timeline. Our entire architecture is decoupled, deterministic, and completely accountable. The Authority can audit the exact execution payload the Supervisor navigated through, parsing distinct LLM calls vs mocked fallback scenarios seamlessly. JalMarg enables true, error-free city resilience."
