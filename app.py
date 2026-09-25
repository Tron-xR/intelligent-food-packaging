import streamlit as st
import requests
import json
import qrcode
from io import BytesIO

# Use 127.0.0.1 instead of localhost to prevent Pinggy tunneling cross-origin blocks
OLLAMA_URL = "http://127.0.0.1:11434/api/generate"
MODEL_NAME = "qwen3-coder" 

# Comprehensive database covering all materials mandated by MoFPI
PACKAGING_DB = {
    "LDPE (Low-Density Polyethylene)": {
        "otr": "2000-8000 cc/m²/day", "wvtr": "15-20 g/m²/day", "thickness_um": "40-75",
        "seal_temp": "105-120°C", "mechanical": "High flexibility, moderate puncture resistance",
        "cost_per_kg": "₹120", "sustainability": "Recyclable (Code 4)", "type": "Monolayer"
    },
    "HDPE (High-Density Polyethylene)": {
        "otr": "1000-3000 cc/m²/day", "wvtr": "4-10 g/m²/day", "thickness_um": "30-60",
        "seal_temp": "125-135°C", "mechanical": "High tensile strength, stiff",
        "cost_per_kg": "₹130", "sustainability": "Recyclable (Code 2)", "type": "Monolayer"
    },
    "PET / Polyester": {
        "otr": "50-100 cc/m²/day", "wvtr": "20-40 g/m²/day", "thickness_um": "12-25",
        "seal_temp": "Requires sealing layer (PE/EVA)", "mechanical": "Very high tensile strength, dimensional stability",
        "cost_per_kg": "₹170", "sustainability": "Widely Recyclable (Code 1)", "type": "Substrate/Laminate"
    },
    "EVOH Multi-Layer Barrier (PE/EVOH/PE)": {
        "otr": "1-5 cc/m²/day", "wvtr": "10-25 g/m²/day", "thickness_um": "60-100",
        "seal_temp": "110-130°C", "mechanical": "High puncture resistance, gas-tight",
        "cost_per_kg": "₹360", "sustainability": "Difficult to recycle (Multi-material)", "type": "Barrier Multi-layer"
    },
    "Metallized BOPP/PET Film": {
        "otr": "15-50 cc/m²/day", "wvtr": "1-3 g/m²/day", "thickness_um": "15-30",
        "seal_temp": "115-125°C", "mechanical": "Good tear resistance, light barrier",
        "cost_per_kg": "₹210", "sustainability": "Non-biodegradable, difficult to separate", "type": "Metallized"
    },
    "Aluminium Foil Laminate (PET/Al/PE)": {
        "otr": "< 0.1 cc/m²/day (True Barrier)", "wvtr": "< 0.1 g/m²/day", "thickness_um": "70-120",
        "seal_temp": "130-150°C", "mechanical": "High burst strength, zero pinhole tolerance",
        "cost_per_kg": "₹310", "sustainability": "Non-recyclable composite", "type": "Barrier Foil"
    },
    "Micro-Perforated Breathable Film": {
        "otr": "> 10,000 cc/m²/day (Controlled Diffusion)", "wvtr": "50-100 g/m²/day", "thickness_um": "25-40",
        "seal_temp": "105-115°C", "mechanical": "Moderate tear strength",
        "cost_per_kg": "₹240", "sustainability": "Recyclable PE base", "type": "Breathable"
    },
    "Biodegradable PLA / PBAT Blend": {
        "otr": "400-800 cc/m²/day", "wvtr": "150-250 g/m²/day", "thickness_um": "30-50",
        "seal_temp": "85-105°C", "mechanical": "Moderate tensile, lower puncture strength",
        "cost_per_kg": "₹420", "sustainability": "Compostable (EN 13432)", "type": "Bio-based"
    }
}

st.set_page_config(page_title="MoFPI Smart Packaging Engine", layout="wide")
st.title("🌱 AI-Powered Intelligent Food Packaging Recommendation System")
st.markdown("**Problem Statement ID: SIH26236** | MoFPI Decision Support System")

# 1. UI Wrapped in a Form to prevent accidental re-runs on slider/dropdown touch
with st.form(key="mofpi_input_form"):
    col1, col2, col3 = st.columns(3)

    with col1:
        st.subheader("1. Commodity Properties")
        commodity_name = st.text_input("Food Commodity", placeholder="e.g., Guava, Paneer, Roasted Cashews")
        category = st.selectbox("Category", ["Fresh Produce (Fruits/Veg)", "Dairy Products", "Processed / Snacks / Dry", "Meat, Poultry & Seafood", "Bakery & Confectionery"])
        desired_shelf_life = st.number_input("Desired Target Shelf Life (Days)", min_value=1, value=14)
        language = st.selectbox("Language / भाषा / भाषा", ["English", "Marathi", "Hindi"])

    with col2:
        st.subheader("2. Chemical & Biological Metrics")
        moisture = st.slider("Moisture Content (%)", 0, 100, 65)
        fat_content = st.slider("Oil/Fat Content (%)", 0, 100, 5)
        ph_level = st.number_input("Product pH Level", 1.0, 14.0, 5.5, step=0.1)
        respiration = st.selectbox("Respiration Rate", ["None / Non-respiring", "Low (<10 mg CO2/kg-h)", "Moderate (10-20 mg CO2/kg-h)", "High (20-40 mg CO2/kg-h)", "Extremely High / Climacteric (>40 mg CO2/kg-h)"])

    with col3:
        st.subheader("3. Environmental & Logistics")
        storage_type = st.selectbox("Storage Condition", ["Ambient (20°C to 28°C)", "Chilled (2°C to 8°C)", "Frozen (-18°C or below)"])
        rel_humidity = st.slider("Storage Relative Humidity (% RH)", 10, 100, 85)
        transport_stress = st.selectbox("Transportation Stress", ["Local Transit (Low vibration)", "Inter-state Highway (Moderate stress)", "Long-haul / Export / Rough handling"])

    # The Submit button MUST be inside the form block
    submit_pressed = st.form_submit_button(label="Generate MoFPI Packaging Specification Matrix", type="primary")

# QR Code Generator Function
def generate_qr(payload_dict):
    qr = qrcode.QRCode(version=1, box_size=5, border=2)
    qr.add_data(json.dumps(payload_dict, indent=2))
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

st.divider()

# 2. Session state to prevent silent reload bug when downloading QR
if "report_generated" not in st.session_state:
    st.session_state.report_generated = False
    st.session_state.report_text = ""
    st.session_state.qr_image = None

if submit_pressed:
    if not commodity_name.strip():
        st.warning("Please specify the Food Commodity Name.")
    else:
        st.session_state.report_generated = True
        st.session_state.report_text = ""  # Reset previous text
        st.session_state.qr_image = None

# 3. Main Generation & Streaming Logic
if st.session_state.report_generated:
    col_left, col_right = st.columns([2.8, 1.2])
    
    with col_left:
        st.success("MoFPI Technical Packaging Specification Generating...")
        
        db_context = json.dumps(PACKAGING_DB, indent=2)
        system_prompt = f"""
        You are an expert Food Packaging Scientist and Technologist representing the Ministry of Food Processing Industries (MoFPI).
        Analyze these scientific parameters for a food commodity and prescribe the packaging configuration:
        
        - Commodity: {commodity_name} (Category: {category})
        - Target Shelf Life: {desired_shelf_life} days
        - Chemical: Moisture: {moisture}%, Fat/Oil: {fat_content}%, pH: {ph_level}
        - Biological: Respiration Rate: {respiration}
        - Storage: {storage_type}, {rel_humidity}% Relative Humidity
        - Transport Logistics: {transport_stress}
        
        You MUST prioritize selecting materials and specifications from this certified packaging database:
        {db_context}
        
        Generate your technical evaluation formatted strictly under these headers in {language}:
        
        ### 1. Recommended Material Architecture
        - **Primary Film:** Choose exact match from DB and justify based on fat, moisture, and pH.
        - **Secondary/Outer Layer:** Specify laminate structure if needed.
        - **Sustainable / Eco-Friendly Alternative:** Recommend a biodegradable or circular alternative from the DB.
        
        ### 2. Engineering & Barrier Specifications
        - **Target OTR:** Specific range in cc/m²/day. (Explain risk: oxidation vs. anaerobic fermentation).
        - **Target WVTR:** Specific range in g/m²/day. (Explain moisture loss or caking risk).
        - **Recommended Thickness:** Film thickness in microns (µm).
        - **Mechanical Strength & Sealability:** Dart impact/puncture strength requirements based on transport stress, and heat seal temperature range.
        
        ### 3. MAP (Modified Atmosphere Packaging) Protocol
        - **Suitability:** (Yes / No / Not Recommended)
        - **Recommended Gas Mixture:** Target %O2, %CO2, and %N2.
        - **Respiration Management:** For fresh produce, explain whether breathable or micro-perforated film is required to balance respiration.
        
        ### 4. Shelf-Life & Cost Optimization Matrix
        - **Unpackaged / Traditional Shelf-Life:** Estimated days.
        - **Extended Shelf-Life with Recommended Pack:** Estimated days.
        - **Cost Evaluation:** Economic viability for small farmers/MSMEs using the DB cost metrics.
        """

        try:
            payload = {"model": MODEL_NAME, "prompt": system_prompt, "stream": True}
            
            # Timeout limits added to fail gracefully on Pinggy
            response = requests.post(OLLAMA_URL, json=payload, stream=True, timeout=(15.0, 300.0))
            response.raise_for_status()
            
            # Stream the data live dynamically word-by-word
            def stream_generator():
                for line in response.iter_lines():
                    if line:
                        chunk = json.loads(line)
                        if "response" in chunk:
                            yield chunk["response"]
                            
            st.session_state.report_text = st.write_stream(stream_generator())
            
        except requests.exceptions.ConnectionError:
            st.error(f"🚨 AI Offline: Could not connect to local Ollama at {OLLAMA_URL}. Please ensure 'ollama run {MODEL_NAME}' is active.")
        except requests.exceptions.Timeout:
            st.error("⏳ AI Timeout: The model took too long to respond. If you are using Pinggy, the connection dropped.")
        except Exception as e:
            st.error(f"System Error: {e}")

    with col_right:
        st.subheader("📦 Traceability QR")
        traceability_payload = {
            "commodity": commodity_name,
            "category": category,
            "storage": storage_type,
            "target_life_days": desired_shelf_life,
            "rh_pct": rel_humidity,
            "ph": ph_level,
            "compliance": "MoFPI-SIH26236-Standard",
            "status": "Verified Packaging Spec"
        }
        
        st.session_state.qr_image = generate_qr(traceability_payload)
        st.image(st.session_state.qr_image, caption="Scan with Handheld Logistics Scanner")
        
        st.download_button(
            label="Download Supply Chain QR",
            data=st.session_state.qr_image,
            file_name=f"{commodity_name}_traceability_spec.png",
            mime="image/png"
        )
        st.caption("QR contains machine-readable JSON: storage limits, target shelf life, and transit parameters.")