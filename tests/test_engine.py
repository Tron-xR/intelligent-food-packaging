import pytest

from app.engine import recommend
from app.schemas import (
    CommodityCategory,
    CommodityInput,
    EnvironmentInput,
    RecommendationRequest,
    RequirementsInput,
    StorageType,
)


def make_request(
    *,
    category: CommodityCategory = CommodityCategory.FRESH_PRODUCE,
    moisture: float = 90,
    fat: float = 2,
    ph: float = 5,
    respiration: float = 12,
    storage: StorageType = StorageType.CHILLED,
    temperature: float = 8,
    humidity: float = 85,
    shelf_life: int = 14,
    transport_hours: float = 24,
) -> RecommendationRequest:
    return RecommendationRequest(
        commodity=CommodityInput(
            name="Tomato",
            category=category,
            moisture_content_pct=moisture,
            fat_content_pct=fat,
            ph=ph,
            respiration_rate_ml_co2_per_kg_hr=respiration,
        ),
        requirements=RequirementsInput(desired_shelf_life_days=shelf_life),
        environment=EnvironmentInput(
            storage_type=storage,
            storage_temp_c=temperature,
            relative_humidity_pct=humidity,
            transport_mode="refrigerated_truck",
            transport_duration_hr=transport_hours,
        ),
    )


def test_oil_rich_product_prefers_high_oxygen_barrier_material() -> None:
    response = recommend(
        make_request(
            category=CommodityCategory.OIL_FAT_RICH,
            moisture=5,
            fat=35,
            respiration=0,
            storage=StorageType.AMBIENT,
            temperature=25,
            humidity=50,
        )
    )

    first_material = response.recommendations[0]
    assert first_material.specs.otr_cc_m2_day != ""
    assert first_material.specs.otr_cc_m2_day.split("-")[0] != "1500"
    assert "oxidation" in first_material.explanation.casefold()


def test_frozen_storage_excludes_non_freezer_grade_materials() -> None:
    response = recommend(
        make_request(
            category=CommodityCategory.DRY_STAPLE,
            moisture=12,
            fat=2,
            respiration=0,
            storage=StorageType.FROZEN,
            temperature=-18,
            humidity=60,
        )
    )

    material_names = {item.material for item in response.recommendations}
    assert "PLA/PBAT biodegradable film" not in material_names
    assert "EVOH barrier film" in material_names


def test_respiring_produce_returns_a_controlled_gas_option() -> None:
    response = recommend(make_request())

    first = response.recommendations[0]
    assert first.specs.map_suitable is True
    assert first.specs.map_gas_mix is not None
    assert first.specs.map_gas_mix.n2_pct == pytest.approx(
        100 - first.specs.map_gas_mix.o2_pct - first.specs.map_gas_mix.co2_pct
    )


def test_contradictory_frozen_respiration_input_degrades_with_warning() -> None:
    response = recommend(
        make_request(
            storage=StorageType.FROZEN,
            temperature=-18,
            respiration=40,
        )
    )

    assert response.recommendations
    assert response.warnings
    assert any("respiration" in warning.casefold() for warning in response.warnings)
