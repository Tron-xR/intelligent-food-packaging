from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field


class CommodityCategory(StrEnum):
    FRESH_PRODUCE = "fresh_produce"
    DAIRY = "dairy"
    MEAT_POULTRY = "meat_poultry"
    BAKERY = "bakery"
    DRY_STAPLE = "dry_staple"
    OIL_FAT_RICH = "oil_fat_rich"
    READY_TO_EAT = "ready_to_eat"


class StorageType(StrEnum):
    AMBIENT = "ambient"
    CHILLED = "chilled"
    FROZEN = "frozen"


class CommodityInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: Annotated[str, Field(min_length=1, max_length=120)]
    category: CommodityCategory
    moisture_content_pct: Annotated[float, Field(ge=0, le=100)]
    fat_content_pct: Annotated[float, Field(ge=0, le=100)]
    ph: Annotated[float, Field(ge=0, le=14)]
    respiration_rate_ml_co2_per_kg_hr: Annotated[float, Field(ge=0, le=1000)] = 0


class RequirementsInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    desired_shelf_life_days: Annotated[int, Field(ge=1, le=3650)]


class EnvironmentInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    storage_type: StorageType
    storage_temp_c: Annotated[float, Field(ge=-60, le=60)]
    relative_humidity_pct: Annotated[float, Field(ge=0, le=100)]
    transport_mode: Annotated[str, Field(min_length=1, max_length=80)]
    transport_duration_hr: Annotated[float, Field(ge=0, le=8760)]


class RecommendationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    commodity: CommodityInput
    requirements: RequirementsInput
    environment: EnvironmentInput


class GasMix(BaseModel):
    o2_pct: Annotated[float, Field(ge=0, le=100)]
    co2_pct: Annotated[float, Field(ge=0, le=100)]
    n2_pct: Annotated[float, Field(ge=0, le=100)]


class SpecificationOutput(BaseModel):
    otr_cc_m2_day: str
    wvtr_g_m2_day: str
    thickness_micron: str
    sealability: str
    map_suitable: bool
    map_gas_mix: GasMix | None = None


class SustainabilityOutput(BaseModel):
    recyclable: bool
    biodegradable: bool
    cost_tier: str


class RecommendationOutput(BaseModel):
    material: str
    material_type: str
    confidence: Annotated[float, Field(ge=0, le=1)]
    specs: SpecificationOutput
    predicted_shelf_life_days: int
    predicted_shelf_life_range_days: tuple[int, int]
    sustainability: SustainabilityOutput
    explanation: str
    rule_trace: list[str]


class RecommendationResponse(BaseModel):
    recommendations: list[RecommendationOutput]
    alternatives: list[str]
    model_version: str
    disclaimer: str
    warnings: list[str] = Field(default_factory=list)
