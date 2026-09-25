# Intelligent Food Packaging Recommendation

An AI-oriented decision-support service for selecting food packaging materials and specifications from commodity properties, shelf-life goals, storage conditions, and transport requirements.

The initial implementation is a transparent rules-based MVP. It ranks material families, returns OTR/WVTR/thickness bands, estimates shelf life, proposes a controlled-atmosphere gas mix for respiring produce when applicable, tags sustainability attributes, and explains every result. It is deliberately designed so a learned ranking or shelf-life model can be added without replacing the API contract.

## Current capabilities

- Validates the documented commodity, requirements, and environment payload.
- Applies category, respiration, moisture, fat, pH, storage, shelf-life, humidity, and transport rules.
- Filters an editable JSON packaging-material knowledge base by storage compatibility and barrier fit.
- Returns up to three ranked recommendations with alternatives, confidence, specifications, sustainability tags, and a rule trace.
- Estimates a shelf-life point and range using an explainable heuristic.
- Returns warnings for contradictory inputs and reduced-confidence nearest matches.
- Exposes `/health` and `POST /recommend` through FastAPI.
- Includes API, engine, boundary, and regression tests plus GitHub Actions CI.

## Quick start

Requires Python 3.11 or newer.

```bash
python -m venv .venv
python -m pip install -e ".[dev]"
python -m uvicorn app.main:app --reload
```

On Windows, replace `python` with `py` when needed.

The API is available at `http://127.0.0.1:8000`, with interactive documentation at `http://127.0.0.1:8000/docs`.

## Example request

```bash
curl -X POST http://127.0.0.1:8000/recommend \
  -H "Content-Type: application/json" \
  -d '{
    "commodity": {
      "name": "Tomato",
      "category": "fresh_produce",
      "moisture_content_pct": 94.5,
      "fat_content_pct": 0.2,
      "ph": 4.3,
      "respiration_rate_ml_co2_per_kg_hr": 15
    },
    "requirements": {"desired_shelf_life_days": 14},
    "environment": {
      "storage_type": "chilled",
      "storage_temp_c": 8,
      "relative_humidity_pct": 90,
      "transport_mode": "refrigerated_truck",
      "transport_duration_hr": 24
    }
  }'
```

## Project layout

```text
app/
  data/                 Editable material and commodity reference data
  engine.py             Rules, matching, ranking, explanations, estimates
  knowledge_base.py     JSON loading and reference lookup
  main.py               FastAPI application and endpoints
  schemas.py            Request and response contracts
 tests/                  API and engine tests
 00_README.md            Original design-document index
 01–07_*.md              Architecture, data flow, agent, data, roadmap, evaluation docs
```

## Verify the project

```bash
python -m pytest -q
python -m ruff check .
python -m mypy app
```

## Data and safety

The material ranges and rule thresholds are an engineering starting point for product development, not validated commercial specifications. Before using a recommendation for procurement, shelf-life claims, or food-safety decisions, have a qualified packaging or food-safety professional review the material data, process conditions, testing methods, and applicable regulations. Do not expose this service as a certified replacement for expert or regulatory review.

## Next development slices

1. Replace the seed knowledge base with versioned, expert-reviewed reference data.
2. Add persistence for recommendation logs and user feedback.
3. Add a calibrated shelf-life model trained on literature and pilot outcomes.
4. Add a material-ranking model as a re-ranking layer over the hard rule filters.
5. Build the web input form and results dashboard described in the design documents.
