from __future__ import annotations

import json
import os
from io import BytesIO
from typing import Any

import qrcode
import requests
import streamlit as st

from app.knowledge_base import MATERIALS

API_BASE_URL = os.getenv("FOOD_PACKAGING_API_URL", "http://127.0.0.1:8000").rstrip("/")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434/api/generate")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen3-coder")

CATEGORY_OPTIONS = {
    "Fresh produce": "fresh_produce",
    "Dairy": "dairy",
    "Dry staple / processed": "dry_staple",
    "Meat / poultry": "meat_poultry",
    "Bakery": "bakery",
    "Oil / fat rich": "oil_fat_rich",
    "Ready-to-eat": "ready_to_eat",
}

RESPIRATION_OPTIONS = {
    "None / non-respiring": 0.0,
    "Low (<10 mL CO2/kg-h)": 7.5,
    "Moderate (10-20 mL CO2/kg-h)": 15.0,
    "High (20-40 mL CO2/kg-h)": 30.0,
    "Extremely high (>40 mL CO2/kg-h)": 50.0,
}

STORAGE_OPTIONS = {
    "Ambient (20-28 C)": ("ambient", 25.0),
    "Chilled (2-8 C)": ("chilled", 5.0),
    "Frozen (-18 C or below)": ("frozen", -18.0),
}

TRANSPORT_OPTIONS = {
    "Local transit": "local_delivery",
    "Refrigerated truck": "refrigerated_truck",
    "Long-haul road": "ambient_truck",
    "Export / sea freight": "sea_freight",
}


def build_request_payload(
    *,
    commodity_name: str,
    category: str,
    desired_shelf_life: int,
    moisture: float,
    fat_content: float,
    ph_level: float,
    respiration: float,
    storage_type: str,
    storage_temp_c: float,
    relative_humidity_pct: float,
    transport_mode: str,
    transport_duration_hr: float,
) -> dict[str, Any]:
    return {
        "commodity": {
            "name": commodity_name,
            "category": category,
            "moisture_content_pct": moisture,
            "fat_content_pct": fat_content,
            "ph": ph_level,
            "respiration_rate_ml_co2_per_kg_hr": respiration,
        },
        "requirements": {"desired_shelf_life_days": desired_shelf_life},
        "environment": {
            "storage_type": storage_type,
            "storage_temp_c": storage_temp_c,
            "relative_humidity_pct": relative_humidity_pct,
            "transport_mode": transport_mode,
            "transport_duration_hr": transport_duration_hr,
        },
    }


def fetch_recommendation(payload: dict[str, Any]) -> dict[str, Any]:
    response = requests.post(
        f"{API_BASE_URL}/recommend",
        json=payload,
        timeout=(5, 30),
    )
    response.raise_for_status()
    result = response.json()
    if not isinstance(result, dict):
        raise ValueError("The recommendation API returned an invalid response.")
    return result


def submit_feedback(payload: dict[str, Any]) -> dict[str, Any]:
    response = requests.post(
        f"{API_BASE_URL}/feedback",
        json=payload,
        timeout=(5, 30),
    )
    response.raise_for_status()
    result = response.json()
    if not isinstance(result, dict):
        raise ValueError("The feedback API returned an invalid response.")
    return result


def generate_qr(payload: dict[str, Any]) -> bytes:
    code = qrcode.QRCode(version=1, box_size=5, border=2)
    code.add_data(json.dumps(payload, ensure_ascii=False))
    code.make(fit=True)
    image = code.make_image(fill_color="black", back_color="white")
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def generate_ollama_report(
    payload: dict[str, Any],
    recommendation_response: dict[str, Any],
    language: str,
) -> str:
    context = json.dumps(MATERIALS, ensure_ascii=False)
    request_context = json.dumps(payload, ensure_ascii=False)
    response_context = json.dumps(recommendation_response, ensure_ascii=False)
    prompt = (
        "You are a food packaging decision-support assistant. Explain the supplied rule-based "
        "recommendation for a non-technical user. Do not claim certification, regulatory approval, "
        "or laboratory validation. Use the requested language. "
        f"Language: {language}. Material context: {context}. "
        f"User request: {request_context}. API result: {response_context}."
    )
    chunks: list[str] = []
    with requests.post(
        OLLAMA_URL,
        json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": True},
        stream=True,
        timeout=(15, 300),
    ) as response:
        response.raise_for_status()
        for line in response.iter_lines():
            if not line:
                continue
            try:
                chunk = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(chunk, dict) and isinstance(chunk.get("response"), str):
                chunks.append(chunk["response"])
    return "".join(chunks)


def _recommendation_rows(recommendations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for recommendation in recommendations:
        specs = recommendation["specs"]
        sustainability = recommendation["sustainability"]
        rows.append(
            {
                "material": recommendation["material"],
                "confidence": f"{float(recommendation['confidence']):.0%}",
                "OTR": specs["otr_cc_m2_day"],
                "WVTR": specs["wvtr_g_m2_day"],
                "thickness_um": specs["thickness_micron"],
                "predicted_days": recommendation["predicted_shelf_life_days"],
                "recyclable": sustainability["recyclable"],
                "biodegradable": sustainability["biodegradable"],
            }
        )
    return rows


def _qr_payload(
    request_payload: dict[str, Any],
    recommendation_response: dict[str, Any],
) -> dict[str, Any]:
    return {
        "project": "intelligent-food-packaging",
        "request": request_payload,
        "recommendation_ids": [
            item["recommendation_id"]
            for item in recommendation_response.get("recommendations", [])
        ],
        "model_version": recommendation_response.get("model_version"),
        "notice": recommendation_response.get("disclaimer"),
    }


def render_results(
    request_payload: dict[str, Any],
    recommendation_response: dict[str, Any],
    language: str,
) -> None:
    recommendations = recommendation_response.get("recommendations", [])
    if not recommendations:
        st.warning("No packaging recommendation was returned for this input.")
        return

    left, right = st.columns([2.5, 1])
    with left:
        st.subheader("Ranked recommendation matrix")
        st.dataframe(
            _recommendation_rows(recommendations),
            use_container_width=True,
            hide_index=True,
        )
        for index, recommendation in enumerate(recommendations, start=1):
            st.markdown(f"#### {index}. {recommendation['material']}")
            st.write(
                f"Confidence: {float(recommendation['confidence']):.0%} | "
                f"Predicted shelf life: {recommendation['predicted_shelf_life_days']} days"
            )
            st.json(recommendation["specs"])
            st.info(recommendation["explanation"])

    with right:
        st.subheader("Traceability QR")
        qr_image = generate_qr(_qr_payload(request_payload, recommendation_response))
        st.image(qr_image, caption="Recommendation and input traceability payload")
        st.download_button(
            label="Download traceability QR",
            data=qr_image,
            file_name=f"{request_payload['commodity']['name']}_packaging_qr.png",
            mime="image/png",
        )

    if recommendation_response.get("warnings"):
        st.warning("; ".join(recommendation_response["warnings"]))

    st.subheader("Optional AI explanation")
    if st.button("Generate Ollama narrative", key="generate_ollama"):
        try:
            report = generate_ollama_report(request_payload, recommendation_response, language)
            st.markdown(report or "The local model returned no text.")
        except requests.RequestException as error:
            st.error(f"Ollama is unavailable: {error}")
        except ValueError as error:
            st.error(f"Ollama returned invalid data: {error}")

    render_feedback_form(recommendations)


def render_feedback_form(recommendations: list[dict[str, Any]]) -> None:
    recommendation_ids = [item["recommendation_id"] for item in recommendations]
    labels = {
        item["recommendation_id"]: f"{item['material']} ({item['recommendation_id'][:8]})"
        for item in recommendations
    }
    st.subheader("Record pilot outcome")
    with st.form("feedback_form"):
        recommendation_id = st.selectbox(
            "Recommendation",
            options=recommendation_ids,
            format_func=lambda value: labels[value],
        )
        actual_shelf_life = st.number_input(
            "Observed shelf life (days)",
            min_value=0,
            max_value=3650,
            value=int(recommendations[0]["predicted_shelf_life_days"]),
            step=1,
        )
        outcome = st.selectbox("Outcome", ["successful", "partial", "unsuccessful"])
        notes = st.text_area("Notes", max_chars=2000)
        submitted = st.form_submit_button("Save feedback", type="primary")
    if submitted:
        try:
            result = submit_feedback(
                {
                    "recommendation_id": recommendation_id,
                    "actual_shelf_life_days": int(actual_shelf_life),
                    "outcome_rating": outcome,
                    "notes": notes or None,
                }
            )
        except requests.RequestException as error:
            st.error(f"Feedback could not be saved: {error}")
        else:
            st.success(f"Feedback recorded as {result['feedback_id']}.")


def main() -> None:
    st.set_page_config(page_title="MoFPI Smart Packaging Engine", layout="wide")
    st.title("AI-Powered Intelligent Food Packaging Recommendation System")
    st.caption(
        "Rules-based recommendation with optional local Ollama explanation and traceability QR"
    )

    with st.form("packaging_input_form"):
        first, second, third = st.columns(3)
        with first:
            st.subheader("Commodity")
            commodity_name = st.text_input(
                "Food commodity",
                placeholder="e.g., Guava, paneer, rice",
            )
            category_label = st.selectbox("Category", list(CATEGORY_OPTIONS))
            desired_shelf_life = int(
                st.number_input("Target shelf life (days)", min_value=1, max_value=3650, value=14)
            )
            language = st.selectbox("Explanation language", ["English", "Hindi", "Marathi"])
        with second:
            st.subheader("Physical properties")
            moisture = float(st.slider("Moisture content (%)", 0.0, 100.0, 65.0))
            fat_content = float(st.slider("Oil/fat content (%)", 0.0, 100.0, 5.0))
            ph_level = float(
                st.number_input("pH", min_value=0.0, max_value=14.0, value=5.5, step=0.1)
            )
            respiration_label = st.selectbox("Respiration rate", list(RESPIRATION_OPTIONS))
        with third:
            st.subheader("Environment and logistics")
            storage_label = st.selectbox("Storage condition", list(STORAGE_OPTIONS))
            storage_type, default_storage_temp = STORAGE_OPTIONS[storage_label]
            storage_temp_c = float(
                st.number_input(
                    "Storage temperature (C)",
                    min_value=-60.0,
                    max_value=60.0,
                    value=default_storage_temp,
                    step=0.5,
                )
            )
            relative_humidity = float(st.slider("Relative humidity (%)", 0.0, 100.0, 85.0))
            transport_label = st.selectbox("Transport mode", list(TRANSPORT_OPTIONS))
            transport_duration_hr = float(
                st.number_input(
                    "Transport duration (hours)",
                    min_value=0.0,
                    max_value=8760.0,
                    value=24.0,
                )
            )
        submitted = st.form_submit_button("Generate packaging specification", type="primary")

    if submitted:
        if not commodity_name.strip():
            st.warning("Enter a commodity name before generating a recommendation.")
        else:
            payload = build_request_payload(
                commodity_name=commodity_name.strip(),
                category=CATEGORY_OPTIONS[category_label],
                desired_shelf_life=desired_shelf_life,
                moisture=moisture,
                fat_content=fat_content,
                ph_level=ph_level,
                respiration=RESPIRATION_OPTIONS[respiration_label],
                storage_type=storage_type,
                storage_temp_c=storage_temp_c,
                relative_humidity_pct=relative_humidity,
                transport_mode=TRANSPORT_OPTIONS[transport_label],
                transport_duration_hr=transport_duration_hr,
            )
            try:
                recommendation_response = fetch_recommendation(payload)
            except (requests.RequestException, ValueError) as error:
                st.error(f"Recommendation API unavailable: {error}")
            else:
                st.session_state["recommendation_request"] = payload
                st.session_state["recommendation_response"] = recommendation_response
                st.session_state["report_language"] = language

    request_payload = st.session_state.get("recommendation_request")
    recommendation_response = st.session_state.get("recommendation_response")
    if isinstance(request_payload, dict) and isinstance(recommendation_response, dict):
        render_results(
            request_payload,
            recommendation_response,
            str(st.session_state.get("report_language", "English")),
        )


if __name__ == "__main__":
    main()
