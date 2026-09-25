# 6. Development Phases & Roadmap

## 6.1 Phase Timeline (indicative)

```mermaid
gantt
    title Development Roadmap
    dateFormat  YYYY-MM-DD
    section Phase 1 - Foundation
    Requirement finalization & domain research   :p1a, 2026-10-01, 14d
    Knowledge base schema + seed data (materials, commodities) :p1b, after p1a, 21d
    section Phase 2 - Core Engine
    Rule engine (hard constraints)                :p2a, after p1b, 14d
    Material Matching + Barrier Predictor agents  :p2b, after p2a, 14d
    section Phase 3 - ML Layer
    Shelf-life prediction model (v1)              :p3a, after p2b, 21d
    Material ranking ML model                     :p3b, after p3a, 14d
    section Phase 4 - Application
    Backend API (FastAPI)                         :p4a, after p2a, 21d
    Web front-end (input form + dashboard)        :p4b, after p4a, 21d
    section Phase 5 - Enrichment
    MAP gas composition module                    :p5a, after p3b, 10d
    Sustainability & cost tagging                 :p5b, after p5a, 7d
    Explanation generator                         :p5c, after p5b, 7d
    section Phase 6 - Validation & Launch
    Domain-expert review of recommendations       :p6a, after p5c, 14d
    Pilot testing with real users                 :p6b, after p6a, 21d
    Feedback loop + retraining pipeline           :p6c, after p6b, 14d
    section Phase 7 - Extensions
    Mobile app (Flutter)                          :p7a, after p6c, 30d
    QR traceability + advanced cost modeling      :p7b, after p7a, 30d
```

## 6.2 Phase-Wise Breakdown

### Phase 1 — Foundation (Research & Data)
- Finalize the exact list of supported commodities and packaging material families for v1.
- Consult/validate against food-packaging science literature (and ideally a domain expert) for the OTR/WVTR/thickness bands per material and per commodity category.
- Design and populate the initial knowledge base (`packaging_material`, `commodity`, `map_gas_profile` tables).
- **Deliverable**: populated database + data dictionary.

### Phase 2 — Core Rule-Based Engine
- Implement the Commodity Classifier, Barrier Property Predictor, and Material Matching agents as a pure rule/decision-table system (no ML yet) — this alone is already usable as an MVP decision-support tool.
- **Deliverable**: working rule engine producing valid material recommendations from structured input.

### Phase 3 — Machine Learning Layer
- Collect/curate training data for shelf-life prediction (literature + any pilot feedback).
- Train and validate the shelf-life regression model and the material-ranking model.
- Integrate as a re-ranking/refinement layer on top of the Phase 2 rule engine (hybrid approach, per architecture doc).
- **Deliverable**: trained models with documented accuracy/validation metrics.

### Phase 4 — Application Layer
- Build the FastAPI backend exposing `/recommend` and `/feedback` endpoints.
- Build the web front-end: input form, results dashboard, explanation panel.
- **Deliverable**: end-to-end working web application (can run in parallel with Phase 2/3).

### Phase 5 — Feature Enrichment
- Add the MAP/gas composition agent for respiring produce.
- Add sustainability tagging (recyclable/biodegradable) and relative cost tiering.
- Add the explanation generator for transparent recommendations.
- **Deliverable**: feature-complete v1 recommendation output matching the full spec in the problem statement.

### Phase 6 — Validation & Pilot Launch
- Domain-expert review of a sample of recommendations for correctness/safety.
- Pilot with a small set of real users (a food startup, a farmer group, or a college food-tech lab).
- Wire up the feedback store and a basic retraining pipeline.
- **Deliverable**: validated, pilot-tested v1 system + retraining process.

### Phase 7 — Extensions (Post-v1)
- Flutter mobile app wrapping the same backend API.
- QR-based traceability across the supply chain.
- Deeper cost optimization (live vendor pricing integration).
- IoT/sensor integration for real-time spoilage monitoring (long-term).

## 6.3 Suggested Team Roles

| Role | Responsibility |
|---|---|
| Backend/ML engineer(s) | API, agent pipeline, ML models |
| Front-end engineer | Web (and later mobile) client |
| Domain/food-science advisor | Validates knowledge base and rule thresholds |
| Data curator | Sources and structures the packaging material + commodity reference data |
