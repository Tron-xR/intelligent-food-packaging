from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.knowledge_base import MATERIALS, find_commodity_reference
from app.schemas import (
    CommodityCategory,
    GasMix,
    RecommendationOutput,
    RecommendationRequest,
    RecommendationResponse,
    SpecificationOutput,
    StorageType,
    SustainabilityOutput,
)


@dataclass(frozen=True)
class BarrierBand:
    otr_min: float
    otr_max: float
    wvtr_min: float
    wvtr_max: float
    thickness_min: float
    thickness_max: float


@dataclass(frozen=True)
class Candidate:
    material: dict[str, Any]
    fit: float
    score: float
    otr_range: tuple[float, float]
    wvtr_range: tuple[float, float]
    thickness_range: tuple[float, float]
    relaxed: bool = False


def _range(value: dict[str, Any]) -> tuple[float, float]:
    return float(value["min"]), float(value["max"])


def _overlap(
    target_min: float,
    target_max: float,
    material_min: float,
    material_max: float,
) -> tuple[float, float, float]:
    lower = max(target_min, material_min)
    upper = min(target_max, material_max)
    if upper <= lower:
        return lower, upper, 0.0
    target_span = max(target_max - target_min, 0.01)
    return lower, upper, (upper - lower) / target_span


def _bounded_range(minimum: float, maximum: float) -> tuple[float, float]:
    lower = max(0.01, min(minimum, maximum))
    upper = max(lower * 1.01, maximum)
    return lower, upper


def _classify_commodity(request: RecommendationRequest) -> tuple[str, list[str]]:
    category = request.commodity.category.value
    traces = [f"Commodity classified as {category} from the submitted category."]
    reference = find_commodity_reference(request.commodity.name)
    if reference is not None:
        traces.append(
            f"Reference profile matched for {reference['name']}; its default properties are "
            "available for future model calibration."
        )
        if reference["category"] != category:
            traces.append(
                "The submitted category was retained because explicit input overrides defaults."
            )
    else:
        traces.append("No reference profile matched; rules use the submitted physical properties.")
    return category, traces


def _derive_barrier_band(
    request: RecommendationRequest,
    category: str,
    warnings: list[str],
) -> tuple[BarrierBand, list[str]]:
    commodity = request.commodity
    environment = request.environment
    storage = environment.storage_type
    respiration = commodity.respiration_rate_ml_co2_per_kg_hr
    fat = commodity.fat_content_pct
    moisture = commodity.moisture_content_pct
    shelf_life = request.requirements.desired_shelf_life_days
    traces: list[str] = []
    otr_min: float
    otr_max: float
    wvtr_min: float
    wvtr_max: float
    thickness_min: float
    thickness_max: float

    if storage is StorageType.FROZEN:
        otr_min, otr_max = 20, 500
        wvtr_min, wvtr_max = 0.05, 3
        thickness_min, thickness_max = 60, 150
        traces.append("Frozen storage sets a high barrier to moisture migration and oxidation.")
        if respiration > 0:
            warnings.append(
                "The commodity has a respiration rate but frozen storage was requested; review the "
                "commodity-storage pairing before commercial use."
            )
    elif storage is StorageType.CHILLED:
        if category == CommodityCategory.FRESH_PRODUCE.value and respiration >= 5:
            otr_min, otr_max = 2000, 10000
            wvtr_min, wvtr_max = 2, 20
            thickness_min, thickness_max = 30, 90
            traces.append(
                "Respiring fresh produce at chilled storage needs controlled gas exchange rather "
                "than the lowest possible oxygen transmission."
            )
        else:
            otr_min, otr_max = 100, 2500
            wvtr_min, wvtr_max = 0.5, 8
            thickness_min, thickness_max = 40, 130
            traces.append(
                "Chilled storage calls for a moisture barrier and moderate oxygen control."
            )
    elif fat >= 20 or category == CommodityCategory.OIL_FAT_RICH.value:
        otr_min, otr_max = 5, 300
        wvtr_min, wvtr_max = 0.1, 3
        thickness_min, thickness_max = 40, 160
        traces.append("High fat content makes oxidation control the primary barrier requirement.")
    elif category == CommodityCategory.DRY_STAPLE.value or moisture <= 20:
        otr_min, otr_max = 20, 600
        wvtr_min, wvtr_max = 0.1, 3
        thickness_min, thickness_max = 40, 180
        traces.append("Dry staples prioritize moisture ingress protection and puncture resistance.")
    elif category in {
        CommodityCategory.DAIRY.value,
        CommodityCategory.MEAT_POULTRY.value,
        CommodityCategory.READY_TO_EAT.value,
    }:
        otr_min, otr_max = 30, 1200
        wvtr_min, wvtr_max = 0.2, 6
        thickness_min, thickness_max = 50, 160
        traces.append(
            "Moisture-rich animal-derived products require consistent barrier protection."
        )
    else:
        otr_min, otr_max = 200, 5000
        wvtr_min, wvtr_max = 2, 20
        thickness_min, thickness_max = 30, 120
        traces.append("High-moisture ambient storage requires a balanced moisture and gas barrier.")

    if shelf_life > 21 and category != CommodityCategory.FRESH_PRODUCE.value:
        otr_max = max(otr_min * 1.5, otr_max * 0.8)
        wvtr_max = max(wvtr_min * 1.5, wvtr_max * 0.85)
        traces.append("A longer shelf-life target tightens the acceptable upper barrier limits.")

    if environment.transport_duration_hr >= 48:
        thickness_min += 10
        traces.append(
            "Longer transport duration increases the minimum mechanical robustness target."
        )
    if environment.transport_duration_hr >= 120:
        thickness_min += 15
        traces.append(
            "Extended transport adds a further thickness requirement for handling stress."
        )

    if environment.relative_humidity_pct >= 85 and moisture >= 75:
        wvtr_max *= 1.2
        traces.append("High ambient humidity requires additional moisture-loss protection.")

    band = BarrierBand(
        otr_min=otr_min,
        otr_max=otr_max,
        wvtr_min=wvtr_min,
        wvtr_max=wvtr_max,
        thickness_min=thickness_min,
        thickness_max=thickness_max,
    )
    band = BarrierBand(
        otr_min=_bounded_range(band.otr_min, band.otr_max)[0],
        otr_max=_bounded_range(band.otr_min, band.otr_max)[1],
        wvtr_min=_bounded_range(band.wvtr_min, band.wvtr_max)[0],
        wvtr_max=_bounded_range(band.wvtr_min, band.wvtr_max)[1],
        thickness_min=band.thickness_min,
        thickness_max=band.thickness_max,
    )
    traces.append(
        f"Target bands: OTR {band.otr_min:g}-{band.otr_max:g} cc/m²/day and "
        f"WVTR {band.wvtr_min:g}-{band.wvtr_max:g} g/m²/day."
    )
    return band, traces


def _is_storage_compatible(material: dict[str, Any], request: RecommendationRequest) -> bool:
    storage = request.environment.storage_type.value
    if storage not in material["storage_compatibility"]:
        return False
    if storage == StorageType.FROZEN.value and not material["freezer_grade"]:
        return False
    return True


def _candidate_from_material(
    material: dict[str, Any],
    request: RecommendationRequest,
    band: BarrierBand,
    category: str,
) -> Candidate | None:
    if not _is_storage_compatible(material, request):
        return None

    commodity = request.commodity
    respiration = commodity.respiration_rate_ml_co2_per_kg_hr
    if respiration >= 5 and category == CommodityCategory.FRESH_PRODUCE.value:
        if not material["respiration_compatible"]:
            return None
    if commodity.fat_content_pct >= 20 and not material["oxidation_compatible"]:
        return None

    material_otr = _range(material["otr_cc_m2_day"])
    material_wvtr = _range(material["wvtr_g_m2_day"])
    material_thickness = _range(material["thickness_micron"])
    otr_lower, otr_upper, otr_fit = _overlap(band.otr_min, band.otr_max, *material_otr)
    wvtr_lower, wvtr_upper, wvtr_fit = _overlap(band.wvtr_min, band.wvtr_max, *material_wvtr)
    thickness_lower, thickness_upper, thickness_fit = _overlap(
        band.thickness_min,
        band.thickness_max,
        *material_thickness,
    )
    if otr_fit == 0 or wvtr_fit == 0:
        return None

    fit = otr_fit * 0.45 + wvtr_fit * 0.35 + thickness_fit * 0.2
    score = fit
    if respiration >= 5 and category == CommodityCategory.FRESH_PRODUCE.value:
        score += 0.12
        if material["respiration_preference"] == "high":
            score += 0.08
    if request.requirements.desired_shelf_life_days > 30:
        if material_otr[1] <= 100 and material_wvtr[1] <= 2:
            score += 0.05
    if request.environment.transport_duration_hr >= 48:
        if material_thickness[1] >= band.thickness_min + 20:
            score += 0.04
    if material["map_suitable"] and respiration >= 5:
        score += 0.04
    if material["recyclable"] or material["biodegradable"]:
        score += 0.03
    if material["cost_tier"] == "low":
        score += 0.01

    return Candidate(
        material=material,
        fit=fit,
        score=score,
        otr_range=(otr_lower, otr_upper),
        wvtr_range=(wvtr_lower, wvtr_upper),
        thickness_range=(thickness_lower, thickness_upper),
    )


def _fallback_score(
    material: dict[str, Any],
    request: RecommendationRequest,
    band: BarrierBand,
) -> Candidate:
    material_otr = _range(material["otr_cc_m2_day"])
    material_wvtr = _range(material["wvtr_g_m2_day"])
    material_thickness = _range(material["thickness_micron"])
    otr_distance = abs(
        ((material_otr[0] + material_otr[1]) / 2) - ((band.otr_min + band.otr_max) / 2)
    )
    wvtr_distance = abs(
        ((material_wvtr[0] + material_wvtr[1]) / 2) - ((band.wvtr_min + band.wvtr_max) / 2)
    )
    normalized_otr_distance = otr_distance / max(band.otr_max, 1)
    normalized_wvtr_distance = wvtr_distance / max(band.wvtr_max, 1)
    fit = max(0.05, 1 - (normalized_otr_distance + normalized_wvtr_distance) / 2)
    score = fit
    if material["recyclable"] or material["biodegradable"]:
        score += 0.02
    if material["cost_tier"] == "low":
        score += 0.01
    return Candidate(
        material=material,
        fit=fit,
        score=score,
        otr_range=material_otr,
        wvtr_range=material_wvtr,
        thickness_range=material_thickness,
        relaxed=True,
    )


def _intersection_or_range(
    target: tuple[float, float],
    material: tuple[float, float],
) -> tuple[float, float]:
    lower = max(target[0], material[0])
    upper = min(target[1], material[1])
    if upper <= lower:
        return material
    return lower, upper


def _gas_mix(
    request: RecommendationRequest,
    category: str,
    material: dict[str, Any],
) -> GasMix | None:
    respiration = request.commodity.respiration_rate_ml_co2_per_kg_hr
    if category != CommodityCategory.FRESH_PRODUCE.value or respiration <= 0:
        return None
    if not material["map_suitable"]:
        return None
    oxygen = 3 if respiration >= 20 else 5
    carbon_dioxide = 3 if request.commodity.ph <= 4.5 and respiration >= 20 else 5
    nitrogen = 100 - oxygen - carbon_dioxide
    return GasMix(o2_pct=oxygen, co2_pct=carbon_dioxide, n2_pct=nitrogen)


def _predicted_shelf_life(
    request: RecommendationRequest,
    category: str,
    candidate: Candidate,
) -> int:
    base_by_category = {
        CommodityCategory.FRESH_PRODUCE.value: 12,
        CommodityCategory.DAIRY.value: 14,
        CommodityCategory.MEAT_POULTRY.value: 10,
        CommodityCategory.BAKERY.value: 12,
        CommodityCategory.DRY_STAPLE.value: 30,
        CommodityCategory.OIL_FAT_RICH.value: 45,
        CommodityCategory.READY_TO_EAT.value: 8,
    }
    base = float(base_by_category[category])
    temperature = request.environment.storage_temp_c
    temperature_factor = max(0.45, min(1.8, 1 + (10 - temperature) * 0.03))
    humidity_factor = 1.0
    if (
        request.environment.relative_humidity_pct >= 85
        and request.commodity.moisture_content_pct >= 75
    ):
        humidity_factor = 0.92
    barrier_factor = 0.7 + min(1.0, candidate.fit) * 0.45
    transport_factor = max(0.8, 1 - request.environment.transport_duration_hr / 720)
    prediction = base * temperature_factor * humidity_factor * barrier_factor * transport_factor
    return max(1, round(prediction))


def _explanation(
    request: RecommendationRequest,
    category: str,
    band: BarrierBand,
    candidate: Candidate,
) -> str:
    material = candidate.material
    if request.commodity.fat_content_pct >= 20 or category == CommodityCategory.OIL_FAT_RICH.value:
        driver = (
            "the high fat content creates oxidation sensitivity, so oxygen barrier is the priority"
        )
    elif (
        category == CommodityCategory.FRESH_PRODUCE.value
        and request.commodity.respiration_rate_ml_co2_per_kg_hr >= 5
    ):
        driver = (
            "the respiration rate makes controlled gas exchange important while still limiting "
            "moisture loss"
        )
    elif request.commodity.moisture_content_pct >= 75:
        driver = "the high moisture content makes moisture control and handling strength important"
    else:
        driver = (
            "the requested storage and shelf-life conditions call for a balanced barrier "
            "specification"
        )

    explanation = (
        f"{material['name']} is recommended because {driver}. Its OTR range "
        f"{candidate.otr_range[0]:g}-{candidate.otr_range[1]:g} and WVTR range "
        f"{candidate.wvtr_range[0]:g}-{candidate.wvtr_range[1]:g} overlap the rule target of "
        f"{band.otr_min:g}-{band.otr_max:g} OTR and {band.wvtr_min:g}-{band.wvtr_max:g} WVTR."
    )
    if candidate.relaxed:
        explanation += (
            " No exact barrier match was available, so this is a nearest compatible alternative."
        )
    return explanation


def _build_output(
    request: RecommendationRequest,
    category: str,
    band: BarrierBand,
    candidate: Candidate,
    trace: list[str],
) -> RecommendationOutput:
    material = candidate.material
    otr_range = candidate.otr_range
    wvtr_range = candidate.wvtr_range
    thickness_range = candidate.thickness_range
    map_gas_mix = _gas_mix(request, category, material)
    predicted = _predicted_shelf_life(request, category, candidate)
    lower = max(1, round(predicted * 0.8))
    upper = max(lower, round(predicted * 1.2))
    confidence = min(
        0.99,
        max(0.35, 0.4 + min(1.0, candidate.fit) * 0.35 + min(0.2, candidate.score * 0.1)),
    )
    if candidate.relaxed:
        confidence = min(confidence, 0.55)
    return RecommendationOutput(
        material=material["name"],
        material_type=material["material_type"],
        confidence=round(confidence, 2),
        specs=SpecificationOutput(
            otr_cc_m2_day=f"{otr_range[0]:g}-{otr_range[1]:g}",
            wvtr_g_m2_day=f"{wvtr_range[0]:g}-{wvtr_range[1]:g}",
            thickness_micron=f"{thickness_range[0]:g}-{thickness_range[1]:g}",
            sealability=material["sealability"],
            map_suitable=map_gas_mix is not None,
            map_gas_mix=map_gas_mix,
        ),
        predicted_shelf_life_days=predicted,
        predicted_shelf_life_range_days=(lower, upper),
        sustainability=SustainabilityOutput(
            recyclable=material["recyclable"],
            biodegradable=material["biodegradable"],
            cost_tier=material["cost_tier"],
        ),
        explanation=_explanation(request, category, band, candidate),
        rule_trace=trace,
    )


def recommend(request: RecommendationRequest) -> RecommendationResponse:
    warnings: list[str] = []
    category, classification_trace = _classify_commodity(request)
    band, barrier_trace = _derive_barrier_band(request, category, warnings)
    exact_candidates: list[Candidate] = []
    fallback_candidates: list[Candidate] = []

    for material in MATERIALS:
        candidate = _candidate_from_material(material, request, band, category)
        if candidate is not None:
            exact_candidates.append(candidate)
        elif _is_storage_compatible(material, request):
            fallback_candidates.append(_fallback_score(material, request, band))

    ranked = sorted(exact_candidates, key=lambda item: item.score, reverse=True)
    if not ranked:
        ranked = sorted(fallback_candidates, key=lambda item: item.score, reverse=True)
        if ranked:
            warnings.append(
                "No material matched the complete barrier target; nearest storage-compatible "
                "options are shown with reduced confidence."
            )
    elif fallback_candidates and len(ranked) < 3:
        ranked.extend(sorted(fallback_candidates, key=lambda item: item.score, reverse=True))

    matching_trace = [
        f"Evaluated {len(MATERIALS)} material families against storage compatibility and "
        "target bands.",
        f"Selected {min(3, len(ranked))} ranked materials; alternatives are listed separately "
        "when available.",
    ]
    if any(item.relaxed for item in ranked[:3]):
        matching_trace.append("At least one returned material uses a relaxed nearest-match rule.")

    output: list[RecommendationOutput] = []
    for candidate in ranked[:3]:
        trace = [*classification_trace, *barrier_trace, *matching_trace]
        output.append(_build_output(request, category, band, candidate, trace))

    alternatives = [item.material["name"] for item in ranked[3:]]
    return RecommendationResponse(
        recommendations=output,
        alternatives=alternatives,
        model_version="rules-v1",
        disclaimer=(
            "Decision-support only. Validate the selected packaging, process conditions, "
            "shelf-life claim, and applicable food-safety requirements with a qualified "
            "packaging or food-safety professional before commercial use."
        ),
        warnings=warnings,
    )
