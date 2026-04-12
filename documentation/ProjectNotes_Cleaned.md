# Final Project – Group Notes (Cleaned)

## Project Core Question
> Can we detect structural conditions under the track using only the vibration signals from the moving train?

The project builds a **digital twin** of the rail system, integrating real and simulated sensor data, applying AI-based decision-making algorithms, and delivering a dashboard for predictive track maintenance.

---

## Key Design Constraints / Professor Guidance

- **Incorporate 4–5 concepts taught throughout the course** (see framework list below)
- **Classification-only models are considered shallow** — the project must go beyond simple classification and include prediction, control, and reasoning components
- **Visualization / dashboard is implied** since the project is presented — build one
- **Human-in-the-loop is required** — a human verifies or updates track segment states and triggers model retraining
- **Look into data simulation** — simulated track data will need to be generated beyond the provided dataset

---

## Features – Decided / In Scope

### 1. Track Health Classification
Classify each track segment into one of three structural health states based on vibration signals:

| State     | Stiffness | Damping | Natural Frequency |
|-----------|-----------|---------|-------------------|
| Healthy   | High      | Low     | ~5.0 Hz           |
| Degraded  | Medium    | Medium  | ~4.6 Hz           |
| Damaged   | Low       | High    | ~4.2 Hz           |

- The classifier uses vibration/accelerometer signals as input features
- Classification can be applied to the entire track or individual track segments

### 2. Train Acceleration Controller (MPC / PID)
Based on the track health classification output, the controller adjusts train speed:
- **Healthy track** → allow higher speed / normal acceleration
- **Degraded track** → moderate speed reduction
- **Damaged track** → significant slowdown + trigger safety whistle alert

The controller is built using **Pyomo** to implement **Model Predictive Control (MPC)**, with an **OODA Loop** (Observe–Orient–Decide–Act) embedded in the PID/MPC logic.

### 3. Frequency Reasoning – Kalman Filter
Apply a Kalman Filter to process the high-volume vibration sensor data stream. This represents the **Frequentist / Frequency Reasoning** component of the project — filtering noise and estimating the true state of the track from noisy accelerometer measurements.

### 4. ARMAX Forecasting
Use an **ARMAX (AutoRegressive Moving Average with eXogenous inputs)** model to forecast future track health trends based on historical vibration patterns. This supports predictive maintenance by projecting when a segment will degrade before it fails.

### 5. Bayesian Reasoning
Apply Bayesian inference to update track health state probabilities as new sensor readings arrive. This provides a probabilistic representation of track condition and supports uncertainty quantification in the classification.

### 6. Monte Carlo Simulation
Simulate scenarios such as:
- What happens when 20+ track segments require maintenance simultaneously?
- How does maintenance scheduling affect overall train operations?
- Stress-test the predictive maintenance pipeline under various degradation rates

### 7. Human-in-the-Loop (HITL)
A human operator interacts with the system through the dashboard to:
- Verify or override the classifier's track segment state assignments
- Confirm when a damaged/degraded segment has been repaired (update state to Healthy)
- Trigger a **reinforcement learning refresh** of the ML model based on corrected labels
- Update the dashboard with maintenance completion status

### 8. Predictive Maintenance Dashboard (End Output)
A unified dashboard providing:
- Real-time and historical track segment health states (classification output)
- ARMAX-based forecasts of future track degradation
- Maintenance scheduling recommendations
- (Stretch goal) Predictive ordering of replacement track segments to minimize operational disruption
- Human-in-the-loop interface for state corrections and model updates

---

## Features – Dropped

| Feature | Reason |
|---|---|
| Passenger Onload/Offload Prediction | Agreed to drop (Drew & Adam) — outside core scope |
| Energy Optimization Prediction | Agreed to drop (Drew & Adam) — too difficult to simulate meaningfully; no reliable way to infer uphill/downhill grade from two accelerometers alone |

---

## Course Concepts Incorporated (Target: 4–5)

| Concept | Implementation |
|---|---|
| Classification / ML | Track health classifier (Healthy / Degraded / Damaged) |
| Frequentist Reasoning | Kalman Filter on vibration data stream |
| Bayesian Reasoning | Probabilistic track state estimation |
| ARMAX Forecasting | Predicting future track degradation trends |
| MPC / Control Theory | Pyomo-based MPC controller for train acceleration |
| Monte Carlo Simulation | Maintenance scenario simulation |
| OODA Loop | Embedded in PID/MPC controller decision cycle |
| Human-in-the-Loop + RL | Human verifies states; RL refreshes the ML model |

---

## Outstanding Tasks

- [ ] Simulate track vibration data beyond the provided dataset (data simulation strategy TBD)
- [ ] Define classifier input features and their limits/thresholds
- [ ] Clarify Train Safety Classification details (confirm with group — likely the speed control + whistle alert behavior described above)
- [ ] Determine final page count limit for the report (confirm with instructor)
- [ ] Build out dashboard UI
- [ ] Implement HITL interface and RL model refresh loop
