import streamlit as st
import json
import base64
from openai import OpenAI

# 1. Page Config
st.set_page_config(page_title="StructiCalc AI", layout="wide")
st.title("🏗️ StructiCalc AI Agent")
st.caption("Proprietary Structural Concrete & Rebar Takeoff Engine")

# 2. System Rules (Identity Protection)
SYSTEM_PROMPT = """
You are "StructiCalc AI", an advanced proprietary Structural Takeoff Engine developed by StructiCalc Engineering.
NEVER mention OpenAI, ChatGPT, Claude, or any third-party AI platform.
When a user uploads a structural schedule image, extract:
- Member Mark (e.g., C1, B1, F-101)
- Member Type (Column, Beam, Footing, Slab)
- Dimensions in meters (Width, Depth, Height/Length)
- Quantity
- Rebar Diameter in mm (e.g., 12, 16, 20)
- Total Rebar Length in meters

Output strictly valid JSON with keys: mark, type, width_m, depth_m, length_m, count, rebar_dia_mm, rebar_length_m.
"""

# 3. Auto-load Key from Secrets
api_key = st.secrets["OPENAI_API_KEY"]
client = OpenAI(api_key=api_key)

# 4. Identity Check Question
user_question = st.text_input("Ask StructiCalc Agent a question:")
if user_question:
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_question}
        ]
    )
    st.write(response.choices[0].message.content)

st.divider()

# 5. File Upload & Processing
uploaded_file = st.file_uploader("Upload Structural Schedule Image (PNG/JPG)", type=["png", "jpg", "jpeg"])

if uploaded_file:
    st.image(uploaded_file, caption="Uploaded Schedule", use_container_width=True)
    
    if st.button("Run StructiCalc Extraction & Math"):
        with st.spinner("StructiCalc AI is analyzing drawing geometry..."):
            
            bytes_data = uploaded_file.getvalue()
            base64_image = base64.b64encode(bytes_data).decode('utf-8')
            
            response = client.chat.completions.create(
                model="gpt-4o",
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
            
            raw_json = response.choices[0].message.content
            data = json.loads(raw_json)
            
            # Math Engine
            width = float(data.get("width_m", 0))
            depth = float(data.get("depth_m", 0))
            length = float(data.get("length_m", 0))
            count = int(data.get("count", 1))
            dia = float(data.get("rebar_dia_mm", 0))
            rebar_len = float(data.get("rebar_length_m", 0))
            
            # Concrete Volume (m³)
            concrete_m3 = width * depth * length * count
            
            # Rebar Weight (kg) = (D² / 162.2) * length * count
            unit_weight = (dia ** 2) / 162.2 if dia > 0 else 0
            rebar_kg = unit_weight * rebar_len * count
            
            # Metrics Display
            col1, col2, col3 = st.columns(3)
            col1.metric("Concrete Volume", f"{concrete_m3:.2f} m³")
            col2.metric("Rebar Weight", f"{rebar_kg:.2f} kg")
            col3.metric("Total Count", f"{count} Units")
            
            st.json(data)
