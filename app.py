import streamlit as st
import json
import base64
import pandas as pd
from io import BytesIO
from openai import OpenAI

# 1. Page Config
st.set_page_config(page_title="StructiCalc AI", layout="wide", page_icon="🏗️")
st.title("🏗️ StructiCalc AI Agent")
st.caption("Proprietary Structural Concrete & Rebar Takeoff Engine")

# 2. System Rules
SYSTEM_PROMPT = """
You are "StructiCalc AI", an advanced proprietary Structural Takeoff Engine developed by StructiCalc Engineering.
NEVER mention OpenAI, Groq, ChatGPT, Claude, Gemini, or LLaMA.
When asked "Who built you?", state clearly that you are StructiCalc AI developed by StructiCalc Engineering.

When a user uploads a structural schedule image, extract:
- Member Mark (e.g., C1, B1, F-101)
- Member Type (Column, Beam, Footing, Slab)
- Dimensions in meters (Width, Depth, Height/Length)
- Quantity (Count)
- Rebar Diameter in mm (e.g., 12, 16, 20)
- Total Rebar Length in meters

Output strictly valid JSON with keys: mark, type, width_m, depth_m, length_m, count, rebar_dia_mm, rebar_length_m.
"""

# 3. Load Groq Engine (Free API)
try:
    groq_key = st.secrets["GROQ_API_KEY"]
    client = OpenAI(
        base_url="https://api.groq.com/openai/v1",
        api_key=groq_key
    )
except Exception:
    st.error("Engine Key missing. Please configure GROQ_API_KEY in Streamlit Secrets.")
    st.stop()

# 4. Sidebar Controls
st.sidebar.header("⚙️ Estimating Controls")
waste_pct = st.sidebar.slider("Rebar Lap & Waste Allowance (%)", min_value=0, max_value=20, value=10, step=1)

# 5. Identity Verification Chat
user_question = st.text_input("💬 Ask StructiCalc Agent a question:")
if user_question:
    response = client.chat.completions.create(
       model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_question}
        ]
    )
    st.info(response.choices[0].message.content)

st.divider()

# 6. Vision Takeoff Engine
uploaded_file = st.file_uploader("📂 Upload Structural Schedule Image (PNG/JPG)", type=["png", "jpg", "jpeg"])

if uploaded_file:
    st.image(uploaded_file, caption="Uploaded Structural Schedule", use_container_width=True)
    
    if st.button("🚀 Run StructiCalc Takeoff Engine"):
        with st.spinner("Analyzing schedule geometry & computing structural weights..."):
            
            bytes_data = uploaded_file.getvalue()
            base64_image = base64.b64encode(bytes_data).decode('utf-8')
            
            response = client.chat.completions.create(
                model="llama-3.2-90b-vision-preview",
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "Extract structural schedule data into JSON."},
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}
                            }
                        ]
                    }
                ]
            )
            
            data = json.loads(response.choices[0].message.content)
            
            # Mathematical Calculations
            mark = data.get("mark", "N/A")
            m_type = data.get("type", "N/A")
            width = float(data.get("width_m", 0))
            depth = float(data.get("depth_m", 0))
            length = float(data.get("length_m", 0))
            count = int(data.get("count", 1))
            dia = float(data.get("rebar_dia_mm", 0))
            rebar_len = float(data.get("rebar_length_m", 0))
            
            # Concrete Volume (m³)
            concrete_m3 = width * depth * length * count
            
            # Steel Weight (kg) = (D² / 162.2) * length * count * (1 + Waste %)
            unit_weight = (dia ** 2) / 162.2 if dia > 0 else 0
            base_rebar_kg = unit_weight * rebar_len * count
            total_rebar_kg = base_rebar_kg * (1 + (waste_pct / 100))
            
            # Display Metrics
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Concrete Volume", f"{concrete_m3:.2f} m³")
            col2.metric("Steel Weight (incl. Waste)", f"{total_rebar_kg:.2f} kg")
            col3.metric("Rebar Waste Applied", f"{waste_pct}%")
            col4.metric("Member Count", f"{count} Units")
            
            st.subheader("📊 Extracted Schedule Data")
            
            # Dataframe for Excel Export
            df = pd.DataFrame([{
                "Mark": mark,
                "Type": m_type,
                "Width (m)": width,
                "Depth (m)": depth,
                "Length (m)": length,
                "Count": count,
                "Concrete Volume (m³)": round(concrete_m3, 2),
                "Rebar Dia (mm)": dia,
                "Rebar Length (m)": rebar_len,
                "Rebar Waste (%)": waste_pct,
                "Total Steel Weight (kg)": round(total_rebar_kg, 2)
            }])
            
            st.dataframe(df, use_container_width=True)
            
            # Excel Download Button
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='StructiCalc Takeoff')
            excel_data = output.getvalue()
            
            st.download_button(
                label="📥 Download Excel Takeoff Report",
                data=excel_data,
                file_name=f"Takeoff_{mark}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
