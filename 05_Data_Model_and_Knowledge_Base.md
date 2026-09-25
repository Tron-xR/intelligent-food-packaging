# 5. Data Model & Knowledge Base

## 5.1 Entity-Relationship Overview

```mermaid
erDiagram
    COMMODITY ||--o{ RECOMMENDATION : "requested for"
    PACKAGING_MATERIAL ||--o{ RECOMMENDATION : "recommended as"
    RECOMMENDATION ||--o| FEEDBACK : "receives"
    PACKAGING_MATERIAL ||--o{ MAP_GAS_PROFILE : "supports"
    COMMODITY ||--o{ MAP_GAS_PROFILE : "uses"

    COMMODITY {
        int commodity_id PK
        string name
        string category
        float moisture_content_pct
        float fat_content_pct
        float ph
        float respiration_rate
        string typical_storage_type
    }

    PACKAGING_MATERIAL {
        int material_id PK
        string name
        string material_type
        float otr_min
        float otr_max
        float wvtr_min
        float wvtr_max
        float thickness_min_micron
        float thickness_max_micron
        string sealability
        bool recyclable
        bool biodegradable
        string cost_tier
    }

    MAP_GAS_PROFILE {
        int profile_id PK
        int commodity_id FK
        int material_id FK
        float o2_pct
        float co2_pct
        float n2_pct
    }

    RECOMMENDATION {
        int recommendation_id PK
        int commodity_id FK
        int material_id FK
        json input_conditions
        float confidence_score
        int predicted_shelf_life_days
        text explanation
        datetime created_at
    }

    FEEDBACK {
        int feedback_id PK
        int recommendation_id FK
        int actual_shelf_life_days
        string outcome_rating
        text notes
    }
```

## 5.2 Core Tables

### `commodity`
Reference data for known commodities — used both to validate/auto-fill user input and as training data for the classifier.

### `packaging_material`
The core knowledge base table. Each row is a material family (not a specific vendor product) with its typical barrier property ranges. This table is the primary thing subject-matter experts (food packaging specialists) should be able to review/edit — consider a lightweight admin UI or a versioned CSV/spreadsheet import pipeline for this in early phases.

### `map_gas_profile`
Pre-validated MAP gas mix recipes per commodity category, cross-referenced against compatible films.

### `recommendation`
Every recommendation served is logged with the full input JSON — this is what feeds the feedback loop and model retraining.

### `feedback`
Optional but valuable: actual observed shelf life or industry-reported outcome, linked back to the recommendation that was given. This is the ground truth for improving the shelf-life model over time.

## 5.3 Knowledge Base Seeding Strategy

1. **Phase 1**: Seed `packaging_material` and `map_gas_profile` from published food-packaging science literature and standard industry references (a domain expert / food-tech advisor review is strongly recommended before production use, given food-safety implications).
2. **Phase 2**: Seed `commodity` with common fruits/vegetables, dairy, meat, and dry-goods reference properties.
3. **Ongoing**: Grow `recommendation` + `feedback` from real usage to train and validate the ML ranking/shelf-life models.
